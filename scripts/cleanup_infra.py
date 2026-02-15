import os
import shutil
import logging
from qdrant_client import QdrantClient
from src.ingestion.theses_client import ThesesClient
from src.config import CANONICAL_THEMES

# Silence technique (PBI-027)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cleanup_infra")

def cleanup():
    """
    Supprime les buckets MinIO orphelins, les collections Qdrant non autorisées
    et vide les dossiers temporaires/venv non standards (PBI-026).
    """
    client = ThesesClient()
    
    # 1. Liste Blanche Canonique (PBI-026/Review)
    # On génère la liste des thèmes autorisés à partir des thèmes canoniques
    allowed_themes = set(CANONICAL_THEMES.values())
    allowed_buckets = [client.bucket, "theses-data", "quarantine"]
    allowed_buckets.extend([f"theses-{t}" for t in allowed_themes])
    
    # Normalisation des noms autorisés
    allowed_buckets = [b.strip("/") for b in allowed_buckets if b]
    allowed_collections = [b for b in allowed_buckets if b.startswith("theses-")]
    
    # 2. Cleanup MinIO buckets
    if client.fs:
        try:
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

    # 3. Cleanup Qdrant Collections (Review Fix)
    try:
        qdrant_url = os.getenv("QDRANT_URL")
        storage_path = "./storage/qdrant"
        
        if qdrant_url:
            q_client = QdrantClient(url=qdrant_url)
            logger.info(f"Scanning Qdrant collections (Remote: {qdrant_url})...")
        elif os.path.exists(storage_path):
            q_client = QdrantClient(path=storage_path)
            logger.info(f"Scanning Qdrant collections (Local: {storage_path})...")
        else:
            q_client = None
            logger.warning("Qdrant non trouvé (ni URL ni stockage local).")

        if q_client:
            collections = q_client.get_collections().collections
            for col in collections:
                if col.name.startswith("theses-") and col.name not in allowed_collections:
                    logger.info(f"Suppression de la collection Qdrant orpheline : {col.name}")
                    q_client.delete_collection(col.name)
                else:
                    logger.info(f"Collection Qdrant conservée : {col.name}")
            q_client.close()
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage Qdrant : {e}")

    # 4. Cleanup local data directory
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

    # 5. Cleanup venv non standards (Review Fix)
    root_items = os.listdir(".")
    for item in root_items:
        if (item.startswith("venv") or item.startswith(".venv")) and item not in ["venv", ".venv"]:
            logger.info(f"Suppression du venv non standard : {item}")
            try:
                shutil.rmtree(item)
            except Exception as e:
                logger.error(f"Erreur lors de la suppression de {item} : {e}")
    
    logger.info("Nettoyage de l'infrastructure terminé.")

if __name__ == "__main__":
    cleanup()
