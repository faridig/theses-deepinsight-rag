import logging
import pandas as pd
import os
from typing import List, Dict
from llama_index.core.query_engine import BaseQueryEngine
from ragas import EvaluationDataset
from ragas.metrics import (
    Faithfulness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
)
from openai import OpenAI as OpenAIClient
from langchain_openai import OpenAIEmbeddings as LangchainOpenAIEmbeddings
from ragas.llms import llm_factory
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.integrations.llama_index import evaluate
from ragas.run_config import RunConfig

# Silence Technique Strict
for lib in ["opentelemetry", "ragas", "pydantic", "httpx", "urllib3", "openai"]:
    logging.getLogger(lib).setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

class ThesesEvaluator:
    """
    Evaluateur Ragas optimisé pour la résilience aux Rate Limits.
    """
    def __init__(self, model: str = "gpt-4o"):
        api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAIClient(api_key=api_key)
        
        self.evaluator_llm = llm_factory(model=model, client=client)
        base_embeddings = LangchainOpenAIEmbeddings(model="text-embedding-3-small")
        self.embeddings = LangchainEmbeddingsWrapper(base_embeddings)
        
        self.metrics = [
            Faithfulness(llm=self.evaluator_llm),
            AnswerRelevancy(llm=self.evaluator_llm, embeddings=self.embeddings),
            ContextPrecision(llm=self.evaluator_llm),
            ContextRecall(llm=self.evaluator_llm),
        ]

    def evaluate_engine(self, query_engine: BaseQueryEngine, dataset: List[Dict[str, str]]):
        logger.info(f"Évaluation Ragas ({len(dataset)} questions)...")
        
        formatted_dataset = [
            {"user_input": item.get("question"), "reference": item.get("ground_truth")}
            for item in dataset
        ]
        
        try:
            eval_dataset = EvaluationDataset.from_list(formatted_dataset)
            
            # Robustesse maximale contre les erreurs 429
            # max_workers=1 est impératif pour les clés Trial
            run_config = RunConfig(
                max_retries=10,
                timeout=300,
                max_workers=1
            )
            
            result = evaluate(
                query_engine=query_engine,
                metrics=self.metrics,
                dataset=eval_dataset,
                run_config=run_config,
                show_progress=True
            )
            return result
        except Exception as e:
            if "429" in str(e):
                logger.error("Échec évaluation: Quota API atteint (429).")
            else:
                logger.error(f"Erreur évaluation Ragas: {e}")
            return None

    def export_to_phoenix(self, evaluation_result):
        if not evaluation_result:
            return False
        
        try:
            eval_scores_df = pd.DataFrame(evaluation_result.scores)
            # Phoenix export logic here if needed, usually handle via traces
            for eval_name in eval_scores_df.columns:
                mean_score = eval_scores_df[eval_name].mean()
                logger.info(f"Score {eval_name}: {mean_score:.4f}")
            return True
        except Exception as e:
            logger.error(f"Erreur export Phoenix: {e}")
            return False
