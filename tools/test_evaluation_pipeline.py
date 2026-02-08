
import asyncio
from dotenv import load_dotenv
from src.generation.rag_engine import RAGEngine
from src.evaluation.evaluator import ThesesEvaluator

async def main():
    load_dotenv()
    engine = RAGEngine()
    
    dataset = [
        {
            "question": "Quel est l'objectif principal de la thèse 2023STRAB011 ?",
            "ground_truth": "L'objectif de cette thèse est d'analyser les mécanismes de transfert thermique dans les nanomatériaux."
        }
    ]
    
    evaluator = ThesesEvaluator()
    print("Démarrage de l'évaluation sur 1 question...")
    results = evaluator.evaluate_engine(engine.query_engine, dataset)
    
    if results:
        print("\n=== RÉSULTATS ÉVALUATION TEST ===")
        print(results)
    else:
        print("Échec de l'évaluation.")

if __name__ == "__main__":
    asyncio.run(main())
