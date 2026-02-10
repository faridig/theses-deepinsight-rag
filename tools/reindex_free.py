import os
import logging
from pathlib import Path
from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceWindowNodeParser
from src.indexing.vector_service import VectorService
from src.ingestion.theses_client import ThesesClient
from dotenv import load_dotenv

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def reindex_without_llamaparse():
    """
    Reconstruit l'index en utilisant un parser gratuit (PyPDF) et applique les métadonnées.
    """
    storage_path = "./storage/chroma"
    collection_name = "theses_collection"
    
    logger.info("Récupération des métadonnées et parsing gratuit...")
    
    # 1. Initialisation des services
    theses_client = ThesesClient()
    
    # Nettoyage radical
    if os.path.exists(storage_path):
        import shutil
        shutil.rmtree(storage_path)
    os.makedirs(storage_path, exist_ok=True)
    
    vector_service = VectorService(storage_path=storage_path, collection_name=collection_name)
    
    # 2. Configuration du parser de nœuds (Sentence Window comme dans ThesisParser)
    node_parser = SentenceWindowNodeParser.from_defaults(
        window_size=3,
        window_metadata_key="window",
        original_text_metadata_key="original_text",
    )
    
    data_dir = Path("data")
    pdf_files = list(data_dir.glob("*.pdf"))
    
    all_nodes = []
    
    for pdf_path in pdf_files:
        thesis_id = pdf_path.stem
        logger.info(f"Traitement de {thesis_id}...")
        
        # Métadonnées
        metadata = {"titre": "Thèse Inconnue", "auteur": "Inconnu"}
        try:
            search_results = theses_client.search(thesis_id)
            if search_results:
                res = search_results[0]
                metadata["titre"] = res.get("titre", metadata["titre"])
                metadata["auteur"] = ", ".join(res.get("auteurs", [metadata["auteur"]]))
        except Exception as e:
            logger.error(f"Erreur métadonnées pour {thesis_id}: {e}")

        # Parsing gratuit avec SimpleDirectoryReader (utilise PyPDF)
        try:
            reader = SimpleDirectoryReader(input_files=[str(pdf_path)])
            documents = reader.load_data()
            
            # Application des métadonnées aux documents avant le découpage
            for doc in documents:
                doc.metadata.update(metadata)
            
            # Découpage en nœuds
            nodes = node_parser.get_nodes_from_documents(documents)
            all_nodes.extend(nodes)
            logger.info(f"OK : {len(nodes)} nœuds extraits pour {thesis_id}")
        except Exception as e:
            logger.error(f"Échec parsing pour {pdf_path.name}: {e}")

    if all_nodes:
        logger.info(f"Indexation de {len(all_nodes)} nœuds dans ChromaDB...")
        vector_service.index_nodes(all_nodes)
        logger.info("Réindexation terminée avec succès.")
    else:
        logger.error("Aucun nœud extrait.")

if __name__ == "__main__":
    reindex_without_llamaparse()
