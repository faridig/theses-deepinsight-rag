import logging
import os
from typing import Sequence, Optional
from llama_index.core import Settings
from llama_index.core.ingestion import IngestionPipeline, IngestionCache
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import Document, BaseNode
from llama_index.core.storage.kvstore import SimpleKVStore
from src.indexing.vector_service import VectorService

logger = logging.getLogger(__name__)

class AsyncIngestor:
    """
    Ingesteur asynchrone utilisant IngestionPipeline pour un traitement massif et parallèle (PBI-024).
    Inclut un cache d'ingestion pour l'idempotence (PBI-027).
    """
    def __init__(self, vector_service: VectorService, cache_path: Optional[str] = None):
        self.vector_service = vector_service
        
        # Configuration du cache (PBI-027)
        cache = None
        if cache_path:
            try:
                # S'assurer que le dossier existe
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                if os.path.exists(cache_path):
                    kv_store = SimpleKVStore.from_persist_path(cache_path)
                else:
                    kv_store = SimpleKVStore()
                cache = IngestionCache(kvstore=kv_store)
                self.cache_path = cache_path
                logger.info(f"IngestionCache initialized (path: {cache_path})")
            except Exception as e:
                logger.warning(f"Failed to initialize IngestionCache: {e}")
                cache = None

        # Configuration du pipeline de transformations (PBI-024)
        self.pipeline = IngestionPipeline(
            transformations=[
                SentenceSplitter(chunk_size=1024, chunk_overlap=20),
                Settings.embed_model,
            ],
            vector_store=self.vector_service.vector_store,
            cache=cache
        )

    async def run_ingestion(self, documents: Sequence[Document], show_progress: bool = True) -> Sequence[BaseNode]:
        """
        Exécute le pipeline d'ingestion de manière asynchrone (PBI-024).
        """
        if not documents:
            logger.warning("Aucun document à ingester.")
            return []
            
        logger.info(f"Démarrage de l'ingestion asynchrone pour {len(documents)} documents.")
        
        try:
            nodes = await self.pipeline.arun(
                documents=documents, 
                show_progress=show_progress,
                num_workers=4 
            )
            
            # Persistance du cache si utilisé
            if self.pipeline.cache and hasattr(self, 'cache_path'):
                try:
                    self.pipeline.cache.kvstore.persist(self.cache_path)
                    logger.info(f"IngestionCache saved to {self.cache_path}")
                except Exception as e:
                    logger.warning(f"Failed to persist IngestionCache: {e}")
            
            logger.info(f"Ingestion massive terminée : {len(nodes)} nœuds créés et indexés.")
            return list(nodes)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ingestion massive : {e}")
            # On tente de remonter l'erreur pour que l'appelant puisse la gérer
            raise e
