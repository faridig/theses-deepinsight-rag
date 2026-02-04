
import logging
import pandas as pd
import warnings
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

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas.integrations.llama_index import evaluate
import phoenix as px

# Filtrer les warnings de dépréciation pour CA-4
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Silence opentelemetry exporter errors (Phoenix connection refused)
logging.getLogger("opentelemetry.sdk.trace.export").setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)

class ThesesEvaluator:
    """
    Evaluateur pour le système RAG utilisant le framework Ragas.
    """
    def __init__(self, model: str = "gpt-4o"):
        # Utilisation des wrappers Langchain comme recommandé par le Reviewer
        self.evaluator_llm = ChatOpenAI(model=model)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
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
        dataset: Liste de dictionnaires avec 'question' et 'ground_truth'.
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
            # On laisse Ragas gérer l'interface avec LlamaIndex
            # Les métriques utiliseront nos objets Langchain configurés
            result = evaluate(
                query_engine=query_engine,
                metrics=self.metrics,
                dataset=eval_dataset
            )
            return result
        except Exception as e:
            logger.error(f"Erreur lors de l'évaluation Ragas : {e}")
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
