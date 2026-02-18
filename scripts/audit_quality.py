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

def run_audit(dataset_path=None):
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
        for item in synthetic_data[:5]: # Limité à 5 pour l'audit rapide
            question = item["question"]
            logger.info(f"Interrogation du RAG pour : {question}")
            response = engine.ask(question)
            
            audit_data.append({
                "question": question,
                "answer": str(response).split("\n\nSources :")[0],
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
        report_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_path = f"docs/AUDITS/audit_{report_date}.md"
        ensure_dir("docs/AUDITS")
        
        # Latency analysis
        client = px.Client(endpoint="http://localhost:6006")
        spans_df = client.get_spans_dataframe()
        avg_latencies = {}
        if spans_df is not None and not spans_df.empty:
            spans_df['duration'] = (spans_df['end_time'] - spans_df['start_time']).dt.total_seconds()
            avg_latencies = spans_df.groupby('span_kind')['duration'].mean().to_dict()

        with open(report_path, "w") as f:
            f.write(f"# Rapport d'Audit Holistique RAG - {report_date}\n\n")
            
            f.write("## 1. Analyse de Latence (Moyenne par étape)\n\n")
            f.write("| Étape | Temps Moyen (s) |\n| :--- | :--- |\n")
            for kind, duration in avg_latencies.items():
                f.write(f"| {kind} | {duration:.3f}s |\n")
            
            f.write("\n## Résumé des Scores Ragas\n\n")
            f.write("| Métrique | Score |\n| :--- | :--- |\n")
            
            try:
                scores = result.scores if hasattr(result, "scores") else result
                for metric, score in scores.items():
                    f.write(f"| {metric} | {score:.4f} |\n")
            except Exception as e:
                logger.warning(f"Erreur lors de l'écriture des scores : {e}")
                f.write(f"| Global | {result} |\n")
            
            f.write("\n## 3. Détails par Question\n\n")
            try:
                if hasattr(result, "to_pandas"):
                    df_res = result.to_pandas()
                    for i, row in df_res.iterrows():
                        q = row.get('question', f"Question {i}")
                        f.write(f"### Q: {q}\n")
                        for col in df_res.columns:
                            if col not in ['question', 'answer', 'contexts', 'ground_truth']:
                                f.write(f"- **{col}**: {row[col]}\n")
                        f.write("\n")
                else:
                    f.write("Détails non disponibles sous forme de tableau.\n")
            except Exception as e:
                logger.warning(f"Détails non disponibles : {e}")

        logger.info(f"Rapport généré : {report_path}")
        
    except Exception as e:
        logger.error(f"Erreur durant l'audit : {e}")

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    run_audit(path)
