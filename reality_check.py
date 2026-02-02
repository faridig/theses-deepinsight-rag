
import sys
import logging
from src.generation.rag_engine import RAGEngine

# Configuration du logging pour voir les sorties
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

def test_reality():
    print("--- DÉBUT DU TEST DE RÉALITÉ ---")
    try:
        engine = RAGEngine(storage_path="./storage", collection_name="theses_collection")
        print("Engine initialisé avec succès.")
        
        # On ne va pas forcément faire un appel réseau si on veut juste tester l'initialisation
        # Mais le plan demande de vérifier la Fusion et le Reranking.
        # Faisons un appel simulé ou court si possible.
        # Pour éviter de consommer trop de crédits, on peut juste vérifier l'initialisation pour l'instant
        # ou faire une question très simple.
        
        question = "Quels sont les thèmes principaux des thèses ?"
        print(f"Question : {question}")
        response = engine.ask(question)
        print(f"Réponse : {response}")
        
    except Exception as e:
        print(f"ERREUR CRITIQUE lors de l'initialisation : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    print("--- FIN DU TEST DE RÉALITÉ ---")

if __name__ == "__main__":
    test_reality()
