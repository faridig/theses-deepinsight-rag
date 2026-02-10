
from src.generation.rag_engine import RAGEngine
from dotenv import load_dotenv

def test_rag():
    load_dotenv()
    engine = RAGEngine()
    response = engine.ask("Quel est le sujet principal de la thèse ?")
    print(f"\n--- REPONSE ---\n{response}")

if __name__ == "__main__":
    test_rag()
