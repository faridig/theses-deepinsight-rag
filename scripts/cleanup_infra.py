import os
import shutil
import logging
from src.ingestion.theses_client import ThesesClient

# Silence technique (PBI-027)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cleanup_infra")

def cleanup():
    """
    Supprime les buckets MinIO orphelins et vide le dossier data/ local (PBI-026).
    """
    client = ThesesClient()
    
    # 1. Cleanup MinIO buckets
    if client.fs:
        try:
            # Buckets autorisés (définis dans le Sprint Plan ou Config)
            # On garde le bucket principal et les silos thématiques connus
            allowed_buckets = [client.bucket, "theses-ia", "theses-agri", "theses-agriculture", "theses-data", "quarantine"]
            
            # Normalisation des noms autorisés
            allowed_buckets = [b.strip("/") for b in allowed_buckets if b]
            
            logger.info("Scanning MinIO buckets...")
            buckets = client.fs.ls("", detail=False)
            for bucket in buckets:
                bucket_name = bucket.strip("/")
                if bucket_name and bucket_name not in allowed_buckets:
                    logger.info(f"Suppression du bucket orphelin : {bucket_name}")
                    try:
                        client.fs.rm(bucket, recursive=True)
                    except Exception as rm_err:
                        logger.error(f"Impossible de supprimer {bucket_name}: {rm_err}")
                else:
                    logger.info(f"Bucket conservé : {bucket_name}")
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage MinIO : {e}")
    else:
        logger.warning("MinIO non configuré, saut du nettoyage des buckets.")

    # 2. Cleanup local data directory
    data_dir = "data"
    if os.path.exists(data_dir):
        logger.info(f"Nettoyage du dossier local : {data_dir}")
        for item in os.listdir(data_dir):
            item_path = os.path.join(data_dir, item)
            try:
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                    logger.info(f"Fichier supprimé : {item}")
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    logger.info(f"Dossier supprimé : {item}")
            except Exception as e:
                logger.error(f"Erreur lors de la suppression de {item_path} : {e}")
    else:
        logger.info("Dossier data/ inexistant, rien à nettoyer.")
    
    logger.info("Nettoyage de l'infrastructure terminé.")

if __name__ == "__main__":
    cleanup()
