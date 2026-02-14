import logging
import os
from llama_index.core import SimpleDirectoryReader
from src.ingestion.theses_client import ThesesClient
from src.ingestion.async_ingestor import AsyncIngestor
from src.indexing.vector_service import VectorService
from src.utils.pdf_validator import PDFValidator

logger = logging.getLogger(__name__)

async def download_theme(theme_name: str, limit: int = 10, storage_path: str = "./storage/qdrant"):
    """
    Télécharge et indexe des thèses par thème (PBI-025 & PBI-026).
    Combine ThesesClient, AsyncIngestor et VectorService.
    Utilise S3 (MinIO) pour le stockage si configuré.
    """
    # 1. Initialisation
    slug_theme = theme_name.lower().replace(" ", "-")
    collection_name = f"theses-{slug_theme}"
    
    client = ThesesClient() # Utilise les ENV par défaut pour S3 (PBI-026)
    vector_service = VectorService(storage_path=storage_path, collection_name=collection_name)
    
    # Création de la collection isolée (PBI-023)
    await vector_service.create_collection_if_not_exists(collection_name)
    
    # Ingestor avec cache d'ingestion (PBI-027)
    cache_path = f"storage/cache/{slug_theme}"
    os.makedirs("storage/cache", exist_ok=True)
    ingestor = AsyncIngestor(vector_service=vector_service, cache_path=cache_path)
    
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
            # Téléchargement vers S3 ou local selon configuration (PBI-026)
            pdf_path = client.download_pdf(meta['id'], meta['urlDocument'], theme=slug_theme)
            if pdf_path:
                # Validation Proactive (PBI-027)
                if not PDFValidator.validate(pdf_path, fs=client.fs):
                    logger.warning(f"Thèse {meta['id']} invalide ou corrompue (URL: {meta['urlDocument']}). Mise en quarantaine.")
                    if client.fs:
                        quarantine_dir = "quarantine"
                        if not client.fs.exists(quarantine_dir):
                            client.fs.makedirs(quarantine_dir)
                        client.fs.mv(pdf_path, f"{quarantine_dir}/{os.path.basename(pdf_path)}")
                    continue

                # Chargement du PDF en documents LlamaIndex (PBI-024 Robustesse)
                try:
                    if client.fs:
                        reader = SimpleDirectoryReader(
                            input_files=[pdf_path],
                            fs=client.fs
                        )
                    else:
                        reader = SimpleDirectoryReader(input_files=[pdf_path])
                    doc_list = reader.load_data()
                except Exception as reader_error:
                    logger.warning(f"Impossible de lire le PDF {pdf_path}: {reader_error}")
                    continue
                
                # Enrichissement des métadonnées (PBI-025 & PBI-027)
                date_soutenance = meta.get('dateSoutenance')
                year = "Inconnue"
                if date_soutenance:
                    if "/" in date_soutenance:
                        year = date_soutenance.split("/")[-1]
                    elif "-" in date_soutenance:
                        year = date_soutenance.split("-")[0]
                    elif len(date_soutenance) >= 4:
                        year = date_soutenance[:4]
                
                for doc in doc_list:
                    doc.metadata.update({
                        "id_these": meta.get('id'),
                        "titre": meta.get('titre'),
                        "auteur": ", ".join(meta.get('auteurs', [])),
                        "discipline": meta.get('discipline'),
                        "year": year, # PBI-027
                        "university": meta.get('university'), # PBI-027
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

async def orchestrate_s3_ingestion(storage_path: str = "./storage/qdrant"):
    """
    Scanne le bucket S3 et orchestre l'ingestion par silo thématique (PBI-027).
    Garantit l'étanchéité thématique entre les collections Qdrant.
    """
    client = ThesesClient()
    if not client.fs:
        logger.error("S3FileSystem non configuré. L'orchestration S3 est impossible.")
        return

    bucket = client.bucket
    # 1. Découverte des Thèmes (PBI-027)
    try:
        # Liste les dossiers (thèmes) dans le bucket
        items = client.fs.ls(bucket, detail=False)
        # On filtre pour ne garder que les répertoires (slugs de thèmes)
        themes = [os.path.basename(item) for item in items if client.fs.isdir(item)]
    except Exception as e:
        logger.error(f"Erreur lors du scan du bucket {bucket} : {e}")
        return

    if not themes:
        logger.warning(f"Aucun thème découvert dans le bucket {bucket}.")
        return

    logger.info(f"Thèmes découverts dans S3 : {themes}")

    # 2. Orchestration de l'Ingestion par Silo (PBI-027)
    for theme_slug in themes:
        collection_name = f"theses-{theme_slug}"
        theme_folder = f"{bucket}/{theme_slug}"
        
        logger.info(f"Démarrage de l'ingestion pour le silo : {theme_slug}")
        
        # Initialisation VectorService pour la collection spécifique
        vector_service = VectorService(storage_path=storage_path, collection_name=collection_name)
        await vector_service.create_collection_if_not_exists(collection_name)
        
        # Ingestor avec Cache (PBI-027)
        cache_path = f"storage/cache/{theme_slug}"
        os.makedirs("storage/cache", exist_ok=True)
        ingestor = AsyncIngestor(vector_service=vector_service, cache_path=cache_path)
        
        # 3. Chargement siloté (SimpleDirectoryReader sur préfixe spécifique)
        try:
            reader = SimpleDirectoryReader(
                input_dir=theme_folder,
                fs=client.fs,
                recursive=True
            )
            documents = reader.load_data()
            
            if documents:
                # Injection de métadonnées pour double vérification (PBI-027 CA)
                for doc in documents:
                    doc.metadata["theme_silo"] = theme_slug
                
                await ingestor.run_ingestion(documents)
                logger.info(f"Silo {theme_slug} ingéré avec succès.")
            else:
                logger.warning(f"Aucun document trouvé dans {theme_folder}")
        except Exception as e:
            logger.error(f"Erreur lors de l'ingestion du silo {theme_slug} : {e}")
