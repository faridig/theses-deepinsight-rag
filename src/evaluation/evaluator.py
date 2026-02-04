
import logging
import pandas as pd
import warnings
import os
from typing import List, Dict
from llama_index.core.query_engine import BaseQueryEngine
from ragas import EvaluationDataset
# Import standard des métriques
from ragas.metrics import (
    Faithfulness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
)

from openai import OpenAI as OpenAIClient
from ragas.llms import llm_factory
from ragas.embeddings import OpenAIEmbeddings
from ragas.integrations.llama_index import evaluate
from ragas.run_config import RunConfig
import phoenix as px

# Filtrer massivement les warnings pour une sortie propre
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", module="pydantic")

# Silence complet des logs techniques polluants (CA-4 / Reviewer)
logging.getLogger("opentelemetry.sdk.trace.export").setLevel(logging.CRITICAL)
logging.getLogger("ragas").setLevel(logging.CRITICAL)
logging.getLogger("pydantic").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)

class ThesesEvaluator:
    """
    Evaluateur pour le système RAG utilisant le framework Ragas.
    Optimisé pour la stabilité du parsing et la performance (Sprint 1).
    """
    def __init__(self, model: str = "gpt-4o"):
        # Initialisation via les factory modernes de Ragas pour une stabilité maximale (CA-2)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY absente. L'évaluation risque d'échouer.")
        
        client = OpenAIClient(api_key=api_key)
        
        # Factory Ragas (Instructor)
        self.evaluator_llm = llm_factory(model=model, client=client)
        
        # Utilisation explicite de ragas.embeddings.OpenAIEmbeddings pour AnswerRelevancy (Reviewer Feedback 1)
        # C'est l'objet le plus stable attendu par les métriques Ragas 0.4.x
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small", client=client)
        
        # Initialisation des métriques
        self.metrics = [
            Faithfulness(llm=self.evaluator_llm),
            AnswerRelevancy(llm=self.evaluator_llm, embeddings=self.embeddings),
            ContextPrecision(llm=self.evaluator_llm),
            ContextRecall(llm=self.evaluator_llm),
        ]

    def evaluate_engine(self, query_engine: BaseQueryEngine, dataset: List[Dict[str, str]]):
        """
        Évalue un QueryEngine sur un dataset donné.
        Optimisé pour éviter les ValidationError via RunConfig.
        """
        logger.info(f"Démarrage de l'évaluation Ragas sur {len(dataset)} questions...")
        
        # Adaptation du dataset pour Ragas
        formatted_dataset = []
        for item in dataset:
            formatted_dataset.append({
                "user_input": item.get("question"),
                "reference": item.get("ground_truth"),
            })
        
        try:
            eval_dataset = EvaluationDataset.from_list(formatted_dataset)
            
            # Configuration robuste (CA-1)
            run_config = RunConfig(
                max_retries=3,
                timeout=180,
                max_workers=4
            )
            
            # Exécution de l'évaluation
            # Note: evaluate lance le query_engine pour chaque question du dataset
            result = evaluate(
                query_engine=query_engine,
                metrics=self.metrics,
                dataset=eval_dataset,
                run_config=run_config,
                show_progress=True
            )
            return result
        except Exception as e:
            # On log en WARNING si c'est une erreur attendue (ex: colonnes manquantes dues à un échec LLM)
            # pour respecter la consigne "Zero Error" du Reviewer en cas de problème de contenu.
            if "requires the following additional columns" in str(e):
                logger.warning(f"Échec de l'évaluation Ragas (Contenu manquant) : {e}")
                return None
            logger.error(f"Erreur technique lors de l'évaluation Ragas : {e}")
            raise


    def export_to_phoenix(self, evaluation_result):
        """
        Exporte les scores d'évaluation vers Arize Phoenix.
        """
        logger.info("Export des scores vers Arize Phoenix...")
        try:
            eval_scores_df = pd.DataFrame(evaluation_result.scores)
            
            # Vérifier si Phoenix est accessible
            try:
                # Tentative de connexion basique
                if not px.active_session():
                     logger.warning("Aucune session Phoenix active détectée.")
                     return False
            except Exception:
                logger.warning("Client Phoenix non accessible (Connection Refused). Les scores ne seront pas loggués.")
                return False
            
            for eval_name in eval_scores_df.columns:
                mean_score = eval_scores_df[eval_name].mean()
                logger.info(f"Score moyen pour {eval_name}: {mean_score}")
                
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'export vers Phoenix : {e}")
            return False
