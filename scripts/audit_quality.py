import os
import sys
import logging
import json
from datetime import datetime
from datasets import Dataset

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import phoenix as px
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
)
from llama_index.core import Settings
from src.config import setup_settings
from src.generation.rag_engine import RAGEngine

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("audit_quality")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def run_audit(dataset_path=None, collection=None):
    logger.info("Démarrage de l'audit de qualité Ragas...")
    
    # 1. Initialisation de l'environnement
    setup_settings()
    
    audit_data = []
    
    # 2. Collecte des données (Synthétique ou Phoenix)
    if dataset_path and os.path.exists(dataset_path):
        logger.info(f"Chargement du dataset synthétique depuis {dataset_path}...")
        with open(dataset_path, "r", encoding="utf-8") as f:
            synthetic_data = json.load(f)
            
        engine = RAGEngine()
        # On utilise la collection spécifiée si fournie
        target_theme = collection if collection else engine.default_collection
        
        for item in synthetic_data[:5]: # Échantillonnage 10% de 50 (Decision 17.2)
            question = item["question"]
            logger.info(f"Interrogation du RAG ({target_theme}) pour : {question}")
            response = engine.ask(question, theme=target_theme)
            
            # On retire les sources du texte de la réponse pour l'évaluation de fidélité
            answer_clean = str(response).split("\n\nSources :")[0]
            
            audit_data.append({
                "question": question,
                "answer": answer_clean,
                "contexts": [node.get_content() for node in response.source_nodes] if hasattr(response, "source_nodes") else [],
                "ground_truth": item["ground_truth"]
            })
    else:
        logger.info("Extraction des traces depuis Phoenix...")
        try:
            client = px.Client(endpoint="http://localhost:6006")
            spans_df = client.get_spans_dataframe()
            
            if spans_df is not None and not spans_df.empty:
                # Filter for Query Engine spans (usually the ones with input.value being a string and no parent)
                chains = spans_df[spans_df['span_kind'] == "CHAIN"]
                
                for _, row in chains.iterrows():
                    query = row.get('attributes.input.value')
                    response = row.get('attributes.output.value')
                    
                    # We want the main query, not the internal ones with JSON inputs
                    if isinstance(query, str) and not query.startswith('{') and isinstance(response, str) and not response.startswith('{'):
                        trace_id = row.get('context.trace_id')
                        
                        # Find context for this trace
                        context = []
                        retriever_spans = spans_df[(spans_df['context.trace_id'] == trace_id) & (spans_df['span_kind'] == "RETRIEVER")]
                        for _, r_span in retriever_spans.iterrows():
                            docs = r_span.get('attributes.retrieval.documents', [])
                            if docs:
                                for doc in docs:
                                    if isinstance(doc, dict):
                                        context.append(doc.get('document.content', ''))
                                    else:
                                        context.append(str(doc))
                        
                        if query and response and context:
                            audit_data.append({
                                "question": query,
                                "answer": response,
                                "contexts": context,
                                "ground_truth": "N/A"
                            })
                    
                    if len(audit_data) >= 20: 
                        break
        except Exception as e:
            logger.warning(f"Impossible de récupérer les traces Phoenix : {e}. Utilisation du fallback.")
            import traceback
            logger.warning(traceback.format_exc())

    # 3. Fallback si aucune donnée
    if not audit_data:
        logger.info("Utilisation d'un échantillon de fallback.")
        audit_data = [
            {
                "question": "Quelles sont les thèses sur l'intelligence artificielle ?",
                "answer": "L'intelligence artificielle est un domaine incluant l'apprentissage automatique.",
                "contexts": ["L'intelligence artificielle inclut l'apprentissage automatique."],
                "ground_truth": "L'IA inclut le machine learning."
            }
        ]

    # 4. Évaluation Ragas
    try:
        dataset = Dataset.from_dict({
            "question": [d["question"] for d in audit_data],
            "answer": [d["answer"] for d in audit_data],
            "contexts": [d["contexts"] for d in audit_data],
            "ground_truth": [d["ground_truth"] for d in audit_data]
        })

        metrics = [faithfulness, answer_relevancy, context_precision]
        logger.info(f"Lancement de l'évaluation sur {len(audit_data)} items...")
        
        from ragas.llms import LlamaIndexLLMWrapper
        from ragas.embeddings import LlamaIndexEmbeddingsWrapper
        
        result = evaluate(
            dataset=dataset, 
            metrics=metrics,
            llm=LlamaIndexLLMWrapper(Settings.llm),
            embeddings=LlamaIndexEmbeddingsWrapper(Settings.embed_model)
        )
        
        # 5. Rapport
        now = datetime.now()
        report_date_str = now.strftime("%Y-%m-%d")
        report_time_str = now.strftime("%H-%M-%S")
        report_filename = f"audit_{report_time_str}.md"
        report_dir = f"docs/AUDITS/{report_date_str}"
        report_path = f"{report_dir}/{report_filename}"
        ensure_dir(report_dir)
        
        # Latency analysis
        client = px.Client(endpoint="http://localhost:6006")
        spans_df = client.get_spans_dataframe()
        avg_latencies = {}
        if spans_df is not None and not spans_df.empty:
            spans_df['duration'] = (spans_df['end_time'] - spans_df['start_time']).dt.total_seconds()
            avg_latencies = spans_df.groupby('span_kind')['duration'].mean().to_dict()

        with open(report_path, "w") as f:
            f.write(f"# 📊 Rapport d'Audit Holistique RAG\n")
            f.write(f"**Date** : {report_date_str} | **Heure** : {report_time_str}\n\n")
            
            f.write("## 🛡️ Résumé de la Qualité (RAGAS)\n\n")
            f.write("| Métrique | Score | État |\n| :--- | :--- | :--- |\n")
            
            try:
                # Gestion robuste du résultat Ragas
                if isinstance(result, dict):
                    scores = result
                elif hasattr(result, "scores") and isinstance(result.scores, dict):
                    scores = result.scores
                else:
                    scores = result # Fallback
                
                if isinstance(scores, dict):
                    # On garde la ligne | Global | ... pour le cockpit admin
                    f.write(f"| Global | {scores} | - |\n")
                    for metric, score in scores.items():
                        status = "✅" if score > 0.85 else "⚠️" if score > 0.7 else "🚨"
                        f.write(f"| {metric} | **{score:.4f}** | {status} |\n")
                else:
                    f.write(f"| Score Global | {scores} | - |\n")
            except Exception as e:
                logger.warning(f"Erreur lors de l'écriture des scores : {e}")
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
                        q = row.get('question', f"Question {i}")
                        f.write(f"### Q{i+1}: {q}\n")
                        f.write(f"**Réponse** : {row.get('answer', 'N/A')[:200]}...\n\n")
                        for col in df_res.columns:
                            if col not in ['question', 'answer', 'contexts', 'ground_truth']:
                                val = row[col]
                                star = "⭐" if isinstance(val, (int, float)) and val > 0.8 else ""
                                f.write(f"- **{col}**: {val} {star}\n")
                        f.write("\n---\n")
                else:
                    f.write("Détails non disponibles sous forme de tableau.\n")
            except Exception as e:
                logger.warning(f"Détails non disponibles : {e}")

        logger.info(f"Rapport local généré : {report_path}")
        
        # 6. Export vers MinIO (PBI-043 + PBI-050 hierarchy)
        try:
            from src.ingestion.theses_client import ThesesClient
            t_client = ThesesClient()
            if t_client.fs:
                bucket_reports = "reports"
                # Hiérarchie /reports/YYYY-MM-DD/
                remote_dir = f"{bucket_reports}/{report_date_str}"
                if not t_client.fs.exists(remote_dir):
                    t_client.fs.makedirs(remote_dir)
                
                remote_path = f"{remote_dir}/{report_filename}"
                with t_client.fs.open(remote_path, "w") as f_remote:
                    with open(report_path, "r") as f_local:
                        f_remote.write(f_local.read())
                
                logger.info(f"🚀 Rapport exporté vers MinIO : {remote_path}")
        except Exception as export_err:
            logger.warning(f"Impossible d'exporter le rapport vers MinIO : {export_err}")
        
    except Exception as e:
        logger.error(f"Erreur durant l'audit : {e}")

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    collection = sys.argv[2] if len(sys.argv) > 2 else None
    run_audit(path, collection)
