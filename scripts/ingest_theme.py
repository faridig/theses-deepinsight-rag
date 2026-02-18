import asyncio
import logging
import sys
import os

# Ajout du root au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import setup_settings
from src.ingestion.theme_ingestor import download_theme

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    # Initialisation
    setup_settings()
    
    themes = ["Intelligence Artificielle", "Agriculture", "Droit"]
    limit_per_theme = 10
    
    logger.info(f"Démarrage de l'ingestion massive pour les thèmes : {themes}")
    
    for theme in themes:
        logger.info(f"--- Ingestion du thème : {theme} ---")
        try:
            nodes = await download_theme(theme, limit=limit_per_theme)
            logger.info(f"Thème '{theme}' ingéré : {len(nodes) if nodes else 0} nœuds.")
        except Exception as e:
            logger.error(f"Erreur lors de l'ingestion du thème '{theme}' : {e}")

if __name__ == "__main__":
    asyncio.run(main())
