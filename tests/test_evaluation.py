
from unittest.mock import MagicMock, patch
from src.evaluation.evaluator import ThesesEvaluator

class TestThesesEvaluator:

    @patch('src.evaluation.evaluator.OpenAI')
    @patch('src.evaluation.evaluator.llm_factory')
    def test_evaluator_initialization(self, mock_llm_factory, mock_openai):
        evaluator = ThesesEvaluator()
        assert len(evaluator.metrics) == 4
        mock_openai.assert_called_once()
        mock_llm_factory.assert_called_once()

    @patch('src.evaluation.evaluator.OpenAI')
    @patch('src.evaluation.evaluator.llm_factory')
    @patch('src.evaluation.evaluator.evaluate')
    def test_evaluate_engine(self, mock_evaluate, mock_llm_factory, mock_openai):
        evaluator = ThesesEvaluator()
        mock_engine = MagicMock()
        dataset = [{"question": "Q1", "ground_truth": "A1"}]
        
        mock_evaluate.return_value = MagicMock(scores={"faithfulness": 0.9})
        
        result = evaluator.evaluate_engine(mock_engine, dataset)
        
        assert result.scores["faithfulness"] == 0.9
        mock_evaluate.assert_called_once()
