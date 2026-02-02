
import os
from unittest.mock import MagicMock
from src.generation.rag_engine import RAGEngine
from llama_index.core.schema import NodeWithScore, TextNode

def test_cohere_crash_no_key():
    print("--- TEST ROBUSTESSE COHERE SANS CLÉ ---")
    os.environ["COHERE_API_KEY"] = ""
    try:
        engine = RAGEngine(storage_path="./storage", collection_name="theses_collection")
        
        # Simuler des nodes récupérés
        nodes = [
            NodeWithScore(node=TextNode(text="Test content 1", metadata={"window": "Test window 1"}), score=0.8),
            NodeWithScore(node=TextNode(text="Test content 2", metadata={"window": "Test window 2"}), score=0.7)
        ]
        
        print("Tentative de reranking avec 0 nodes...")
        # Si la liste est vide, ça devrait passer
        engine.reranker.postprocess_nodes([], query_bundle=MagicMock())
        print("Ok avec 0 nodes.")
        
        print("Tentative de reranking avec des nodes...")
        # Si la liste n'est pas vide, CohereRerank va tenter d'appeler l'API
        # S'il n'y a pas de clé, ça devrait crasher
        try:
            engine.reranker.postprocess_nodes(nodes, query_bundle=MagicMock(query_str="test"))
            print("Surprenant : pas de crash sans clé !")
        except Exception as e:
            print(f"Crash attendu et intercepté : {e}")
            
    except Exception as e:
        print(f"Erreur inattendue : {e}")
    print("--- FIN DU TEST ROBUSTESSE ---")

if __name__ == "__main__":
    test_cohere_crash_no_key()
