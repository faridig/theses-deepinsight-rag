import os
import json
import logging
import asyncio
import warnings
from dotenv import load_dotenv
from llama_index.core import set_global_handler
from src.generation.rag_engine import RAGEngine
from src.evaluation.evaluator import ThesesEvaluator

# Silence Technique Radical (Directive Alpha)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

for lib in ["opentelemetry", "ragas", "pydantic", "httpx", "urllib3", "chromadb", "bm25s", "llama_index", "openai", "cohere"]:
    logging.getLogger(lib).setLevel(logging.ERROR)

warnings.filterwarnings("ignore")

def setup_phoenix():
    """Initialise Phoenix proprement (arize-phoenix)."""
    if os.getenv("DISABLE_PHOENIX") == "1":
        return None

    try:
        import phoenix as px
        # On tente de lancer ou de récupérer la session
        session = px.launch_app()
        set_global_handler("arize_phoenix")
        if session:
            logger.info(f"Phoenix actif: {session.url}")
        return session
    except Exception as e:
        # Pas de traceback en console (Directive Alpha)
        return None

async def main():
    load_dotenv()
    
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("COHERE_API_KEY"):
        logger.error("Clés API manquantes.")
        return

    setup_phoenix()

    logger.info("Démarrage du moteur RAG...")
    try:
        engine = RAGEngine()
    except Exception as e:
        logger.error(f"Échec initialisation moteur: {e}")
        return
    
    dataset_path = "data/golden_dataset.json"
    if not os.path.exists(dataset_path):
        logger.error(f"Dataset introuvable: {dataset_path}")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    
    evaluator = ThesesEvaluator()
    
    try:
        results = evaluator.evaluate_engine(engine.query_engine, dataset)
        
        if results:
            print("\n=== SYNTHÈSE ÉVALUATION ===")
            evaluator.export_to_phoenix(results)
            
            with open("evaluation_report.json", "w", encoding="utf-8") as f:
                json.dump(results.scores, f, indent=4)
        else:
            logger.error("L'évaluation n'a retourné aucun résultat.")
            
    except Exception as e:
        # Silence total sur les tracebacks
        if "429" in str(e):
            logger.error("Arrêt: Limite de taux API atteinte (429).")
        else:
            logger.error(f"Interruption de l'évaluation: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
