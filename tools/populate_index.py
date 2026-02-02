import logging
from src.ingestion.theses_client import ThesesClient
from src.processing.parser import ThesisParser
from src.indexing.vector_service import VectorService
from dotenv import load_dotenv

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def populate_index(query: str = "intelligence artificielle", limit: int = 2):
    """
    Télécharge des thèses, les parse et les indexe dans ChromaDB.
    """
    logger.info(f"Début de la population de l'index pour la requête : {query}")
    
    # 1. Ingestion
    client = ThesesClient(data_dir="data")
    theses = client.search(query, rows=limit)
    
    if not theses:
        logger.warning("Aucune thèse trouvée.")
        return

    logger.info(f"{len(theses)} thèses trouvées. Début du téléchargement...")
    
    downloaded_files = []
    for thesis in theses:
        file_path = client.download_pdf(thesis['id'], thesis['urlDocument'])
        if file_path:
            downloaded_files.append((file_path, thesis))

    if not downloaded_files:
        logger.warning("Aucun PDF n'a pu être téléchargé.")
        return

    # 2. Parsing & Indexation
    parser = ThesisParser()
    vector_service = VectorService(storage_path="./storage/chroma", collection_name="theses_collection")
    
    all_nodes = []
    # On ne prend qu'un seul fichier pour être sûr que ça passe le timeout
    for file_path, metadata in downloaded_files[:1]:
        logger.info(f"Parsing de {file_path}...")
        try:
            # On limite à 10 pages en dev pour économiser le quota LlamaParse
            nodes = parser.parse_pdf(str(file_path), is_dev=True)
            
            # Injection des métadonnées métier dans chaque nœud
            for node in nodes:
                node.metadata.update({
                    "id": metadata.get("id"),
                    "titre": metadata.get("titre"),
                    "auteur": ", ".join(metadata.get("auteurs", [])),
                    "date": metadata.get("dateSoutenance"),
                    "discipline": metadata.get("discipline")
                })
            
            all_nodes.extend(nodes)
        except Exception as e:
            logger.error(f"Erreur lors du parsing de {file_path}: {e}")

    if all_nodes:
        logger.info(f"Indexation de {len(all_nodes)} nœuds dans ChromaDB...")
        vector_service.index_nodes(all_nodes)
        logger.info("Indexation terminée avec succès.")
    else:
        logger.warning("Aucun nœud à indexer.")

if __name__ == "__main__":
    populate_index()
