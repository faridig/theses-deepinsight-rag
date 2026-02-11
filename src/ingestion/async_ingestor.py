import os
import logging
from typing import List, Optional
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import Document, BaseNode
from src.indexing.vector_service import VectorService

logger = logging.getLogger(__name__)

class AsyncIngestor:
    """
    Ingesteur asynchrone utilisant IngestionPipeline pour un traitement massif et parallèle (PBI-024).
    """
    def __init__(self, vector_service: VectorService):
        self.vector_service = vector_service
        
        # Configuration du pipeline de transformations (PBI-024)
        # On utilise SentenceSplitter comme transformation de base
        # Le vector_store est intégré pour une indexation directe en fin de pipeline
        self.pipeline = IngestionPipeline(
            transformations=[
                SentenceSplitter(chunk_size=1024, chunk_overlap=20),
            ],
            vector_store=self.vector_service.vector_store
        )

    async def run_ingestion(self, documents: List[Document], show_progress: bool = True) -> List[BaseNode]:
        """
        Exécute le pipeline d'ingestion de manière asynchrone (PBI-024).
        Supporte le traitement parallèle via num_workers.
        """
        if not documents:
            logger.warning("Aucun document à ingester.")
            return []
            
        logger.info(f"Démarrage de l'ingestion asynchrone pour {len(documents)} documents.")
        
        try:
            # Lancement asynchrone du pipeline (arun) pour un traitement total non-bloquant
            # num_workers permet la parallélisation locale du parsing
            nodes = await self.pipeline.arun(
                documents=documents, 
                show_progress=show_progress,
                num_workers=4 
            )
            
            # Note: Si vector_service.aclient est None (mode local), 
            # LlamaIndex pourrait lever une erreur lors de l'insertion.
            # En production, l'utilisation d'un serveur Qdrant est requise pour cette fonctionnalité.
            
            logger.info(f"Ingestion massive terminée : {len(nodes)} nœuds créés et indexés.")
            return nodes
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ingestion massive : {e}")
            # On tente de remonter l'erreur pour que l'appelant puisse la gérer
            raise e
