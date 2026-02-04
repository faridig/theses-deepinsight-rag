
from unittest.mock import MagicMock, patch
from src.evaluation.evaluator import ThesesEvaluator

class TestThesesEvaluator:

    @patch('src.evaluation.evaluator.OpenAI')
    @patch('src.evaluation.evaluator.OpenAIEmbedding')
    @patch('src.evaluation.evaluator.llm_factory')
    def test_evaluator_initialization(self, mock_llm_factory, mock_embed, mock_openai):
        evaluator = ThesesEvaluator()
        assert len(evaluator.metrics) == 4

    @patch('src.evaluation.evaluator.OpenAI')
    @patch('src.evaluation.evaluator.OpenAIEmbedding')
    @patch('src.evaluation.evaluator.llm_factory')
    @patch('src.evaluation.evaluator.evaluate')
    def test_evaluate_engine(self, mock_evaluate, mock_llm_factory, mock_embed, mock_openai):
        evaluator = ThesesEvaluator()
        mock_engine = MagicMock()
        dataset = [{"question": "Q1", "ground_truth": "A1"}]
        
        # Mocking the Ragas Result object
        mock_result = MagicMock()
        mock_result.scores = {"faithfulness": 0.9}
        mock_result.__getitem__ = lambda self, key: self.scores[key]
        mock_evaluate.return_value = mock_result
        
        result = evaluator.evaluate_engine(mock_engine, dataset)
        
        assert result.scores["faithfulness"] == 0.9
        mock_evaluate.assert_called_once()
