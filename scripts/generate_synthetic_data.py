import os
import sys
import json
import logging
from dotenv import load_dotenv
from llama_index.core import Settings, SimpleDirectoryReader
from llama_index.core.llama_dataset.generator import RagDatasetGenerator
from s3fs import S3FileSystem

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import setup_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("generate_synthetic_data")

def generate_synthetic_dataset():
    """
    Génère un dataset synthétique de test à partir des documents indexés.
    """
    load_dotenv()
    setup_settings()
    
    try:
        # PBI-038 : Suppression de la dépendance à data/sample.pdf
        bucket = os.getenv("MINIO_BUCKET", "theses-data")
        endpoint_url = os.getenv("MINIO_ENDPOINT_URL", "http://localhost:9000")
        access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        
        logger.info(f"Connexion à MinIO sur {endpoint_url} pour charger les documents...")
        fs = S3FileSystem(
            key=access_key,
            secret=secret_key,
            endpoint_url=endpoint_url,
            use_ssl=os.getenv("MINIO_USE_SSL", "False").lower() == "true"
        )
        input_dir = f"{bucket}/pdfs"
        reader = SimpleDirectoryReader(input_dir=input_dir, fs=fs)

        documents = reader.load_data()
        
        if not documents:
            logger.error("Aucun document trouvé pour la génération.")
            return

        # Limiter à quelques documents pour le test (PBI-030)
        documents = documents[:3]
        
        logger.info(f"{len(documents)} documents sélectionnés. Initialisation du générateur...")

        
        # Initialisation du générateur LlamaIndex
        # On limite le nombre de questions par document pour le MVP (PBI-030)
        generator = RagDatasetGenerator.from_documents(
            documents=documents,
            llm=Settings.llm,
            num_questions_per_chunk=2, # Limité pour la démo
            show_progress=True
        )
        
        logger.info("Génération du dataset synthétique (Questions/Réponses)...")
        dataset = generator.generate_dataset_from_nodes()
        
        # Export au format attendu par audit_quality.py ou compatible Ragas
        output_path = "data/synthetic_dataset.json"
        os.makedirs("data", exist_ok=True)
        
        # Conversion en format compatible Ragas (Question, Ground Truth, Context)
        ragas_compatible_data = []
        for item in dataset.examples:
            ragas_compatible_data.append({
                "question": item.query,
                "ground_truth": item.reference_answer,
                "contexts": [item.reference_contexts[0]] if item.reference_contexts else []
            })
            
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(ragas_compatible_data, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Dataset synthétique généré avec succès ({len(ragas_compatible_data)} items) : {output_path}")
        
    except Exception as e:
        logger.error(f"Erreur durant la génération : {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    generate_synthetic_dataset()
