import asyncio
import logging
from src.ingestion.theme_ingestor import orchestrate_s3_ingestion

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Démarrage de l'orchestration globale de l'ingestion depuis S3...")
    await orchestrate_s3_ingestion()
    logger.info("Orchestration terminée.")

if __name__ == "__main__":
    asyncio.run(main())
