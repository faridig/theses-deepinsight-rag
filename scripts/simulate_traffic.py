import asyncio
import logging
import os
import sys
import random
from typing import List

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import setup_settings
from src.generation.rag_engine import RAGEngine
from src.indexing.vector_service import VectorService
from llama_index.core.llama_dataset.generator import RagDatasetGenerator
from llama_index.core import Settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("simulate_traffic")

MANUAL_QUESTIONS = {
    "theses-intelligence-artificielle": [
        "Quels sont les enjeux éthiques de l'intelligence artificielle ?",
        "Comment l'IA transforme-t-elle le secteur de la santé ?",
        "Expliquez le concept d'apprentissage profond."
    ],
    "theses-agriculture": [
        "Quels sont les impacts du changement climatique sur l'agriculture ?",
        "Comment l'agriculture de précision peut-elle réduire l'usage des pesticides ?",
        "Quelles sont les nouvelles techniques d'irrigation durable ?"
    ],
    "theses-droit": [
        "Quels sont les principes fondamentaux du droit civil ?",
        "Comment le droit s'adapte-t-il aux nouvelles technologies ?",
        "Expliquez la hiérarchie des normes en droit français."
    ]
}

async def generate_questions(theme: str, num_questions: int) -> List[str]:
    logger.info(f"Génération de {num_questions} questions pour le thème {theme}...")
    vector_service = VectorService(collection_name=theme)
    nodes = vector_service.get_all_nodes()
    
    if not nodes:
        logger.warning(f"Aucun nœud trouvé pour le thème {theme}. Utilisation de questions manuelles uniquement.")
        return MANUAL_QUESTIONS.get(theme, ["Question générique ?"])

    # On prend quelques nœuds au hasard pour varier les questions
    sample_nodes = random.sample(list(nodes), min(len(nodes), 10))
    
    generator = RagDatasetGenerator.from_documents(
        documents=sample_nodes,
        llm=Settings.llm,
        num_questions_per_chunk=2,
        show_progress=False
    )
    
    try:
        dataset = generator.generate_dataset_from_nodes()
        questions = [item.query for item in dataset.examples]
        return questions[:num_questions]
    except Exception as e:
        logger.error(f"Erreur lors de la génération pour {theme}: {e}")
        return MANUAL_QUESTIONS.get(theme, ["Question générique ?"])

async def run_simulation():
    setup_settings()
    engine = RAGEngine()
    
    # On récupère les thèmes réels (slugs)
    available_collections = engine.get_available_themes()
    target_themes = ["theses-intelligence-artificielle", "theses-agriculture", "theses-droit"]
    
    # On ne garde que ceux qui existent vraiment
    themes_to_test = [t for t in target_themes if t in available_collections]
    
    if not themes_to_test:
        logger.error("Aucun des thèmes cibles n'a été trouvé dans Qdrant.")
        return

    questions_per_theme = 50 // len(themes_to_test)
    
    logger.info(f"Début de la simulation sur {len(themes_to_test)} thèmes.")
    
    total_executed = 0
    
    for theme in themes_to_test:
        # Mélange de synthétique et manuel
        synth_questions = await generate_questions(theme, questions_per_theme - 3)
        manual_questions = MANUAL_QUESTIONS.get(theme, [])
        theme_questions = synth_questions + manual_questions
        
        logger.info(f"Exécution de {len(theme_questions)} requêtes pour le thème {theme}...")
        
        for q in theme_questions:
            # On exécute séquentiellement ou avec un petit sémaphore pour ne pas exploser les rate limits
            logger.info(f"[{theme}] Question: {q}")
            try:
                await engine.aask(q, theme=theme)
                total_executed += 1
                logger.info(f"[{theme}] Réponse reçue ({total_executed}/50)")
            except Exception as e:
                logger.error(f"Erreur lors de la requête: {e}")
            
            # Petit délai pour Phoenix et les API
            await asyncio.sleep(0.5)

    logger.info(f"Simulation terminée. {total_executed} requêtes exécutées.")

if __name__ == "__main__":
    asyncio.run(run_simulation())
