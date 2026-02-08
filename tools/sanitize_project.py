import logging
import os
from src.indexing.vector_service import VectorService
from pathlib import Path

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def sanitize_project():
    """
    Réalise l'assainissement total du projet (Scenario 0 du PBI-011).
    1. Supprime les fichiers JSON suspects.
    2. Réinitialise l'index vectoriel.
    """
    logger.info("Démarrage de l'assainissement du projet...")

    # 1. Nettoyage des fichiers JSON suspects dans data/
    data_dir = Path("data")
    if data_dir.exists():
        json_files = list(data_dir.glob("*.json"))
        for json_file in json_files:
            logger.warning(f"Suppression du fichier suspect : {json_file}")
            json_file.unlink()
    
    # On cherche aussi à la racine au cas où
    root_suspects = ["test_dataset.json", "golden_dataset.json"]
    for suspect in root_suspects:
        suspect_path = Path(suspect)
        if suspect_path.exists():
            logger.warning(f"Suppression du fichier suspect à la racine : {suspect_path}")
            suspect_path.unlink()

    # 2. Réinitialisation de l'index
    vector_service = VectorService()
    vector_service.reset()

    logger.info("Assainissement terminé avec succès.")

if __name__ == "__main__":
    sanitize_project()
