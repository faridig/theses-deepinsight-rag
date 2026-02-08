import os
import shutil

# Supprimer les fichiers .json suspects dans le dossier data/
def clean_data_files(data_dir="data/"):
    for filename in os.listdir(data_dir):
        if filename.endswith(".json") and ("test" in filename or "golden" in filename):
            filepath = os.path.join(data_dir, filename)
            try:
                os.remove(filepath)
                print(f"Suppression de {filepath}")
            except OSError as e:
                print(f"Erreur lors de la suppression de {filepath}: {e}")

# Réinitialiser la collection ChromaDB via VectorService
def reset_chromadb():
    from src.indexing.vector_service import VectorService
    service = VectorService()
    service.reset()
    print("Réinitialisation de ChromaDB effectuée via VectorService.")


if __name__ == "__main__":
    clean_data_files()
    reset_chromadb()
