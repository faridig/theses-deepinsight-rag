
from unittest.mock import MagicMock, patch
from src.evaluation.evaluator import ThesesEvaluator

class TestThesesEvaluator:

    @patch('src.evaluation.evaluator.OpenAIClient')
    @patch('src.evaluation.evaluator.llm_factory')
    @patch('src.evaluation.evaluator.LangchainOpenAIEmbeddings')
    @patch('src.evaluation.evaluator.LangchainEmbeddingsWrapper')
    def test_evaluator_initialization(self, mock_emb_wrapper, mock_langchain_emb, mock_llm_factory, mock_openai_client):
        evaluator = ThesesEvaluator()
        assert len(evaluator.metrics) == 4

    @patch('src.evaluation.evaluator.OpenAIClient')
    @patch('src.evaluation.evaluator.llm_factory')
    @patch('src.evaluation.evaluator.LangchainOpenAIEmbeddings')
    @patch('src.evaluation.evaluator.LangchainEmbeddingsWrapper')
    @patch('src.evaluation.evaluator.evaluate')
    @patch('src.evaluation.evaluator.RunConfig')
    def test_evaluate_engine(self, mock_run_config, mock_evaluate, mock_emb_wrapper, mock_langchain_emb, mock_llm_factory, mock_openai_client):
        evaluator = ThesesEvaluator()
        mock_engine = MagicMock()
        dataset = [{"question": "Q1", "ground_truth": "A1"}]
        
        # Mocking the Ragas Result object
        mock_result = MagicMock()
        mock_result.scores = {"faithfulness": 0.9}
        # Utilisation de dict pour éviter les erreurs de type dans les mocks
        mock_result.__getitem__ = lambda self, key: self.scores.get(key)
        mock_evaluate.return_value = mock_result
        
        result = evaluator.evaluate_engine(mock_engine, dataset)
        
        assert result.scores["faithfulness"] == 0.9
        mock_evaluate.assert_called_once()
