import os
import sys
import logging
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ingestion.theses_client import ThesesClient

def prepare():
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("prepare_test_data")
    
    client = ThesesClient(data_dir="data", fs=None, bucket=None)
    
    query = "machine learning"
    logger.info(f"Recherche de thèses pour '{query}'...")
    results = client.search(query, rows=10)
    
    if results:
        downloaded = False
        for thesis in results:
            logger.info(f"Essai de téléchargement pour : {thesis['titre']} ({thesis['urlDocument']})")
            download_result = client.download_pdf(thesis['id'], thesis['urlDocument'], theme="test")
            if download_result:
                logger.info(f"PDF téléchargé : {download_result['path']}")
                downloaded = True
                break
        if not downloaded:
            logger.error("Aucune thèse avec document accessible trouvée.")
    else:
        logger.error("Aucune thèse trouvée.")

if __name__ == "__main__":
    prepare()
