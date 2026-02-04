
import logging
import pandas as pd
from typing import List, Dict
from llama_index.llms.openai import OpenAI
from llama_index.core.query_engine import BaseQueryEngine
from ragas.metrics import (
    Faithfulness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
)
from ragas.llms import LlamaIndexLLMWrapper
from ragas.integrations.llama_index import evaluate
import phoenix as px

logger = logging.getLogger(__name__)

class ThesesEvaluator:
    """
    Evaluateur pour le système RAG utilisant le framework Ragas.
    """
    def __init__(self, model: str = "gpt-4o"):
        self.llm = OpenAI(model=model)
        self.evaluator_llm = LlamaIndexLLMWrapper(llm=self.llm)
        
        # Initialisation des métriques
        self.metrics = [
            Faithfulness(llm=self.evaluator_llm),
            AnswerRelevancy(llm=self.evaluator_llm),
            ContextPrecision(llm=self.evaluator_llm),
            ContextRecall(llm=self.evaluator_llm),
        ]

    def evaluate_engine(self, query_engine: BaseQueryEngine, dataset: List[Dict[str, str]]):
        """
        Évalue un QueryEngine sur un dataset donné.
        dataset: Liste de dictionnaires avec 'question' et 'ground_truth'.
        """
        logger.info(f"Démarrage de l'évaluation Ragas sur {len(dataset)} questions...")
        
        try:
            result = evaluate(
                query_engine=query_engine,
                metrics=self.metrics,
                dataset=dataset
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
                px.Client()
            except Exception:
                logger.warning("Client Phoenix non accessible. Les scores ne seront pas loggués.")
                return False
            
            for eval_name in eval_scores_df.columns:
                mean_score = eval_scores_df[eval_name].mean()
                logger.info(f"Score moyen pour {eval_name}: {mean_score}")
                
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'export vers Phoenix : {e}")
            return False
