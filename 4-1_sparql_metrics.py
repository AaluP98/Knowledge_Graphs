"""
4-1 Symbolic Methods: SPARQL Queries & KG Metrics

Make SPARQL queries on HI KG & compute structural KG metrics using NetworkX.

Output:
  -> query results print to console
  -> kg_metrics.json (metrics summary forthe report)
  -> kg_metrics.png (bar chart of class counts)

"""

from rdflib import Graph, Namespace
import json
import collections


# load graph
HI = Namespace("https://w3id.org/hi-ontology#")

g = Graph()
g.parse("hi_ontology_linked.ttl", format="turtle")   # use linked version 
# g.parse("hi-ontology-populated.ttl", format="turtle")  
print(f"Graph loaded: {len(g)} triples\n")


# SPARQL queries
QUERIES = {}


#  list all use cases with their domain
QUERIES["1_usecases_with_domain"] = """
PREFIX hi:   <https://w3id.org/hi-ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?usecase ?ucLabel ?domain ?domainLabel WHERE {
    ?usecase  a hi:UseCase ;
              hi:hasDomain ?domain .
    OPTIONAL { ?usecase rdfs:label ?ucLabel . }
    OPTIONAL { ?domain  rdfs:label ?domainLabel . }
}
ORDER BY ?domainLabel
"""


# for each HI team, list its members (with agent type)
QUERIES["2_team_members"] = """
PREFIX hi:   <https://w3id.org/hi-ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?team ?teamLabel ?agent ?agentLabel ?agentType WHERE {
    ?team   a hi:HITeam ;
            hi:hasMember ?agent .
    ?agent  rdf:type ?agentType .
    FILTER(?agentType IN (hi:HumanAgent, hi:ArtificialAgent))
    OPTIONAL { ?team  rdfs:label ?teamLabel . }
    OPTIONAL { ?agent rdfs:label ?agentLabel . }
}
ORDER BY ?teamLabel ?agentType
"""


# agents with most capabilities (top10)
QUERIES["3_most_capable_agents"] = """
PREFIX hi:   <https://w3id.org/hi-ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?agent ?label (COUNT(?cap) AS ?capCount) WHERE {
    ?agent hi:hasCapability ?cap .
    OPTIONAL { ?agent rdfs:label ?label . }
}
GROUP BY ?agent ?label
ORDER BY DESC(?capCount)
LIMIT 10
"""


# tasks with the most required capabilities (complexity proxy)
QUERIES["4_complex_tasks"] = """
PREFIX hi:   <https://w3id.org/hi-ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?task ?label (COUNT(?cap) AS ?capCount) WHERE {
    ?task hi:requiresCapability ?cap .
    OPTIONAL { ?task rdfs:label ?label . }
}
GROUP BY ?task ?label
ORDER BY DESC(?capCount)
LIMIT 10
"""


# human–AI interaction episodes (which pairs interact)
QUERIES["5_human_ai_interactions"] = """
PREFIX hi:   <https://w3id.org/hi-ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?interaction ?humanLabel ?aiLabel WHERE {
    ?interaction a hi:Interaction ;
                 hi:hasAgentInvolved ?human ;
                 hi:hasAgentInvolved ?ai .
    ?human  rdf:type hi:HumanAgent .
    ?ai     rdf:type hi:ArtificialAgent .
    FILTER(?human != ?ai)
    OPTIONAL { ?human rdfs:label ?humanLabel . }
    OPTIONAL { ?ai    rdfs:label ?aiLabel . }
}
ORDER BY ?humanLabel
"""


# use cases in domains that have more than one team
QUERIES["6_multi_team_domains"] = """
PREFIX hi:   <https://w3id.org/hi-ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?domain ?domainLabel (COUNT(?uc) AS ?ucCount) WHERE {
    ?uc a hi:UseCase ;
        hi:hasDomain ?domain .
    OPTIONAL { ?domain rdfs:label ?domainLabel . }
}
GROUP BY ?domain ?domainLabel
HAVING (COUNT(?uc) > 1)
ORDER BY DESC(?ucCount)
"""


