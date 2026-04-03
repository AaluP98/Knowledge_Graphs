"""
4-2 Subsymbolic Methods, KG Embeddings & Link Prediction

Convert HI KG to triple format, trains a TransE embedding 
model using PyKEEN, evaluates it, and runs link prediction.

Output:
  - kg_triples.tsv (triple dump for embedding training)
  - results/ (PyKEEN training artifacts)
  - link_predictions.json (top predicted missing links)
  - embeddings_tsne.png (2D visualisation of entity embeddings)

"""

from rdflib import Graph, Namespace
from pathlib import Path
import json
import pandas as pd
import numpy as np

HI = Namespace("https://w3id.org/hi-ontology#")
HI_NS = "https://w3id.org/hi-ontology#"
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)


# (1) Extract triples from KG
print("Loading graph ...")
g = Graph()
g.parse("hi_ontology_linked.ttl", format="turtle")
# g.parse("hi-ontology-populated.ttl", format="turtle") 
print(f"  {len(g)} total triples loaded.")

# only keep triples where BOTH subject and object are HI-namespace entities
# (as schema/OWL axioms are not useful for embedding training)
triples = []
for s, p, o in g:
    s_str = str(s)
    o_str = str(o)
    if (s_str.startswith(HI_NS) and o_str.startswith(HI_NS)
            and not s_str == o_str):
        # shorten URIs to local names to be more readable
        s_short = s_str.split("#")[-1]
        p_short = str(p).split("#")[-1]
        o_short = o_str.split("#")[-1]
        triples.append((s_short, p_short, o_short))

# eemove duplicates
triples = list(set(triples))
print(f" number of HI-namespace triples retained: {len(triples)}")

# save as TSV (head, relation, tail as expected by PyKEEN's TriplesFactory)
tsv_path = Path("kg_triples.tsv")
with open(tsv_path, "w") as f:
    for h, r, t in triples:
        f.write(f"{h}\t{r}\t{t}\n")
print(f"  Triples saved to {tsv_path}")



