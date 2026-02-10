import os
import sys
import logging
from dotenv import load_dotenv

# Ajout du chemin racine pour l'import des modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.generation.rag_engine import RAGEngine
from src.evaluation.evaluator import RagasEvaluator, RagasTestItem

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def test_ragas_evaluation_execution():
    """
    Script de test pour valider le RAG avec Ragas.
    """
    logger.info("Initialisation du moteur RAG...")
    # Skip if no API keys
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("COHERE_API_KEY"):
        logger.warning("Clés API manquantes, saut du test Ragas.")
        return

    try:
        engine = RAGEngine()
        evaluator = RagasEvaluator(engine)
    except Exception as e:
        logger.error(f"Erreur d'initialisation : {e}")
        return

    # Golden Dataset - 3 questions pour le test rapide
    test_items = [
        RagasTestItem(
            query_str="Quels sont les impacts de l'intelligence artificielle sur le système scientifique ?",
            expected_response="L'IA affecte la production de connaissances, son originalité et l'impact scientifique associé.",
            expected_context=["impact of artificial intelligence (AI) on the scientific system"]
        ),
        RagasTestItem(
            query_str="Qui a popularisé le terme Knowledge Graph en 2012 ?",
            expected_response="Google a popularisé le terme Knowledge Graph en 2012.",
            expected_context=["popularisé qu’en 2012 lorsque Google a présenté son propre KG"]
        ),
        RagasTestItem(
            query_str="Qu'est-ce que Novelpy ?",
            expected_response="Novelpy est un outil open-source basé sur Python qui calcule divers indicateurs de nouveauté et de disruption.",
            expected_context=["Novelpy, un outil open-source basé sur Python"]
        )
    ]

    logger.info(f"Lancement de l'évaluation sur {len(test_items)} questions...")
    results = evaluator.run_evaluation(test_items)
    
    print("\n=== RÉSULTATS DE L'ÉVALUATION RAGAS ===")
    print(results)
    print("=======================================\n")

    assert results is not None
    assert "faithfulness" in results

if __name__ == "__main__":
    test_ragas_evaluation_execution()
