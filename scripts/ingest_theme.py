import asyncio
import logging
import sys
import os
import argparse

# Ajout du root au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import setup_settings
from src.ingestion.theme_ingestor import download_theme, orchestrate_s3_ingestion

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    parser = argparse.ArgumentParser(description="Ingestion thématique pour Theses-DeepInsight")
    parser.add_argument("--theme", type=str, help="Thème à ingester")
    parser.add_argument("--limit", type=int, default=10, help="Nombre de thèses à ingester (Top N)")
    parser.add_argument("--s3-only", action="store_true", help="Re-synchroniser depuis S3 uniquement")
    
    args = parser.parse_args()
    
    # Initialisation
    setup_settings()
    
    if args.s3_only:
        logger.info(f"Démarrage de la re-synchronisation S3 pour : {args.theme or 'Tous les thèmes'}")
        await orchestrate_s3_ingestion(target_theme=args.theme)
        return

    themes = [args.theme] if args.theme else ["Intelligence Artificielle", "Agriculture", "Droit"]
    limit_per_theme = args.limit
    
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
