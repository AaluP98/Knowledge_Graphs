"""
3 - External Linking

Output: hi_ontology_linked.ttl  (populated HI KG & new external links)
"""

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD
from SPARQLWrapper import SPARQLWrapper, JSON
import requests
import time
import json


# namespaces
HI      = Namespace("https://w3id.org/hi-ontology#")
DBR     = Namespace("http://dbpedia.org/resource/")
DBO     = Namespace("http://dbpedia.org/ontology/")
WD      = Namespace("http://www.wikidata.org/entity/")
SCHEMA  = Namespace("http://schema.org/")


# Manual mapping 
# (entity URI in KG  to  external URIs)
# for concepts that are clearly identifiable (well-known AI tools,
# domains, methods) -> curated manual mappings; more accurate and reproducible than automated lookup.
# For the remaining entities we use the Wikidata/DBpedia SPARQL lookup.


MANUAL_LINKS = {
    # agents
    "AlphaFoldSystem": {
        "dbpedia": "http://dbpedia.org/resource/AlphaFold",
        "wikidata": "http://www.wikidata.org/entity/Q79161027",
    },
    "NaoRobot": {
        "dbpedia": "http://dbpedia.org/resource/Nao_(robot)",
        "wikidata": "http://www.wikidata.org/entity/Q732170",
    },
    "GrammarlyAutocorrect": {
        "wikidata": "http://www.wikidata.org/entity/Q5595569",
    },
    "TeslaAutosteer": {
        "dbpedia": "http://dbpedia.org/resource/Tesla_Autopilot",
        "wikidata": "http://www.wikidata.org/entity/Q21067279",
    },
    "Chatbot": {
        "dbpedia": "http://dbpedia.org/resource/Chatbot",
        "wikidata": "http://www.wikidata.org/entity/Q2241538",
    },
    "AssistiveRobot": {
        "dbpedia": "http://dbpedia.org/resource/Assistive_technology",
        "wikidata": "http://www.wikidata.org/entity/Q217138",
    },



    # domains
    "HealthcareDomain": {
        "dbpedia": "http://dbpedia.org/resource/Health_care",
        "wikidata": "http://www.wikidata.org/entity/Q31207",
    },
    "SecurityDomain": {
        "dbpedia": "http://dbpedia.org/resource/Computer_security",
        "wikidata": "http://www.wikidata.org/entity/Q3510521",
    },
    "EducationDomain": {
        "dbpedia": "http://dbpedia.org/resource/Education",
        "wikidata": "http://www.wikidata.org/entity/Q8434",
    },
    "PublicPolicyDomain": {
        "dbpedia": "http://dbpedia.org/resource/Public_policy",
        "wikidata": "http://www.wikidata.org/entity/Q322374",
    },
    "KnowledgeEngineeringDomain": {
        "dbpedia": "http://dbpedia.org/resource/Knowledge_engineering",
        "wikidata": "http://www.wikidata.org/entity/Q180684",
    },
    "SoftwareEngineeringDomain": {
        "dbpedia": "http://dbpedia.org/resource/Software_engineering",
        "wikidata": "http://www.wikidata.org/entity/Q80993",
    },
    "CulturalHeritageDomain": {
        "dbpedia": "http://dbpedia.org/resource/Cultural_heritage",
        "wikidata": "http://www.wikidata.org/entity/Q210272",
    },
    "ConversationalAIDomain": {
        "dbpedia": "http://dbpedia.org/resource/Dialogue_system",
        "wikidata": "http://www.wikidata.org/entity/Q1382110",
    },
    "MobilityDomain": {
        "dbpedia": "http://dbpedia.org/resource/Mobility_as_a_service",
        "wikidata": "http://www.wikidata.org/entity/Q18537",
    },
    "GovernanceDomain": {
        "dbpedia": "http://dbpedia.org/resource/Governance",
        "wikidata": "http://www.wikidata.org/entity/Q372824",
    },
    "BiometricsAndForensicsDomain": {
        "dbpedia": "http://dbpedia.org/resource/Biometrics",
        "wikidata": "http://www.wikidata.org/entity/Q207476",
    },
    "CausalDiscoveryDomain": {
        "dbpedia": "http://dbpedia.org/resource/Causal_inference",
        "wikidata": "http://www.wikidata.org/entity/Q217602",
    },
    "VirtualRealityDomain": {
        "dbpedia": "http://dbpedia.org/resource/Virtual_reality",
        "wikidata": "http://www.wikidata.org/entity/Q170538",
    },



    # capabilities
    "Transparency": {
        "dbpedia": "http://dbpedia.org/resource/Transparency_(behavior)",
        "wikidata": "http://www.wikidata.org/entity/Q372670",
    },
    "Adaptiveness": {
        "dbpedia": "http://dbpedia.org/resource/Adaptability",
    },
    "Communication": {
        "dbpedia": "http://dbpedia.org/resource/Communication",
        "wikidata": "http://www.wikidata.org/entity/Q11024",
    },
    "Personalization": {
        "dbpedia": "http://dbpedia.org/resource/Personalization",
        "wikidata": "http://www.wikidata.org/entity/Q1416796",
    },
    "UserModeling": {
        "dbpedia": "http://dbpedia.org/resource/User_modeling",
    },
    "ProteinStructurePrediction": {
        "dbpedia": "http://dbpedia.org/resource/Protein_structure_prediction",
        "wikidata": "http://www.wikidata.org/entity/Q901429",
    },
    "ClinicalJudgment": {
        "dbpedia": "http://dbpedia.org/resource/Clinical_psychology",
        "wikidata": "http://www.wikidata.org/entity/Q188553",
    },
    "Negotiation": {
        "dbpedia": "http://dbpedia.org/resource/Negotiation",
        "wikidata": "http://www.wikidata.org/entity/Q181764",
    },
    "Creativity": {
        "dbpedia": "http://dbpedia.org/resource/Creativity",
        "wikidata": "http://www.wikidata.org/entity/Q207537",
    },
    "SituationalAwareness": {
        "dbpedia": "http://dbpedia.org/resource/Situation_awareness",
        "wikidata": "http://www.wikidata.org/entity/Q1144315",
    },
    "ContinuousLearning": {
        "dbpedia": "http://dbpedia.org/resource/Lifelong_learning",
        "wikidata": "http://www.wikidata.org/entity/Q1154951",
    },
    "PatternRecognitionForThreatDetection": {
        "dbpedia": "http://dbpedia.org/resource/Pattern_recognition_(psychology)",
    },
    "LiteratureReview": {
        "dbpedia": "http://dbpedia.org/resource/Literature_review",
        "wikidata": "http://www.wikidata.org/entity/Q791676",
    },
    "ExplainabilityCapability": {
        "dbpedia": "http://dbpedia.org/resource/Explainable_artificial_intelligence",
        "wikidata": "http://www.wikidata.org/entity/Q61961899",
    },



    # methods
    "AxiomWeakening": {
        "dbpedia": "http://dbpedia.org/resource/Ontology_learning",
    },
    "SpreadingActivation": {
        "dbpedia": "http://dbpedia.org/resource/Spreading_activation",
        "wikidata": "http://www.wikidata.org/entity/Q907258",
    },
    "NeuroSymbolic": {
        "dbpedia": "http://dbpedia.org/resource/Neuro-symbolic_AI",
        "wikidata": "http://www.wikidata.org/entity/Q97477039",
    },
    "DeepLearningMethod": {
        "dbpedia": "http://dbpedia.org/resource/Deep_learning",
        "wikidata": "http://www.wikidata.org/entity/Q197536",
    },
    "AgentBasedSocialSimulationMethod": {
        "dbpedia": "http://dbpedia.org/resource/Agent-based_social_simulation",
        "wikidata": "http://www.wikidata.org/entity/Q619754",
    },
    "StatisticalMethod": {
        "dbpedia": "http://dbpedia.org/resource/Statistics",
        "wikidata": "http://www.wikidata.org/entity/Q12483",
    },
    "CoCreation": {
        "dbpedia": "http://dbpedia.org/resource/Co-creation",
        "wikidata": "http://www.wikidata.org/entity/Q5132513",
    },
    "LinearRegressionMethod": {
        "dbpedia": "http://dbpedia.org/resource/Linear_regression",
        "wikidata": "http://www.wikidata.org/entity/Q190391",
    },
    "KnowledgeDistillationMethod": {
        "dbpedia": "http://dbpedia.org/resource/Knowledge_distillation",
    },


    # link ontology classes to equivalent DBpedia/schema.org ones
    "_class_HITeam": {
        "schema": "http://schema.org/OrganizationRole",
    },
    "_class_HumanAgent": {
        "dbpedia_class": "http://dbpedia.org/ontology/Person",
        "schema": "http://schema.org/Person",
    },
    "_class_ArtificialAgent": {
        "dbpedia_class": "http://dbpedia.org/ontology/Software",
    },

}





