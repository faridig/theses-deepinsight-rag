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
            spans_df = client.get_spans_dataframe(filter_condition='span_kind == "CHAIN"')
            
            if spans_df is not None and not spans_df.empty:
                for _, row in spans_df.iterrows():
                    attributes = row.get('attributes', {})
                    if attributes is None:
                        continue
                    
                    query = attributes.get('input.value') or attributes.get('query_str')
                    response = attributes.get('output.value') or attributes.get('response')
                    
                    context = []
                    trace_id = row.get('context.trace_id')
                    if trace_id:
                        try:
                            retriever_spans = client.get_spans_dataframe(
                                filter_condition=f'trace_id == "{trace_id}" and span_kind == "RETRIEVER"'
                            )
                            if retriever_spans is not None:
                                for _, r_span in retriever_spans.iterrows():
                                    r_attr = r_span.get('attributes', {})
                                    if r_attr is None:
                                        continue
                                    docs = r_attr.get('retrieval.documents', [])
                                    for doc in docs:
                                        if isinstance(doc, dict):
                                            context.append(doc.get('document.content', ''))
                                        else:
                                            context.append(str(doc))
                        except Exception:
                            pass
                    
                    if query and response and context:
                        audit_data.append({
                            "question": query,
                            "answer": response,
                            "contexts": context,
                            "ground_truth": "N/A"
                        })
                    if len(audit_data) >= 10:
                        break
        except Exception as e:
            logger.warning(f"Impossible de récupérer les traces Phoenix : {e}. Utilisation du fallback.")

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
        
        # Correction Lesson Learned: Ragas attend embed_query et LLM wrapper
        from ragas.llms import LlamaIndexLLMWrapper
        from ragas.embeddings import LlamaIndexEmbeddingsWrapper
        from llama_index.core import Settings
        
        # On passe explicitement les modèles à evaluate pour éviter les conflits
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
        
        with open(report_path, "w") as f:
            f.write(f"# Rapport d'Audit Qualité RAG - {report_date}\n\n")
            f.write("## Résumé des Scores Ragas\n\n")
            f.write("| Métrique | Score |\n| :--- | :--- |\n")
            
            # Gestion robuste du résultat
            try:
                # result se comporte comme un dict pour les scores globaux
                for metric, score in result.items():
                    f.write(f"| {metric} | {score:.4f} |\n")
            except Exception as e:
                logger.warning(f"Erreur lors de l'écriture des scores : {e}")
                f.write(f"| Global | {result} |\n")
            
            f.write("\n## Détails par Question\n\n")
            try:
                df_res = result.to_pandas()
                for i, row in df_res.iterrows():
                    q = row.get('question', f"Question {i}")
                    f.write(f"### Q: {q}\n")
                    # Afficher toutes les métriques
                    for col in df_res.columns:
                        if col not in ['question', 'answer', 'contexts', 'ground_truth']:
                            f.write(f"- **{col}**: {row[col]}\n")
                    f.write("\n")
            except Exception as e:
                logger.warning(f"Détails non disponibles : {e}")
                f.write("Détails non disponibles sous forme de tableau.\n")

        logger.info(f"Rapport généré : {report_path}")
        
    except Exception as e:
        logger.error(f"Erreur durant l'audit : {e}")

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    run_audit(path)
