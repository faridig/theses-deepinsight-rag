import logging
from src.ingestion.theses_client import ThesesClient
from src.processing.parser import ThesisParser
from src.indexing.vector_service import VectorService
import s3fs
from dotenv import load_dotenv

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def reindex_s3(query: str = "intelligence artificielle", limit: int = 1):
    """
    Pipeline complet utilisant MinIO (S3) pour le stockage des PDFs.
    """
    logger.info("Démarrage du pipeline S3...")
    
    # 1. Configuration S3
    endpoint_url = "http://localhost:9000"
    key = "minioadmin"
    secret = "minioadmin"
    bucket = "theses-bucket"
    
    fs = s3fs.S3FileSystem(
        endpoint_url=endpoint_url,
        key=key,
        secret=secret,
        use_ssl=False
    )
    
    if not fs.exists(bucket):
        fs.mkdir(bucket)
        logger.info(f"Bucket {bucket} créé.")

    # 2. Ingestion vers S3
    client = ThesesClient(fs=fs, bucket=bucket)
    theses = client.search(query, rows=limit)
    
    if not theses:
        logger.warning("Aucune thèse trouvée.")
        return

    downloaded_paths = []
    for thesis in theses:
        s3_path = client.download_pdf(thesis['id'], thesis['urlDocument'])
        if s3_path:
            downloaded_paths.append((s3_path, thesis))

    # 3. Parsing depuis S3 & Indexation
    # On utilise le mode 'docling' si possible, sinon llama-parse
    # Note: En environnement de test, docling peut être lourd, on utilise llama-parse par défaut
    parser = ThesisParser(mode="llama-parse")
    vector_service = VectorService(storage_path="./storage/chroma", collection_name="s3_collection")
    
    all_nodes = []
    for s3_path, metadata in downloaded_paths:
        logger.info(f"Parsing depuis S3: {s3_path}...")
        try:
            nodes = parser.parse_pdf(s3_path, fs=fs, is_dev=True)
            
            for node in nodes:
                node.metadata.update({
                    "id": metadata.get("id"),
                    "titre": metadata.get("titre"),
                    "auteur": ", ".join(metadata.get("auteurs", [])),
                    "s3_path": s3_path
                })
            all_nodes.extend(nodes)
        except Exception as e:
            logger.error(f"Erreur lors du parsing de {s3_path}: {e}")

    if all_nodes:
        logger.info(f"Indexation de {len(all_nodes)} nœuds...")
        vector_service.index_nodes(all_nodes)
        logger.info("Terminé !")
    else:
        logger.warning("Aucun nœud indexé.")

if __name__ == "__main__":
    reindex_s3()