# capabilities shared by both human and artificial agents
QUERIES["7_shared_capabilities"] = """
PREFIX hi:   <https://w3id.org/hi-ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?cap ?capLabel
       (COUNT(DISTINCT ?human) AS ?humanCount)
       (COUNT(DISTINCT ?ai) AS ?aiCount)
WHERE {
    ?cap a hi:Capability .
    OPTIONAL { ?cap rdfs:label ?capLabel . }
    OPTIONAL {
        ?human rdf:type hi:HumanAgent ;
               hi:hasCapability ?cap .
    }
    OPTIONAL {
        ?ai rdf:type hi:ArtificialAgent ;
            hi:hasCapability ?cap .
    }
}
GROUP BY ?cap ?capLabel
HAVING (COUNT(DISTINCT ?human) > 0 && COUNT(DISTINCT ?ai) > 0)
ORDER BY DESC(?humanCount)
"""


# external links added (owl:sameAs triples)
QUERIES["8_external_links"] = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>

SELECT ?entity ?externalURI WHERE {
    ?entity owl:sameAs ?externalURI .
    FILTER(STRSTARTS(STR(?entity), "https://w3id.org/hi-ontology#"))
}
ORDER BY ?entity
"""

# task executions that involve an AI model
QUERIES["9_executions_with_models"] = """
PREFIX hi:   <https://w3id.org/hi-ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?exec ?execLabel ?model ?modelLabel WHERE {
    ?exec  hi:usesModel ?model .
    OPTIONAL { ?exec  rdfs:label ?execLabel . }
    OPTIONAL { ?model rdfs:label ?modelLabel . }
}
"""

# goals that require more than 2 tasks (ambitious goals)
QUERIES["10_ambitious_goals"] = """
PREFIX hi:   <https://w3id.org/hi-ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?goal ?label (COUNT(?task) AS ?taskCount) WHERE {
    ?goal hi:requiresTask ?task .
    OPTIONAL { ?goal rdfs:label ?label . }
}
GROUP BY ?goal ?label
HAVING (COUNT(?task) > 2)
ORDER BY DESC(?taskCount)
"""



# run all queries
results_summary = {}

for qname, qstr in QUERIES.items():
    print(f"\n{'='*60}")
    print(f"  {qname}")
    print('='*60)
    try:
        rows = list(g.query(qstr))
        results_summary[qname] = len(rows)
        if not rows:
            print(" (no results) :( ")
            continue

        # print in simple table
        if rows:
            vars_ = [str(v) for v in rows[0].__dict__.get("_fields", rows[0].labels or [])]
        for row in rows[:20]:   # cap display at 20 rows
            vals = [str(v) if v else "-" for v in row]
            print("  " + " | ".join(f"{k}={v[:60]}" for k, v in zip(vars_, vals)))
        if len(rows) > 20:
            print(f"({len(rows) - 20} more rows)")
    except Exception as e:
        print(f" ERROR: {e}")





# KG metrcs (structural, using rdflib + basic counting)
print(f"\n\n{'='*60}")
print(" KG STRUCTURAL METRICS::")
print('='*60)

HI_NS = "https://w3id.org/hi-ontology#"

# count instances per class
CLASS_QUERY = """
PREFIX hi:  <https://w3id.org/hi-ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?class (COUNT(?inst) AS ?count) WHERE {
    ?inst rdf:type ?class .
    FILTER(STRSTARTS(STR(?class), "https://w3id.org/hi-ontology#"))
    FILTER(?inst != ?class)
}
GROUP BY ?class
ORDER BY DESC(?count)
"""

class_counts = {}
for row in g.query(CLASS_QUERY):
    cname = str(row["class"]).replace(HI_NS, "hi:")
    class_counts[cname] = int(row["count"])

print("\n Instance counts per class:")
for cls, cnt in class_counts.items():
    bar = "█" * min(cnt, 40)
    print(f"  {cls:<40} {cnt:>4}  {bar}")


# triple count
total_triples = len(g)

# count unique subjects, predicates, objects
subjects   = set(s for s, _, _ in g)
predicates = set(p for _, p, _ in g)
objects    = set(o for _, _, o in g)

# count HI-namespace entities only
hi_entities = set(s for s in subjects if str(s).startswith(HI_NS))

# object properties used
OP_QUERY = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
SELECT (COUNT(?p) AS ?count) WHERE {
    ?p a owl:ObjectProperty .
}
"""
op_count = int(list(g.query(OP_QUERY))[0][0])

