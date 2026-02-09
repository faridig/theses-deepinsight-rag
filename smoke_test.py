import os
import sys
from src.generation.rag_engine import RAGEngine

def main():
    os.environ["DISABLE_PHOENIX"] = "1"
    try:
        engine = RAGEngine()
        # Question qui devrait générer des sources
        response = engine.ask("Qu'est-ce que l'IA ?")
        print("\n=== REPONSE RAG ===")
        print(response)
        print("=== FIN REPONSE ===")
        
        if "Sources:" in str(response):
            print("\n✅ Bloc Sources détecté (PBI-012).")
        else:
            print("\n❌ Bloc Sources manquant.")
            
    except Exception as e:
        print(f"Erreur: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
