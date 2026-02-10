import os
import logging
from src.processing.parser import ThesisParser
from src.indexing.vector_service import VectorService
from dotenv import load_dotenv
import chromadb
from pathlib import Path

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def reindex_real_data():
    """
    Supprime l'index existant et indexe les thèses réelles présentes dans data/
    """
    storage_path = "./storage/chroma"
    collection_name = "theses_collection"
    
    # 1. Nettoyage radical
    logger.info("Nettoyage de l'index existant...")
    if os.path.exists(storage_path):
        client = chromadb.PersistentClient(path=storage_path)
        try:
            client.delete_collection(collection_name)
            logger.info(f"Collection {collection_name} supprimée.")
        except Exception as e:
            logger.warning(f"Erreur lors de la suppression de la collection (peut-être inexistante) : {e}")

    # 2. Initialisation des services
    parser = ThesisParser()
    vector_service = VectorService(storage_path=storage_path, collection_name=collection_name)
    
    # 3. Récupération des PDF réels
    data_dir = Path("data")
    pdf_files = list(data_dir.glob("*.pdf"))
    
    if not pdf_files:
        logger.error("Aucun fichier PDF trouvé dans data/. Abandon.")
        return

    logger.info(f"Fichiers trouvés pour indexation : {[f.name for f in pdf_files]}")

    from src.ingestion.theses_client import ThesesClient
    theses_client = ThesesClient()

    all_nodes = []
    
    for pdf_path in pdf_files:
        thesis_id = pdf_path.stem
        logger.info(f"Traitement de {thesis_id}...")
        
        # Récupération dynamique des métadonnées
        metadata = {"titre": "Thèse Inconnue", "auteur": "Inconnu", "date": "N/A", "discipline": "N/A"}
        try:
            search_results = theses_client.search(thesis_id)
            if search_results:
                res = search_results[0]
                metadata["titre"] = res.get("titre", metadata["titre"])
                metadata["auteur"] = ", ".join(res.get("auteurs", [metadata["auteur"]]))
                metadata["date"] = res.get("dateSoutenance", metadata["date"])
                metadata["discipline"] = res.get("discipline", metadata["discipline"])
                logger.info(f"Métadonnées récupérées pour {thesis_id} : {metadata['auteur']} - {metadata['titre']}")
            else:
                logger.warning(f"Aucune métadonnée trouvée pour {thesis_id}")
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métadonnées pour {thesis_id} : {e}")

        logger.info(f"Parsing réel de {pdf_path.name}...")
        try:
            # On parse le document
            nodes = parser.parse_pdf(str(pdf_path))
            
            for node in nodes:
                node.metadata.update({
                    "id": thesis_id,
                    "titre": metadata["titre"],
                    "auteur": metadata["auteur"],
                    "date": metadata["date"],
                    "discipline": metadata["discipline"]
                })
            
            all_nodes.extend(nodes)
            logger.info(f"OK : {len(nodes)} nœuds extraits pour {thesis_id}")
        except Exception as e:
            logger.error(f"Échec du parsing pour {pdf_path.name} : {e}")

    if all_nodes:
        logger.info(f"Indexation de {len(all_nodes)} nœuds réels dans ChromaDB...")
        vector_service.index_nodes(all_nodes)
        logger.info("Indexation réelle terminée.")
    else:
        logger.error("Aucun nœud extrait. L'index reste vide.")

if __name__ == "__main__":
    reindex_real_data()
