import os
import sys
import json
import logging
import random
from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.core.llama_dataset.generator import RagDatasetGenerator

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import setup_settings
from src.indexing.vector_service import VectorService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("generate_ground_truth")

def generate_ground_truth(collection_name: str = "theses-intelligence-artificielle", num_nodes: int = 50):
    """
    Génère un dataset de vérité terrain à partir de nœuds réels extraits de Qdrant.
    """
    load_dotenv()
    setup_settings()
    
    try:
        logger.info(f"Connexion à Qdrant pour récupérer {num_nodes} nœuds de '{collection_name}'...")
        svc = VectorService(collection_name=collection_name)
        
        if not svc.available:
            logger.error("Qdrant n'est pas disponible.")
            return

        # Récupération des points via scroll
        points, _ = svc.client.scroll(
            collection_name=collection_name,
            limit=num_nodes * 2, # On prend un peu plus pour filtrer les petits nœuds
            with_payload=True
        )
        
        if not points:
            logger.error(f"Aucun point trouvé dans la collection {collection_name}.")
            return

        # Filtrage et conversion en nœuds LlamaIndex
        from llama_index.core.schema import TextNode
        nodes = []
        for p in points:
            payload = p.payload or {}
            if "_node_content" in payload:
                node_data = json.loads(payload["_node_content"])
                node = TextNode.from_dict(node_data)
            else:
                node = TextNode(
                    text=payload.get("text", ""),
                    id_=str(p.id),
                    metadata=payload.get("metadata", {})
                )
            
            # On ne garde que les nœuds avec suffisamment de contenu
            if len(node.get_content()) > 200:
                nodes.append(node)
        
        # Mélange et sélection des 50 premiers
        random.shuffle(nodes)
        nodes = nodes[:num_nodes]
        
        logger.info(f"{len(nodes)} nœuds sélectionnés pour la génération.")
        
        # Initialisation du générateur
        generator = RagDatasetGenerator(
            nodes=nodes,
            llm=Settings.llm,
            num_questions_per_chunk=1, # 1 question par nœud pour avoir 50 questions distinctes
            show_progress=True
        )
        
        logger.info("Génération des couples Q/A via LLM...")
        # On utilise generate_dataset_from_nodes pour rester fidèle aux extraits
        dataset = generator.generate_dataset_from_nodes()
        
        # Export
        output_path = "data/ground_truth.json"
        os.makedirs("data", exist_ok=True)
        
        ragas_compatible_data = []
        for item in dataset.examples:
            # On s'assure d'avoir la réponse idéale et le contexte
            ragas_compatible_data.append({
                "question": item.query,
                "ground_truth": item.reference_answer,
                "contexts": item.reference_contexts if item.reference_contexts else [item.reference_contexts]
            })
            
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(ragas_compatible_data, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Dataset de vérité terrain généré avec succès ({len(ragas_compatible_data)} items) : {output_path}")
        
    except Exception as e:
        logger.error(f"Erreur durant la génération : {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    collection = sys.argv[1] if len(sys.argv) > 1 else "theses-intelligence-artificielle"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    generate_ground_truth(collection, limit)