# wikidata & DBpedia label-based lookup 

WIKIDATA_ENDPOINT = "https://www.wikidata.org/w/api.php"
DBPEDIA_ENDPOINT  = "https://dbpedia.org/sparql"


def lookup_wikidata(label: str) -> str | None:
    """search Wikidata for concept by label 
    return: entity URI or None"""
    params = {
        "action": "wbsearchentities",
        "search": label,
        "language": "en",
        "limit": 1,
        "format": "json",
    }
    try:
        r = requests.get(WIKIDATA_ENDPOINT, params=params, timeout=10)
        data = r.json()
        if data.get("search"):
            qid = data["search"][0]["id"]
            return f"http://www.wikidata.org/entity/{qid}"
    except Exception as e:
        print(f"[FAIL] Wikidata lookup failed for '{label}': {e}")
    return None



def lookup_dbpedia(label: str) -> str | None:
    """Search DBpedia for concept by label; 
    return: resource URI or None"""
    # DBpedia's lookup API
    url = f"https://lookup.dbpedia.org/api/search?query={requests.utils.quote(label)}&maxResults=1&format=json"
    try:
        r = requests.get(url, timeout=10, headers={"Accept": "application/json"})
        data = r.json()
        docs = data.get("docs", [])
        if docs:
            return docs[0].get("resource", [None])[0]
    except Exception as e:
        print(f"[FAIL] DBpedia lookup failed for '{label}': {e}")
    return None