# data properties used
DP_QUERY = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
SELECT (COUNT(?p) AS ?count) WHERE {
    ?p a owl:DatatypeProperty .
}
"""
dp_count = int(list(g.query(DP_QUERY))[0][0])

# classes defined
CLS_DEF_QUERY = """
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT (COUNT(?c) AS ?count) WHERE { ?c a owl:Class . }
"""
cls_count = int(list(g.query(CLS_DEF_QUERY))[0][0])

#  external links
EXT_QUERY = """
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT (COUNT(?s) AS ?count) WHERE {
    ?s owl:sameAs ?o .
    FILTER(STRSTARTS(STR(?s), "https://w3id.org/hi-ontology#"))
}
"""
ext_links = int(list(g.query(EXT_QUERY))[0][0])

metrics = {
    "total_triples": total_triples,
    "unique_subjects": len(subjects),
    "unique_predicates": len(predicates),
    "unique_objects": len(objects),
    "hi_namespace_entities": len(hi_entities),
    "ontology_classes": cls_count,
    "object_properties": op_count,
    "data_properties": dp_count,
    "external_sameAs_links": ext_links,
    "class_instance_counts": class_counts,
}

print(f"\n  Total triples: {total_triples}")
print(f" Unique subjects: {len(subjects)}")
print(f" Unique predicates: {len(predicates)}")
print(f" HI-namespace entities: {len(hi_entities)}")
print(f" Ontology classes: {cls_count}")
print(f" Object properties: {op_count}")
print(f" Data properties: {dp_count}")
print(f" External sameAs links: {ext_links}")

#  save metrics to JSON
with open("kg_metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)
print("\n kg_metrics.json saved")



# basic kg metrics using NetworkX (optional but great for the report)
try:
    import networkx as nx
    import matplotlib.pyplot as plt

    print("\n bilding NetworkX graph for structural analysis")
    G = nx.DiGraph()

    # add only HI-namespace triples as edges 
    for s, p, o in g:
        if str(s).startswith(HI_NS) and str(o).startswith(HI_NS):
            G.add_edge(str(s).split("#")[-1], str(o).split("#")[-1],
                       label=str(p).split("#")[-1])

    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")
    density = nx.density(G)
    print(f"  Density: {density:.4f}")

    # degree distribution
    in_degrees  = sorted([d for _, d in G.in_degree()], reverse=True)
    out_degrees = sorted([d for _, d in G.out_degree()], reverse=True)
    print(f"  Max in-degree:  {in_degrees[0]}")
    print(f"  Max out-degree: {out_degrees[0]}")

    # top10 most connected nodes
    top_nodes = sorted(G.degree(), key=lambda x: x[1], reverse=True)[:10]
    print("\n  Top-10 most connected entities:")
    for node, deg in top_nodes:
        print(f"    {node:<50} degree={deg}")

    # weakly connected components
    wcc = list(nx.weakly_connected_components(G))
    print(f"\n  Weakly connected components: {len(wcc)}")
    print(f"  Largest component size: {max(len(c) for c in wcc)}")

    # add networkx metrics to saved dict
    metrics["nx_nodes"]   = G.number_of_nodes()
    metrics["nx_edges"]   = G.number_of_edges()
    metrics["nx_density"] = density
    metrics["nx_wcc"]     = len(wcc)
    with open("kg_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # bar chart of class counts
    plt.figure(figsize=(10, 5))
    short_labels = [k.replace("hi:", "") for k in class_counts.keys()]
    counts = list(class_counts.values())
    bars = plt.barh(short_labels[::-1], counts[::-1], color="#53a5dc")
    plt.xlabel("Number of instances")
    plt.title("HI KG instances per class")
    plt.tight_layout()
    plt.savefig("kg_metrics_class_counts.png", dpi=150)
    print("\n  Bar chart saved to kg_metrics_class_counts.png")

    # degree distribution plot 
    plt.figure(figsize=(8, 4))
    plt.hist(in_degrees,  bins=20, alpha=0.7, label="in-degree",  color="#48B9E2")
    plt.hist(out_degrees, bins=20, alpha=0.7, label="out-degree", color="#D3431B")
    plt.xlabel("Degree")
    plt.ylabel("Frequency")
    plt.title("Degree distribution (HI NS subgraph)")
    plt.legend()
    plt.tight_layout()
    plt.savefig("kg_metrics_degree_dist.png", dpi=150)
    print("kg_metrics_degree_dist.png saved")

except ImportError:
    print("\n [INFO] NetworkX/matplotlib not installed — skipping graph metrics.")
    print("pip install networkx matplotlib")

print("\n Done :)")
