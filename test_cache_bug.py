
import os
import asyncio
import logging
from src.ingestion.async_ingestor import AsyncIngestor
from src.indexing.vector_service import VectorService
from llama_index.core.schema import Document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_cache_init():
    os.makedirs("storage/test_cache", exist_ok=True)
    cache_path = "storage/test_cache/test.json"
    if os.path.exists(cache_path):
        os.remove(cache_path)
        
    vector_service = VectorService(storage_path="./storage/test_qdrant", collection_name="test_collection")
    
    print("\n--- Testing AsyncIngestor Initialization ---")
    ingestor = AsyncIngestor(vector_service=vector_service, cache_path=cache_path)
    
    if ingestor.pipeline.cache is None:
        print("FAILURE: Pipeline cache is None!")
    else:
        print(f"Pipeline cache type: {type(ingestor.pipeline.cache)}")
        # Check if it's using our kv_store
        if hasattr(ingestor.pipeline.cache, 'cache') and ingestor.pipeline.cache.cache == ingestor.kv_store:
            print("SUCCESS: Cache is correctly linked to kv_store.")
        else:
            print("FAILURE: Cache is NOT linked to kv_store.")
            print(f"Pipeline cache 'cache' field: {getattr(ingestor.pipeline.cache, 'cache', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(test_cache_init())
