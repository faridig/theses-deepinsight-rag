from llama_index.core import Settings
import pandas as pd
from datasets import Dataset
import logging
from ragas.llms import LlamaIndexLLMWrapper
from ragas.embeddings import LlamaIndexEmbeddingsWrapper
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)

logger = logging.getLogger(__name__)

class RagasTestItem:
    """
    Élément de test pour l'évaluation Ragas.
    """
    def __init__(self, query_str: str, expected_response: str, expected_context: list[str]):
        self.query_str = query_str
        self.expected_response = expected_response
        self.expected_context = expected_context
    
class RagasEvaluator:
    """
    Évaluateur utilisant le framework Ragas pour valider la qualité du RAG.
    """
    def __init__(self, rag_engine):
        self.rag_engine = rag_engine
        # On utilise les wrappers Ragas pour LlamaIndex
        self.evaluator_llm = LlamaIndexLLMWrapper(Settings.llm)
        self.evaluator_embeddings = LlamaIndexEmbeddingsWrapper(Settings.embed_model)

    def run_evaluation(self, test_items: list[RagasTestItem]):
        """
        Exécute l'évaluation sur une liste de questions de test.
        """
        questions = []
        answers = []
        contexts = []
        ground_truths = []

        for item in test_items:
            logger.info(f"Évaluation de la question : {item.query_str}")
            response = self.rag_engine.ask(item.query_str)
            
            # On extrait le texte de la réponse
            answer_text = str(response)
            
            # On récupère les contextes réellement retrouvés par le moteur
            actual_contexts = [node.get_content() for node in response.source_nodes] if hasattr(response, "source_nodes") else []

            questions.append(item.query_str)
            answers.append(answer_text)
            contexts.append(actual_contexts)
            ground_truths.append(item.expected_response)

        data = {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        }
        
        dataset = Dataset.from_dict(data)
        
        from ragas import evaluate

        # Configurer les métriques avec le LLM et les Embeddings appropriés
        metrics = [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ]

        logger.info("Lancement de l'évaluation Ragas...")
        # Note: Dans les versions récentes de Ragas, on peut passer llm et embeddings à evaluate
        result = evaluate(
            dataset=dataset,
            metrics=metrics,
            llm=self.evaluator_llm,
            embeddings=self.evaluator_embeddings
        )
        
        return result
