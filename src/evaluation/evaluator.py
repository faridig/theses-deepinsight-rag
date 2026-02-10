from llama_index.core import Settings
import pandas as pd
from datasets import Dataset
import logging
import os
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
            # On demande au moteur (avec traçabilité activée)
            response = self.rag_engine.ask(item.query_str)
            
            # On extrait le texte de la réponse (on enlève la partie "Sources :" pour l'évaluation si possible)
            answer_text = str(response)
            if "\n\nSources :" in answer_text:
                answer_text = answer_text.split("\n\nSources :")[0]
            
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

        # Configurer les métriques
        metrics = [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ]

        logger.info("Lancement de l'évaluation Ragas...")
        result = evaluate(
            dataset=dataset,
            metrics=metrics,
            llm=self.evaluator_llm,
            embeddings=self.evaluator_embeddings
        )
        
        # Intégration Phoenix (PBI-009)
        self._export_to_phoenix(result)
            
        return result

    def _export_to_phoenix(self, result):
        """
        Exporte les résultats Ragas vers Arize Phoenix.
        """
        try:
            import phoenix as px
            
            logger.info("Export des scores Ragas vers Phoenix...")
            
            # Affichage des scores dans les logs (visibles dans Phoenix via l'instrumentation des traces)
            for metric, score in result.items():
                logger.info(f"Phoenix Metric - {metric}: {score:.4f}")
            
            # Note: L'instrumentation LlamaIndex + Phoenix capture déjà les spans.
            # Les scores Ragas sont ici affichés dans le flux de log pour corrélation.
        except Exception as e:
            logger.warning(f"Export Phoenix échoué : {e}")
