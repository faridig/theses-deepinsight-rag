
import os
import json
import logging
import asyncio
from dotenv import load_dotenv
from src.generation.rag_engine import RAGEngine
from src.evaluation.evaluator import ThesesEvaluator

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    load_dotenv()
    
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("COHERE_API_KEY"):
        logger.error("Clés API manquantes (OPENAI_API_KEY ou COHERE_API_KEY).")
        return

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
    # Note: Ragas evaluate pour LlamaIndex est synchrone mais utilise de l'async en interne
    try:
        results = evaluator.evaluate_engine(engine.query_engine, dataset)
        
        # 5. Affichage des résultats
        print("\n=== RÉSULTATS DE L'ÉVALUATION RAGAS ===")
        print(results)
        
        # 6. Export vers Phoenix
        evaluator.export_to_phoenix(results)
        
        # Sauvegarde locale
        with open("evaluation_report.json", "w", encoding="utf-8") as f:
            json.dump(results.scores, f, indent=4)
        logger.info("Rapport d'évaluation sauvegardé dans evaluation_report.json")
        
    except Exception as e:
        logger.error(f"Échec de l'évaluation : {e}")

if __name__ == "__main__":
    asyncio.run(main())
