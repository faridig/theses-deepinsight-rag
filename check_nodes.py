
import os
from src.indexing.vector_service import VectorService
from llama_index.core import StorageContext

def check_nodes():
    service = VectorService()
    docstore = service.storage_context.docstore
    nodes = list(docstore.docs.values())
    print(f"Total nodes: {len(nodes)}")
    
    for n in nodes[:20]:
        if "2024PA131029" in n.metadata.get('id', ''):
            print(f"ID: {n.metadata.get('id')} - Text: {n.get_content()[:200]}...")
            break
    else:
        print("No nodes found for 2024PA131029 in first 20")

if __name__ == "__main__":
    check_nodes()
