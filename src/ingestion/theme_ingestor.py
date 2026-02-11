import logging
import os
from llama_index.core import SimpleDirectoryReader
from src.ingestion.theses_client import ThesesClient
from src.ingestion.async_ingestor import AsyncIngestor
from src.indexing.vector_service import VectorService

logger = logging.getLogger(__name__)

async def download_theme(theme_name: str, limit: int = 10, storage_path: str = "./storage/qdrant"):
    """
    Télécharge et indexe des thèses par thème (PBI-025).
    Combine ThesesClient, AsyncIngestor et VectorService.
    """
    # 1. Initialisation
    slug_theme = theme_name.lower().replace(" ", "-")
    collection_name = f"theses-{slug_theme}"
    data_dir = f"data/{slug_theme}"
    
    client = ThesesClient(data_dir=data_dir)
    vector_service = VectorService(storage_path=storage_path, collection_name=collection_name)
    
    # Création de la collection isolée (PBI-023)
    await vector_service.create_collection_if_not_exists(collection_name)
    
    ingestor = AsyncIngestor(vector_service=vector_service)
    
    # 2. Recherche des thèses (PBI-025 Pagination/Filtres)
    logger.info(f"Recherche de {limit} thèses pour le thème : {theme_name}")
    theses_metadata = client.search_all(query=theme_name, limit=limit)
    
    if not theses_metadata:
        logger.warning(f"Aucune thèse trouvée pour le thème : {theme_name}")
        return []

    # 3. Téléchargement et Chargement en Documents
    documents = []
    for meta in theses_metadata:
        try:
            pdf_path = client.download_pdf(meta['id'], meta['urlDocument'])
            if pdf_path and os.path.exists(pdf_path):
                # Chargement du PDF en documents LlamaIndex
                reader = SimpleDirectoryReader(input_files=[pdf_path])
                doc_list = reader.load_data()
                
                # Enrichissement des métadonnées (PBI-025)
                for doc in doc_list:
                    doc.metadata.update({
                        "id_these": meta.get('id'),
                        "titre": meta.get('titre'),
                        "auteur": ", ".join(meta.get('auteurs', [])),
                        "discipline": meta.get('discipline'),
                        "theme": theme_name, # Métadonnée thématique
                        "slug": slug_theme
                    })
                documents.extend(doc_list)
        except Exception as e:
            logger.error(f"Erreur lors du traitement de la thèse {meta.get('id')} : {e}")
            continue # On continue malgré une erreur sur un PDF (PBI-024 Robustesse)

    # 4. Ingestion massive asynchrone (PBI-024)
    if documents:
        nodes = await ingestor.run_ingestion(documents)
        logger.info(f"Thème {theme_name} indexé avec succès ({len(nodes)} nœuds).")
        return nodes
    else:
        logger.warning(f"Aucun document valide à ingester pour le thème {theme_name}.")
        return []