# main enrichment function
def enrich_graph(input_ttl: str, output_ttl: str):
    print(f"Loading {input_ttl} ...")
    g = Graph()
    g.parse(input_ttl, format="turtle")
    print(f"  Loaded {len(g)} triples.")

    # bind prefixes for clean output
    g.bind("hi", HI)
    g.bind("owl", OWL)
    g.bind("skos", SKOS)
    g.bind("dbr", DBR)
    g.bind("wd", WD)
    g.bind("schema", SCHEMA)

    links_added = 0

    # apply manual mapping table
    print("\n Mnual links:")
    for local_name, targets in MANUAL_LINKS.items():
        if local_name.startswith("_class_"):
            continue  # handle separately below
        subject = HI[local_name]
        # Check the entity actually exists in the graph
        if (subject, None, None) not in g:
            print(f"[SKIP] {local_name} not found in graph")
            continue
        for src, uri in targets.items():
            obj = URIRef(uri)
            g.add((subject, OWL.sameAs, obj))
            print(f"  + {local_name}  owl:sameAs  <{uri}>")
            links_added += 1

    # link ontology classes to external equivalents
    print("\n Linking ontology classes: ")
    class_links = {
        HI.HITeam:         [URIRef("http://schema.org/Organization")],
        HI.HumanAgent:     [URIRef("http://dbpedia.org/ontology/Person"),
                            URIRef("http://schema.org/Person")],
        HI.ArtificialAgent:[URIRef("http://dbpedia.org/ontology/Software")],
        HI.Task:           [URIRef("http://schema.org/Action")],
        HI.Goal:           [URIRef("http://dbpedia.org/ontology/Goal")],
    }
    for hi_class, equivalents in class_links.items():
        for eq in equivalents:
            g.add((hi_class, OWL.equivalentClass, eq))
            print(f"  + hi:{hi_class.split('#')[1]}  owl:equivalentClass  <{eq}>")
            links_added += 1



    # auto-lookup for all hi:Domain instances without manual links
    print("\n auto-enriching domain instances (Wikidata):")
    DOMAIN_QUERY = """
    PREFIX hi: <https://w3id.org/hi-ontology#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?domain ?label WHERE {
        ?domain a hi:Domain .
        ?domain rdfs:label ?label .
        FILTER(LANG(?label) = "en")
    }
    """
    already_mapped = set(MANUAL_LINKS.keys())
    for row in g.query(DOMAIN_QUERY):
        domain_uri = row["domain"]
        label      = str(row["label"])
        local_name = str(domain_uri).split("#")[-1]
        if local_name in already_mapped:
            continue
        print(f"  Looking up '{label}' ...")
        wd_uri = lookup_wikidata(label)
        if wd_uri:
            g.add((domain_uri, OWL.sameAs, URIRef(wd_uri)))
            print(f"  + {local_name}  owl:sameAs  <{wd_uri}>")
            links_added += 1
        time.sleep(0.3)   # be polite to the API



    # skos:exactMatch links for capability instances to DBpedia
    print("\n auto-enriching capability instances (DBpedia):")
    CAP_QUERY = """
    PREFIX hi: <https://w3id.org/hi-ontology#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?cap ?label WHERE {
        ?cap a hi:Capability .
        ?cap rdfs:label ?label .
        FILTER(LANG(?label) = "en")
    }
    """
    for row in g.query(CAP_QUERY):
        cap_uri = row["cap"]
        label   = str(row["label"])
        local_name = str(cap_uri).split("#")[-1]
        if local_name in already_mapped:
            continue
        dbp_uri = lookup_dbpedia(label)
        if dbp_uri:
            g.add((cap_uri, SKOS.exactMatch, URIRef(dbp_uri)))
            print(f"  + {local_name}  skos:exactMatch  <{dbp_uri}>")
            links_added += 1
        time.sleep(0.3)



    # auto-lookup for method instances not in th manual table
    print("\n auto-enriching method instances (DBpedia): ")
    METHOD_QUERY = """
    PREFIX hi: <https://w3id.org/hi-ontology#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?method ?label WHERE {
        ?method a hi:Method .
        ?method rdfs:label ?label .
        FILTER(LANG(?label) = "en")
    }
    """
    for row in g.query(METHOD_QUERY):
        method_uri = row["method"]
        label = str(row["label"])
        local_name = str(method_uri).split("#")[-1]
        if local_name in already_mapped:
            continue
        dbp_uri = lookup_dbpedia(label)
        if dbp_uri:
            g.add((method_uri, SKOS.exactMatch, URIRef(dbp_uri)))
            print(f"  + {local_name}  skos:exactMatch  <{dbp_uri}>")
            links_added += 1
        time.sleep(0.3)



    # save enriched graph
    print(f"\n--- Saving {output_ttl} ({links_added} new triples added) ---")
    g.serialize(output_ttl, format="turtle")
    print("Done.")


if __name__ == "__main__":
    enrich_graph(
        input_ttl  = "hi-ontology-populated.ttl",
        output_ttl = "hi_ontology_linked.ttl",
    )
