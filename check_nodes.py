
import os
from src.generation.rag_engine import RAGEngine

def check_nodes():
    engine = RAGEngine()
    nodes = list(engine.index.docstore.docs.values())
    print(f"Nombre de nodes dans le docstore : {len(nodes)}")

if __name__ == "__main__":
    check_nodes()
