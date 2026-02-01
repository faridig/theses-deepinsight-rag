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

    all_nodes = []
    
    # Métadonnées manuelles pour la démo basées sur les fichiers connus
    # Dans un flux complet, elles viendraient du search API, ici on les mappe par ID de fichier
    meta_map = {
        "2023STRAB011": {
            "titre": "L’apport de l’intelligence artificielle à la recherche en économie : trois essais sur la science des données et l’innovation",
            "auteur": "Pierre Pelletier",
            "date": "2023",
            "discipline": "Sciences économiques"
        },
        "2024STRAB004": {
            "titre": "Inférence causale et apprentissage automatique pour l'évaluation des politiques publiques",
            "auteur": "Diletta Abbonato",
            "date": "2024",
            "discipline": "Sciences économiques"
        }
    }

    for pdf_path in pdf_files:
        thesis_id = pdf_path.stem
        logger.info(f"Parsing réel de {pdf_path.name}...")
        try:
            # On parse les 10 premières pages (is_dev=True)
            nodes = parser.parse_pdf(str(pdf_path), is_dev=True)
            
            metadata = meta_map.get(thesis_id, {"titre": "Thèse Inconnue", "auteur": "Inconnu"})
            
            for node in nodes:
                node.metadata.update({
                    "id": thesis_id,
                    "titre": metadata["titre"],
                    "auteur": metadata["auteur"],
                    "date": metadata.get("date", "N/A"),
                    "discipline": metadata.get("discipline", "N/A")
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
