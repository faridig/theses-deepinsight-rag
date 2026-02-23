import os
import shutil
import logging
from qdrant_client import QdrantClient
from src.ingestion.theses_client import ThesesClient
from src.config import CANONICAL_THEMES, setup_settings

# Silence technique (PBI-027)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cleanup_infra")

def cleanup():
    """
    Grand Nettoyage de l'infrastructure (Sprint 21 - PBI-071, 072, 073).
    """
    setup_settings()
    client = ThesesClient()
    
    # 1. PBI-071: Nettoyage des Buckets MinIO
    if client.fs:
        try:
            logger.info("--- PBI-071: Scanning MinIO buckets ---")
            buckets = client.fs.ls("", detail=False)
            target_bucket = os.getenv("MINIO_BUCKET", "theses-data")
            
            for b_path in buckets:
                b_name = b_path.strip("/")
                if b_name != target_bucket and b_name != "reports": # On garde reports par précaution
                    logger.info(f"Suppression du bucket orphelin : {b_name}")
                    try:
                        client.fs.rm(b_path, recursive=True)
                    except Exception as e:
                        logger.error(f"Erreur lors de la suppression du bucket {b_name}: {e}")
                else:
                    logger.info(f"Bucket conservé : {b_name}")
            
            # PBI-071: Nettoyage de la racine du bucket
            logger.info(f"--- PBI-071: Nettoyage racine de {target_bucket} ---")
            root_items = client.fs.ls(target_bucket, detail=False)
            for item in root_items:
                item_name = os.path.basename(item)
                if item_name == "themes":
                    continue
                
                # Migration PDF orphelin
                if item.lower().endswith(".pdf"):
                    target_path = f"{target_bucket}/themes/unsorted/docs/{item_name}"
                    logger.info(f"Migration PDF orphelin {item} -> {target_path}")
                    client.fs.makedirs(f"{target_bucket}/themes/unsorted/docs", exist_ok=True)
                    client.fs.mv(item, target_path)
                
                # Suppression dossier agriculture orphelin à la racine
                elif item_name == "agriculture":
                    logger.info(f"Suppression dossier 'agriculture' orphelin à la racine de {target_bucket}")
                    client.fs.rm(item, recursive=True)
                
                # Autres orphelins (sauf dossiers techniques)
                elif item_name not in ["themes", "quarantine", "reports"]:
                    logger.info(f"Suppression item orphelin : {item}")
                    client.fs.rm(item, recursive=True)
                    
        except Exception as e:
            logger.error(f"Erreur durant le nettoyage MinIO : {e}")
    else:
        logger.warning("MinIO non configuré, saut du nettoyage S3.")

    # 2. Cleanup Qdrant Collections
    # On définit explicitement les collections autorisées (celles qui commencent par theses-)
    allowed_collections = ["theses-agriculture", "theses-intelligence-artificielle", "theses-droit", "theses-sante", "theses-biologie", "theses-default", "theses-ia", "theses-énergie-solaire", "theses-animaux"]
    
    try:
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        q_client = QdrantClient(url=qdrant_url)
        
        collections = q_client.get_collections().collections
        for col in collections:
            if col.name.startswith("theses-") and col.name not in allowed_collections:
                logger.info(f"Suppression de la collection Qdrant orpheline : {col.name}")
                q_client.delete_collection(col.name)
            elif not col.name.startswith("theses-") and "test" in col.name:
                logger.info(f"Suppression de la collection de test : {col.name}")
                q_client.delete_collection(col.name)
        q_client.close()
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage Qdrant : {e}")

    # 3. Cleanup local data directory (PBI-072)
    data_dir = "data"
    if os.path.exists(data_dir):
        logger.info("--- PBI-072: Nettoyage local ---")
        # On supprime data/pdfs qui est obsolète
        legacy_pdf_dir = os.path.join(data_dir, "pdfs")
        if os.path.exists(legacy_pdf_dir):
            logger.info("Suppression du dossier local obsolète data/pdfs/")
            shutil.rmtree(legacy_pdf_dir)
            
        # On garde ground_truth.json et les thèmes structurés
        for item in os.listdir(data_dir):
            item_path = os.path.join(data_dir, item)
            if item == "ground_truth.json" or item == "themes" or item == "synthetic_dataset.json":
                continue
            
            try:
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception as e:
                logger.error(f"Erreur lors de la suppression de {item_path} : {e}")

    # 4. Cleanup cache
    cache_dir = "storage/cache"
    if os.path.exists(cache_dir):
        logger.info("Nettoyage du cache d'ingestion...")
        # On ne garde que les dossiers de thèmes valides
        for theme_cache in os.listdir(cache_dir):
            if theme_cache not in [t.replace("theses-", "") for t in allowed_collections]:
                path = os.path.join(cache_dir, theme_cache)
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.unlink(path)
                except Exception as e:
                    logger.error(f"Erreur lors de la suppression du cache {path}: {e}")

    logger.info("Nettoyage de l'infrastructure terminé.")

    
    logger.info("Nettoyage de l'infrastructure terminé.")

if __name__ == "__main__":
    cleanup()
