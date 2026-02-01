
from src.generation.rag_engine import RAGEngine
import os

# Ensure we have a mock index if real one is empty
def test_phoenix_trace():
    print("Initialisation du RAGEngine...")
    try:
        engine = RAGEngine()
        print("Moteur initialisé. Exécution d'une requête HyDE...")
        # We don't really care about the answer, just the execution flow
        response = engine.ask("Qu'est-ce que l'IA ?")
        print(f"Réponse reçue: {str(response)[:100]}...")
        print("Succès de l'exécution.")
    except Exception as e:
        print(f"Erreur lors du test: {e}")

if __name__ == "__main__":
    test_phoenix_trace()
