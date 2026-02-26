import os
import sys
import logging
import json
from datetime import datetime
from datasets import Dataset

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import phoenix as px  # noqa: E402
from ragas import evaluate  # noqa: E402
from ragas.metrics import (  # noqa: E402
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from llama_index.core import Settings  # noqa: E402
from src.config import setup_settings  # noqa: E402
from src.generation.rag_engine import RAGEngine  # noqa: E402

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("audit_quality")


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def run_audit(dataset_path=None, collection=None, mode="lab"):
    logger.info(f"Démarrage de l'audit de qualité Ragas (Mode: {mode})...")

    # 1. Initialisation de l'environnement
    setup_settings()

    audit_data = []

    # PBI-090/091 : Gestion des modes et datasets
    if mode == "lab":
        if not dataset_path:
            # 1. On cherche d'abord dans data/benchmarks/ground_truth_{theme}.json
            if collection:
                theme_gt = f"data/benchmarks/ground_truth_{collection}.json"
                if os.path.exists(theme_gt):
                    dataset_path = theme_gt
                    logger.info(f"Utilisation du Dataset thématique : {dataset_path}")

            # 2. Fallback sur ground_truth.json (benchmarks ou legacy)
            if not dataset_path:
                bench_gt = "data/benchmarks/ground_truth.json"
                legacy_gt = "data/ground_truth.json"
                if os.path.exists(bench_gt):
                    dataset_path = bench_gt
                    logger.info(
                        f"Utilisation du Gold Standard (benchmarks) : {dataset_path}"
                    )
                elif os.path.exists(legacy_gt):
                    dataset_path = legacy_gt
                    logger.info(
                        f"Utilisation du Gold Standard (legacy) : {dataset_path}"
                    )
    else:
        # Mode terrain : on force dataset_path à None pour déclencher l'extraction Phoenix
        dataset_path = None
        logger.info("Mode Terrain activé : extraction forcée des traces Phoenix.")

    # 2. Collecte des données (Synthétique ou Phoenix)
    if dataset_path and os.path.exists(dataset_path):
        logger.info(f"Chargement du dataset depuis {dataset_path}...")
        with open(dataset_path, "r", encoding="utf-8") as f:
            synthetic_data = json.load(f)

        engine = RAGEngine()
        # On utilise la collection spécifiée si fournie
        target_theme = collection if collection else engine.default_collection

        # On prend 10 items ou tout le dataset s'il est plus petit
        sample_size = min(len(synthetic_data), 10)
        logger.info(f"Échantillonnage de {sample_size} questions du dataset.")

        for item in synthetic_data[:sample_size]:
            question = item["question"]
            logger.info(f"Interrogation du RAG ({target_theme}) pour : {question}")
            response = engine.ask(question, theme=target_theme)

            # On retire les sources du texte de la réponse pour l'évaluation de fidélité
            answer_clean = str(response).split("\n\nSources :")[0]

            audit_data.append(
                {
                    "question": question,
                    "answer": answer_clean,
                    "contexts": [node.get_content() for node in response.source_nodes]
                    if hasattr(response, "source_nodes")
                    else [],
                    "ground_truth": item["ground_truth"],
                }
            )
    else:
        logger.info("Extraction des traces depuis Phoenix...")
        try:
            client = px.Client(endpoint="http://localhost:6006")
            spans_df = client.get_spans_dataframe()

            if spans_df is not None and not spans_df.empty:
                # Filter for Query Engine spans
                chains = spans_df[spans_df["span_kind"] == "CHAIN"]

                for _, row in chains.iterrows():
                    query = row.get("attributes.input.value")
                    response = row.get("attributes.output.value")

                    if (
                        isinstance(query, str)
                        and not query.startswith("{")
                        and isinstance(response, str)
                        and not response.startswith("{")
                    ):
                        trace_id = row.get("context.trace_id")

                        context = []
                        retriever_spans = spans_df[
                            (spans_df["context.trace_id"] == trace_id)
                            & (spans_df["span_kind"] == "RETRIEVER")
                        ]
                        for _, r_span in retriever_spans.iterrows():
                            docs = r_span.get("attributes.retrieval.documents", [])
                            if docs:
                                for doc in docs:
                                    if isinstance(doc, dict):
                                        context.append(doc.get("document.content", ""))
                                    else:
                                        context.append(str(doc))

                        if query and response and context:
                            audit_data.append(
                                {
                                    "question": query,
                                    "answer": response,
                                    "contexts": context,
                                    "ground_truth": "N/A",
                                }
                            )

                    if len(audit_data) >= 20:
                        break
        except Exception as e:
            logger.warning(f"Impossible de récupérer les traces Phoenix : {e}.")

    # 3. Fallback si aucune donnée
    if not audit_data:
        logger.info("Utilisation d'un échantillon de fallback.")
        audit_data = [
            {
                "question": "Quelles sont les thèses sur l'intelligence artificielle ?",
                "answer": "L'intelligence artificielle est un domaine incluant l'apprentissage automatique.",
                "contexts": [
                    "L'intelligence artificielle inclut l'apprentissage automatique."
                ],
                "ground_truth": "L'IA inclut le machine learning.",
            }
        ]

    # 4. Évaluation Ragas
    try:
        dataset = Dataset.from_dict(
            {
                "question": [d["question"] for d in audit_data],
                "answer": [d["answer"] for d in audit_data],
                "contexts": [d["contexts"] for d in audit_data],
                "ground_truth": [d["ground_truth"] for d in audit_data],
            }
        )

        metrics = [faithfulness, answer_relevancy, context_precision, context_recall]
        logger.info(f"Lancement de l'évaluation sur {len(audit_data)} items...")

        from ragas.llms import LlamaIndexLLMWrapper
        from ragas.embeddings import LlamaIndexEmbeddingsWrapper

        result = evaluate(
            dataset=dataset,
            metrics=metrics,
            llm=LlamaIndexLLMWrapper(Settings.llm),
            embeddings=LlamaIndexEmbeddingsWrapper(Settings.embed_model),
        )

        # 5. Rapport & Phoenix Export
        now = datetime.now()
        report_date_str = now.strftime("%Y-%m-%d")
        report_time_str = now.strftime("%H-%M-%S")
        report_filename = f"audit_{report_time_str}.md"
        report_dir = f"docs/AUDITS/{report_date_str}"
        report_path = f"{report_dir}/{report_filename}"
        ensure_dir(report_dir)

        avg_latencies = {}
        try:
            client = px.Client(endpoint="http://localhost:6006")
            spans_df = client.get_spans_dataframe()
            if spans_df is not None and not spans_df.empty:
                spans_df["duration"] = (
                    spans_df["end_time"] - spans_df["start_time"]
                ).dt.total_seconds()
                avg_latencies = (
                    spans_df.groupby("span_kind")["duration"].mean().to_dict()
                )
        except Exception:
            pass

        with open(report_path, "w") as f:
            f.write("# 📊 Rapport d'Audit Holistique RAG\n")
            f.write(f"**Date** : {report_date_str} | **Heure** : {report_time_str}\n")
            f.write(
                f"**Thème** : `{collection if collection else 'default'}` | **Mode** : `{mode}`\n\n"
            )

            f.write("## 🛡️ Résumé de la Qualité (RAGAS)\n\n")
            f.write("| Métrique | Score | État |\n| :--- | :--- | :--- |\n")

            try:
                # Normalisation des scores (PBI-091 Correction Bloquant)
                raw_scores = result.scores if hasattr(result, "scores") else result

                # Si c'est un dataset ou une liste (cas Ragas récent), on extrait le premier élément
                if hasattr(raw_scores, "to_list"):
                    raw_scores = raw_scores.to_list()

                if isinstance(raw_scores, list) and len(raw_scores) > 0:
                    scores = raw_scores[0]
                else:
                    scores = raw_scores

                # Conversion systématique en float Python natif (np.float64 -> float)
                if isinstance(scores, dict):
                    clean_scores = {}
                    for k, v in scores.items():
                        if hasattr(v, "item"):  # NumPy
                            clean_scores[k] = float(v.item())
                        else:
                            try:
                                clean_scores[k] = float(v)
                            except:
                                clean_scores[k] = v
                    scores = clean_scores

                if isinstance(scores, dict):
                    # On garde la ligne | Global | ... pour le cockpit admin
                    f.write(f"| Global | {scores} | - |\n")
                    for metric, score in scores.items():
                        status = (
                            "✅"
                            if isinstance(score, (int, float)) and score > 0.85
                            else "⚠️"
                            if isinstance(score, (int, float)) and score > 0.7
                            else "🚨"
                        )
                        if isinstance(score, (int, float)):
                            f.write(f"| {metric} | **{score:.4f}** | {status} |\n")
                        else:
                            f.write(f"| {metric} | {score} | - |\n")
                else:
                    f.write(f"| Score Global | {scores} | - |\n")
            except Exception as e:
                logger.warning(f"Erreur lors de la normalisation des scores : {e}")
                f.write(f"| Résultat | {result} | |\n")

            f.write("\n## ⏱️ Performance & Latence\n\n")
            f.write("| Étape | Temps Moyen (s) | Graphique |\n| :--- | :--- | :--- |\n")
            for kind, duration in avg_latencies.items():
                bar = "█" * int(duration * 10) if duration > 0.1 else "░"
                f.write(f"| {kind} | {duration:.3f}s | `{bar}` |\n")

            f.write("\n## 📝 Détails par Question\n\n")
            try:
                if hasattr(result, "to_pandas"):
                    df_res = result.to_pandas()
                    for i, row in df_res.iterrows():
                        q = row.get("question", f"Question {i}")
                        f.write(f"### Q{i + 1}: {q}\n")
                        f.write(
                            f"**Réponse** : {row.get('answer', 'N/A')[:200]}...\n\n"
                        )
                        for col in df_res.columns:
                            if col not in [
                                "question",
                                "answer",
                                "contexts",
                                "ground_truth",
                            ]:
                                val = row[col]
                                star = (
                                    "⭐"
                                    if isinstance(val, (int, float)) and val > 0.8
                                    else ""
                                )
                                f.write(f"- **{col}**: {val} {star}\n")
                        f.write("\n---\n")
            except Exception:
                pass

        logger.info(f"Rapport local généré : {report_path}")

        # 6. Export vers MinIO
        try:
            from src.ingestion.theses_client import ThesesClient

            t_client = ThesesClient()
            if t_client.fs:
                bucket_reports = "reports"
                remote_dir = f"{bucket_reports}/{report_date_str}"
                if not t_client.fs.exists(remote_dir):
                    t_client.fs.makedirs(remote_dir)
                remote_path = f"{remote_dir}/{report_filename}"
                with t_client.fs.open(remote_path, "w") as f_remote:
                    with open(report_path, "r") as f_local:
                        f_remote.write(f_local.read())
                logger.info(f"🚀 Rapport exporté vers MinIO : {remote_path}")
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Erreur durant l'audit : {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Audit de qualité RAG avec Ragas")
    parser.add_argument("--path", help="Chemin vers le fichier de dataset (JSON)")
    parser.add_argument("--theme", help="Thème (collection Qdrant) à auditer")
    parser.add_argument(
        "--mode",
        choices=["lab", "terrain"],
        default="lab",
        help="Mode d'audit : lab (dataset) ou terrain (traces)",
    )
    args = parser.parse_args()
    run_audit(args.path, args.theme, args.mode)