# (2) Train a TransE embedding model with PyKEEN
try:
    import torch
    from pykeen.triples import TriplesFactory
    from pykeen.pipeline import pipeline
    from pykeen.models import TransE, RotatE


    print("\nBuilding TriplesFactory: ")
    tf = TriplesFactory.from_path(tsv_path)

    # split into train / validation / test (80/10/10)
    training, testing, validation = tf.split([0.8, 0.1, 0.1], random_state=42)

    print(f"Training triples: {training.num_triples}")
    print(f"Validation triples: {validation.num_triples}")
    print(f"Test triples: {testing.num_triples}")

    # TransE
    print("\nTraining TransE (50 epochs):")
    result_transe = pipeline(
        training=training,
        testing=testing,
        validation=validation,
        model="TransE",
        model_kwargs=dict(embedding_dim=64),
        optimizer="Adam",
        optimizer_kwargs=dict(lr=0.01),
        loss="marginranking",
        training_kwargs=dict(
            num_epochs=50,
            batch_size=32,
        ),
        random_seed=42,
        device="cpu",
    )
    result_transe.save_to_directory(RESULTS_DIR / "transe")
    print("TransE training complete.")



    # rotatE (usually better on smaller KGs) 
    print("\nTraining RotatE (50 epochs):")
    result_rotate = pipeline(
        training=training,
        testing=testing,
        validation=validation,
        model="RotatE",
        model_kwargs=dict(embedding_dim=64),
        optimizer="Adam",
        optimizer_kwargs=dict(lr=0.01),
        loss="nssa",
        training_kwargs=dict(
            num_epochs=50,
            batch_size=32,
        ),
        random_seed=42,
        device="cpu",
    )
    result_rotate.save_to_directory(RESULTS_DIR / "rotate")
    print("RotatE training complete.")



    # save metrics comparison
    metrics_comparison = {
        "TransE": {
            "hits@1":  result_transe.metric_results.get_metric("hits@1"),
            "hits@3":  result_transe.metric_results.get_metric("hits@3"),
            "hits@10": result_transe.metric_results.get_metric("hits@10"),
            "mrr":     result_transe.metric_results.get_metric("mean_reciprocal_rank"),
        },
        "RotatE": {
            "hits@1":  result_rotate.metric_results.get_metric("hits@1"),
            "hits@3":  result_rotate.metric_results.get_metric("hits@3"),
            "hits@10": result_rotate.metric_results.get_metric("hits@10"),
            "mrr":     result_rotate.metric_results.get_metric("mean_reciprocal_rank"),
        },
    }
    with open(RESULTS_DIR / "metrics_comparison.json", "w") as f:
        json.dump(metrics_comparison, f, indent=2)

    print("\nEmbedding Evaluation Results:")
    for model_name, m in metrics_comparison.items():
        print(f"  {model_name}:")
        for k, v in m.items():
            print(f"    {k}: {v:.4f}")


    # (3) link prediction
    print("\n Link Prediction:")
    # use best model based on mrr
    best_result = result_rotate if (
        metrics_comparison["RotatE"]["mrr"] > metrics_comparison["TransE"]["mrr"]
    ) else result_transe
    best_name = "RotatE" if best_result is result_rotate else "TransE"
    print(f" Using {best_name} (best MRR)")

    model = best_result.model
    tf_full = best_result.training  # entity/relation index

    # predict tails for known entities and interesting relations
    interesting_heads = [
        "HumanAgent", "ArtificialAgent", "Clinician",
        "AlphaFoldSystem", "NaoRobot", "AssistiveRobot",
    ]
    interesting_rels = [
        "hasCapability", "operatesInContext", "hasMember", "requiresTask",
    ]

    predictions = []
    for head in interesting_heads:
        if head not in tf_full.entity_to_id:
            continue
        for rel in interesting_rels:
            if rel not in tf_full.relation_to_id:
                continue
            # score all possible tails
            h_id = torch.tensor([tf_full.entity_to_id[head]])
            r_id = torch.tensor([tf_full.relation_to_id[rel]])
            hr_batch = torch.stack([h_id, r_id], dim=-1)
            scores = model.score_t(hr_batch).detach().numpy().flatten()
            # get t5 predicted tails
            top5_ids = np.argsort(scores)[-5:][::-1]
            id_to_entity = {v: k for k, v in tf_full.entity_to_id.items()}
            for tid in top5_ids:
                tail = id_to_entity[tid]
                predictions.append({
                    "head":     head,
                    "relation": rel,
                    "tail":     tail,
                    "score":    float(scores[tid]),
                })

    with open("link_predictions.json", "w") as f:
        json.dump(predictions[:50], f, indent=2)
    print(f"  Top link predictions saved to link_predictions.json")
    print("\n  Sample predictions:")
    for p in predictions[:10]:
        print(f"    ({p['head']}, {p['relation']}, {p['tail']})  score={p['score']:.3f}")


    # (4) visualise embeddings with t-SNE
    print("\n t-SNE Visualisation: ")
    try:
        from sklearn.manifold import TSNE
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches

        # eet entity embeddings
        entity_emb = model.entity_representations[0]().detach().numpy()
        if np.iscomplexobj(entity_emb):
            print("  Converting complex RotatE embeddings to real-valued vectors for t-SNE...")
            # concatenate real and imaginary parts: (N, D) complex => (N, 2D) real
            entity_emb = np.concatenate([entity_emb.real, entity_emb.imag], axis=-1)

        id_to_entity = {v: k for k, v in tf_full.entity_to_id.items()}

        # clour by entity type usng SPARQL results
        TYPE_QUERY = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX hi:  <https://w3id.org/hi-ontology#>
        SELECT ?entity ?type WHERE {
            ?entity rdf:type ?type .
            FILTER(?type IN (hi:HumanAgent, hi:ArtificialAgent, hi:Task,
                             hi:Capability, hi:Goal, hi:Context,
                             hi:HITeam, hi:UseCase, hi:TaskExecution))
            FILTER(STRSTARTS(STR(?entity), "https://w3id.org/hi-ontology#"))
        }
        """
        entity_types = {}
        for row in g.query(TYPE_QUERY):
            ent = str(row["entity"]).split("#")[-1]
            typ = str(row["type"]).split("#")[-1]
            entity_types[ent] = typ

        COLOR_MAP = {
            "HumanAgent":    "#6ad2ec",
            "ArtificialAgent":"#a9cf4f",
            "Task":          "#d3d538",
            "Capability":    "#e96a81",
            "Goal":          "#968ddb",
            "Context":       "#CD8643",
            "HITeam":        "#bc71f4",
            "UseCase":       "#3154BF",
            "TaskExecution": "#4f8892",
        }

        labels = [id_to_entity[i] for i in range(len(id_to_entity))]
        colors = [COLOR_MAP.get(entity_types.get(l, ""), "#848484") for l in labels]

        print("  Running t-SNE ...")
        tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, len(labels)-1))
        coords = tsne.fit_transform(entity_emb)

        plt.figure(figsize=(14, 10))
        plt.scatter(coords[:, 0], coords[:, 1], c=colors, alpha=0.7, s=40)

        # label a selection of interesting entities
        highlight = {
            "HumanAgent", "ArtificialAgent", "AlphaFoldSystem", "NaoRobot",
            "Clinician", "AssistiveRobot", "CybersecurityExpert",
        }
        for i, lbl in enumerate(labels):
            if lbl in highlight:
                plt.annotate(lbl, (coords[i, 0], coords[i, 1]),
                             fontsize=7, alpha=0.9)

        # legend
        patches = [mpatches.Patch(color=c, label=t) for t, c in COLOR_MAP.items()]
        plt.legend(handles=patches, fontsize=8, loc="upper right")
        plt.title("t-SNE of HI KG Entity Embeddings, rotatE")
        plt.tight_layout()
        plt.savefig("embeddings_tsne.png", dpi=150)
        print("embeddings_tsne.png saved")

    except ImportError:
        print(" [INFO] scikit-learn/matplotlib not installed — skipping t-SNE.")

except ImportError:
    print("\n[INFO] PyKEEN / torch not installed.")
    print("The triple dump (kg_triples.tsv) has been created.")

print("\n Dooone :) ")
