
import os
import json
import logging
import asyncio
from dotenv import load_dotenv
from llama_index.core import set_global_handler
from src.generation.rag_engine import RAGEngine
from src.evaluation.evaluator import ThesesEvaluator

# Configuration des logs - Silence Technique strict
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Silence sélectif pour réduire la pollution visuelle
SILENT_LOGGERS = [
    "opentelemetry", "ragas", "pydantic", "httpx", "urllib3", 
    "chromadb", "bm25s", "llama_index", "openai"
]
for logger_name in SILENT_LOGGERS:
    logging.getLogger(logger_name).setLevel(logging.ERROR)

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

def setup_phoenix():
    """Initialise Phoenix pour capturer les traces de l'évaluation."""
    if os.getenv("DISABLE_PHOENIX") == "1":
        logger.info("Phoenix désactivé via variable d'environnement.")
        return

    try:
        import phoenix as px
        # On tente de se connecter à une instance existante ou on lance
        try:
            px.active_session()
        except Exception:
            try:
                px.launch_app()
            except Exception as e:
                logger.warning(f"Échec du lancement de Phoenix : {e}")
                return
        
        try:
            set_global_handler("arize_phoenix")
            logger.info("Observabilité Phoenix activée pour l'évaluation.")
        except Exception as e:
            logger.warning(f"Échec de l'activation du handler Phoenix : {e}")
    except ImportError:
        logger.warning("Phoenix n'est pas installé.")
    except Exception as e:
        logger.warning(f"Impossible d'activer Phoenix : {e}")

async def main():
    load_dotenv()
    
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("COHERE_API_KEY"):
        logger.error("Clés API manquantes (OPENAI_API_KEY ou COHERE_API_KEY).")
        return

    # Configuration de l'observabilité
    setup_phoenix()

    # 1. Initialisation du moteur RAG
    logger.info("Initialisation du moteur RAG...")
    engine = RAGEngine()
    
    # 2. Chargement du Golden Dataset
    logger.info("Chargement du Golden Dataset...")
    dataset_path = "data/golden_dataset.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    
    # 3. Initialisation de l'évaluateur
    logger.info("Initialisation de l'évaluateur Ragas...")
    evaluator = ThesesEvaluator()
    
    # 4. Exécution de l'évaluation
    try:
        results = evaluator.evaluate_engine(engine.query_engine, dataset)
        
        if results:
            print("\n=== RÉSULTATS DE L'ÉVALUATION RAGAS ===")
            print(results)
            
            evaluator.export_to_phoenix(results)
            
            with open("evaluation_report.json", "w", encoding="utf-8") as f:
                json.dump(results.scores, f, indent=4)
            logger.info("Rapport d'évaluation sauvegardé.")
        else:
            logger.error("L'évaluation n'a produit aucun résultat.")
            
    except Exception as e:
        logger.error(f"Échec critique de l'évaluation : {e}")
        # On ne re-raise pas pour éviter le traceback en console

if __name__ == "__main__":
    asyncio.run(main())
