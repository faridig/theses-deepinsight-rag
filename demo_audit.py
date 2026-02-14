
import asyncio
import os
import logging
from src.ingestion.theme_ingestor import download_theme, orchestrate_s3_ingestion
from src.ingestion.theses_client import ThesesClient
from llama_index.core import Settings
from llama_index.core.embeddings.mock_embed_model import MockEmbedding

# Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DemoAudit")

async def run_demo():
    # 1. Setup Env
    os.environ["MINIO_ACCESS_KEY"] = "minioadmin"
    os.environ["MINIO_SECRET_KEY"] = "minioadmin"
    os.environ["MINIO_ENDPOINT_URL"] = "http://localhost:9000"
    os.environ["MINIO_BUCKET"] = "theses-demo"
    os.environ["QDRANT_URL"] = "http://localhost:6333"
    
    # Mock Embeddings to avoid needing an API key
    Settings.embed_model = MockEmbedding(embed_dim=1536)
    
    logger.info("--- PHASE 1 : Téléchargement Thématique ---")
    # Télécharge 2 thèses sur l'IA
    nodes = await download_theme("Intelligence Artificielle", limit=2)
    logger.info(f"Phase 1 terminée. {len(nodes)} nodes indexés.")
    
    logger.info("--- PHASE 2 : Vérification S3 ---")
    client = ThesesClient()
    items = client.fs.ls("theses-demo/intelligence-artificielle")
    logger.info(f"Fichiers dans S3 : {items}")
    if len(items) >= 2:
        logger.info("Vérification S3 réussie.")
    else:
        logger.error("Vérification S3 échouée.")
        return

    logger.info("--- PHASE 3 : Orchestration Globale ---")
    # On supprime le cache pour forcer la re-lecture (mais l'idempotence devrait gérer si on le laissait)
    # Ici on veut tester que l'orchestrateur voit le dossier IA dans S3 et traite tout.
    await orchestrate_s3_ingestion()
    logger.info("Phase 3 terminée.")

    logger.info("--- PHASE 4 : Vérification Qdrant ---")
    from qdrant_client import QdrantClient
    q_client = QdrantClient(url="http://localhost:6333")
    collections = q_client.get_collections().collections
    names = [c.name for c in collections]
    logger.info(f"Collections dans Qdrant : {names}")
    
    if "theses-intelligence-artificielle" in names:
        logger.info("Audit réussi : Collection créée.")
        count = q_client.count(collection_name="theses-intelligence-artificielle").count
        logger.info(f"Nombre de points dans la collection : {count}")
    else:
        logger.error("Audit échoué : Collection manquante.")

if __name__ == "__main__":
    asyncio.run(run_demo())
