import asyncio
import sys
import argparse
import logging
from src.ingestion.theme_ingestor import download_theme

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    parser = argparse.ArgumentParser(description="Télécharge et indexe des thèses par thème depuis theses.fr")
    parser.add_argument("theme", type=str, help="Le thème de recherche (ex: 'intelligence artificielle')")
    parser.add_argument("--limit", type=int, default=10, help="Nombre maximum de thèses à télécharger")
    parser.add_argument("--storage", type=str, default="./storage/qdrant", help="Dossier de stockage Qdrant")
    
    args = parser.parse_args()

    print(f"=== Thématique : {args.theme} ===")
    print(f"=== Limite : {args.limit} ===")
    
    try:
        await download_theme(args.theme, limit=args.limit, storage_path=args.storage)
        print("✅ Opération terminée avec succès.")
    except Exception as e:
        print(f"❌ Erreur : {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
