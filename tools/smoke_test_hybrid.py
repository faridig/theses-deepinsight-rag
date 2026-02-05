
import logging
from src.generation.rag_engine import RAGEngine

# Silence lower level logs to see if our engine is clean
logging.basicConfig(level=logging.INFO)

def smoke_test():
    print("=== SMOKE TEST: RAGEngine Hybrid Search ===")
    try:
        # 1. Test Initialization
        print("\n--- Initialisation du RAGEngine ---")
        engine = RAGEngine(storage_path="./storage/chroma", collection_name="theses_collection")
        
        # Verify Hybrid Search setup
        if hasattr(engine, 'fusion_retriever'):
            print("✅ QueryFusionRetriever détecté.")
            num_retrievers = len(engine.fusion_retriever._retrievers)
            print(f"✅ Nombre de retrievers : {num_retrievers}")
            if num_retrievers >= 2:
                print("✅ Recherche Hybride (Vector + BM25) confirmée.")
            else:
                print("❌ Un seul retriever détecté. BM25 possiblement manquant.")
        else:
            print("❌ QueryFusionRetriever manquant dans l'engine.")

        # 2. Test Real Query (Smoke Test)
        # On utilise une question simple pour vérifier que la chaîne fonctionne
        question = "Quels sont les thèmes principaux des thèses ?"
        print(f"\n--- Test de Requête : '{question}' ---")
        
        import time
        start_time = time.time()
        # On va capturer les logs pour vérifier la pollution
        response = engine.ask(question)
        end_time = time.time()
        
        print(f"\n--- Réponse reçue (en {end_time - start_time:.2f}s) ---")
        print(response)
        
        if response and not str(response).startswith("Une erreur est survenue"):
            print("\n✅ Requête réussie.")
        else:
            print("\n❌ Échec de la requête.")

    except Exception as e:
        print(f"\n❌ CRASH LORS DU SMOKE TEST : {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    smoke_test()
