
import os
import logging
from src.generation.rag_engine import RAGEngine
from llama_index.core.settings import Settings

logging.basicConfig(level=logging.INFO)

def debug_retrieval():
    engine = RAGEngine()
    query = "Quel est l'objectif principal de la thèse 2023STRAB011 ?"
    
    print(f"\n--- DEBUG RETRIEVAL FOR: {query} ---")
    
    # 1. Test Vector Retriever alone
    print("\n[Vector Retriever Only]")
    vector_retriever = engine.index.as_retriever(similarity_top_k=5)
    nodes = vector_retriever.retrieve(query)
    for i, n in enumerate(nodes):
        print(f"{i+1}. [Score: {n.score:.4f}] ID: {n.node.metadata.get('id')} - Titre: {n.node.metadata.get('titre')}")
        # print(f"   Text: {n.node.get_content()[:100]}...")

    # 2. Test BM25 Retriever alone
    print("\n[BM25 Retriever Only]")
    # We need to access the bm25_retriever from the fusion_retriever if possible, or recreate it
    # Fusion retriever has a list of retrievers
    bm25_retriever = engine.fusion_retriever._retrievers[1] if len(engine.fusion_retriever._retrievers) > 1 else None
    if bm25_retriever:
        nodes = bm25_retriever.retrieve(query)
        for i, n in enumerate(nodes):
            print(f"{i+1}. [Score: {n.score:.4f}] ID: {n.node.metadata.get('id')} - Titre: {n.node.metadata.get('titre')}")
    else:
        print("BM25 retriever not found")

    # 3. Test Fusion Retriever
    print("\n[Fusion Retriever]")
    nodes = engine.fusion_retriever.retrieve(query)
    for i, n in enumerate(nodes):
        print(f"{i+1}. [Score: {n.score:.4f}] ID: {n.node.metadata.get('id')} - Titre: {n.node.metadata.get('titre')}")
        if i == 0:
            print(f"   Text: {n.node.get_content()}")
            print(f"   Window: {n.node.metadata.get('window')}")
            # Run post-processors manually
            for pp in engine.query_engine._node_postprocessors:
                print(f"   Running post-processor: {type(pp).__name__}")
                nodes_pp = pp.postprocess_nodes([n])
                if nodes_pp:
                    print(f"   New Text: {nodes_pp[0].node.get_content()}")

    # 4. Final Response
    print("\n[Final Response]")
    resp = engine.ask(query)
    print(f"Response: {resp}")

if __name__ == "__main__":
    debug_retrieval()
