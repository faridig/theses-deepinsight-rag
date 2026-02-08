import os
import logging
from src.processing.parser import ThesisParser
from src.indexing.vector_service import VectorService
from dotenv import load_dotenv
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
        import shutil
        shutil.rmtree(storage_path)
        logger.info(f"Répertoire {storage_path} supprimé.")

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

    all_documents = []
    
    for pdf_path in pdf_files:
        thesis_id = pdf_path.stem
        logger.info(f"Traitement de {thesis_id}...")
        
        # Utilisation de l'API pour les métadonnées brutes (CA-1)
        metadata = {"titre": "Thèse Inconnue", "auteur": "Inconnu", "date": "N/A", "discipline": "N/A"}
        try:
            search_results = theses_client.search(thesis_id)
            if search_results:
                res = search_results[0]
                metadata["titre"] = res.get("titre", metadata["titre"])
                metadata["auteur"] = ", ".join(res.get("auteurs", [metadata["auteur"]]))
                metadata["date"] = res.get("dateSoutenance", metadata["date"])
                metadata["discipline"] = res.get("discipline", metadata["discipline"])
                logger.info(f"Métadonnées API récupérées pour {thesis_id}")
            else:
                logger.warning(f"Aucune métadonnée trouvée pour {thesis_id}")
        except Exception as e:
            logger.error(f"Erreur API pour {thesis_id} : {e}")

        logger.info(f"Parsing réel de {pdf_path.name}...")
        try:
            # On n'injecte plus de résumé factice (Incident PR #12)
            extra_meta = {
                "id": thesis_id,
                "titre": metadata["titre"],
                "auteur": metadata["auteur"],
                "date": metadata["date"],
                "discipline": metadata["discipline"]
            }
            # PBI-011: Indexation exhaustive
            documents = parser.parse_pdf(str(pdf_path), extra_metadata=extra_meta)
            
            all_documents.extend(documents)
            logger.info(f"OK : {len(documents)} documents extraits pour {thesis_id}")
        except Exception as e:
            logger.error(f"Échec du parsing pour {pdf_path.name} : {e}")

    if all_documents:
        logger.info(f"Indexation de {len(all_documents)} documents réels dans ChromaDB...")
        vector_service.index_documents(all_documents)
        logger.info("Indexation réelle terminée.")
    else:
        logger.error("Aucun document extrait. L'index reste vide.")

if __name__ == "__main__":
    reindex_real_data()
