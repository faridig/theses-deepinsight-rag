import pytest
from unittest.mock import MagicMock, patch
from llama_index.core.base.response.schema import Response
from llama_index.core.llms.mock import MockLLM
from llama_index.core.schema import QueryBundle

# Patch Phoenix at module level before importing src.generation.rag_engine
with patch('phoenix.launch_app'), patch('llama_index.core.set_global_handler'):
    from src.generation.rag_engine import RAGEngine

class TestRAGEngine:
    @patch('src.generation.rag_engine.VectorService')
    @patch('src.generation.rag_engine.OpenAI')
    def test_rag_engine_initialization(self, mock_openai, mock_vector_service):
        # Setup mocks
        mock_openai.return_value = MockLLM()
        mock_index = MagicMock()
        mock_vector_service.return_value.index = mock_index
        mock_query_engine = MagicMock()
        mock_index.as_query_engine.return_value = mock_query_engine
        
        # Initialize engine
        engine = RAGEngine(storage_path="/tmp/test_chroma", collection_name="test_collection")
        
        # Assertions
        assert engine.index == mock_index
        mock_index.as_query_engine.assert_called_once()
        mock_query_engine.update_prompts.assert_called_once()
        
    @patch('src.generation.rag_engine.VectorService')
    @patch('src.generation.rag_engine.OpenAI')
    def test_rag_engine_ask(self, mock_openai, mock_vector_service):
        # Setup mocks
        mock_openai.return_value = MockLLM()
        mock_index = MagicMock()
        mock_vector_service.return_value.index = mock_index
        mock_query_engine = MagicMock()
        mock_index.as_query_engine.return_value = mock_query_engine
        
        expected_response = Response(response="Ceci est une réponse de test.", source_nodes=[])
        mock_query_engine.query.return_value = expected_response
        
        # Initialize and ask
        engine = RAGEngine(storage_path="/tmp/test_chroma", collection_name="test_collection")
        response = engine.ask("Quelle est la question ?")
        
        # Assertions
        assert response.response == "Ceci est une réponse de test."
        # With HyDE, query is called with a QueryBundle
        args, _ = mock_query_engine.query.call_args
        if isinstance(args[0], QueryBundle):
            assert args[0].query_str == "Quelle est la question ?"
        else:
            assert args[0] == "Quelle est la question ?"

    @patch('src.generation.rag_engine.VectorService')
    @patch('src.generation.rag_engine.OpenAI')
    def test_rag_engine_ask_empty_question(self, mock_openai, mock_vector_service):
        # Setup mocks
        mock_openai.return_value = MockLLM()
        mock_index = MagicMock()
        mock_vector_service.return_value.index = mock_index
        
        engine = RAGEngine(storage_path="/tmp/test_chroma", collection_name="test_collection")
        response = engine.ask("")
        
        assert response == "Veuillez poser une question valide."
