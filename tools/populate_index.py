import logging
from src.ingestion.theses_client import ThesesClient
from src.processing.parser import ThesisParser
from src.indexing.vector_service import VectorService
import pypdf
from dotenv import load_dotenv
import typer

app = typer.Typer()

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

@app.command()
def populate_index(
    query: str = typer.Option("intelligence artificielle", help="La requête de recherche pour les thèses."), 
    limit: int = typer.Option(2, help="Le nombre de thèses à télécharger. Utiliser un grand nombre pour l'ingestion complète."), 
    reset_index: bool = typer.Option(False, "--reset", "-r", help="Supprime et recrée la collection ChromaDB avant l'indexation."), 
    is_production_run: bool = typer.Option(False, "--prod", "-p", help="Lève toutes les limites de parsing et de fichiers (mode production).")
):
    """
    Télécharge des thèses, les parse et les indexe dans ChromaDB.
    """
    logger.info(f"Début de la population de l'index pour la requête : {query}. Production run: {is_production_run}, Reset index: {reset_index}")
    
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
    
    if reset_index:
        vector_service.reset_collection()
    
    total_estimated_pages = 0
    all_nodes = []
    # Contrôle de la volumétrie pour les runs de développement/test
    files_to_process = downloaded_files if is_production_run else downloaded_files[:1]
    for file_path, metadata in files_to_process:
        # 1. Compter les pages pour l'estimation de coût (Scenario 1.2)
        try:
            reader = pypdf.PdfReader(file_path)
            page_count = len(reader.pages)
            total_estimated_pages += page_count
            logger.info(f"PDF {file_path} a {page_count} pages.")
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du nombre de pages de {file_path}: {e}")
            
        logger.info(f"Parsing de {file_path}...")
        try:
            # On utilise le mode dev pour limiter le parsing si on n'est pas en run de production
            nodes = parser.parse_pdf(str(file_path), is_dev=not is_production_run)
            
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
        
    # PBI-011 Scenario 1.2: Documentation de l'estimation des coûts
    if total_estimated_pages > 0:
        COST_PER_PAGE = 0.0005  # $0.0005 par page LlamaParse (Estimation basée sur la doc)
        estimated_cost = total_estimated_pages * COST_PER_PAGE
        logger.info("-" * 50)
        logger.info(f"ESTIMATION DES COÛTS LLAMAPARSE (PBI-011 Scenario 1.2)")
        logger.info(f"Nombre total de pages à parser pour ce lot: {total_estimated_pages}")
        logger.info(f"Coût par page (estimation): ${COST_PER_PAGE}")
        logger.info(f"Coût total estimé pour ce lot: ${estimated_cost:.4f}")
        logger.info("-" * 50)

if __name__ == "__main__":
    app()
