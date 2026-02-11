from unittest.mock import MagicMock, patch
from src.generation.rag_engine import RAGEngine
from llama_index.core.base.response.schema import Response
from llama_index.core.llms.mock import MockLLM

class TestRAGEngine:

    @patch('src.generation.rag_engine.VectorService')
    @patch('src.generation.rag_engine.OpenAI')
    @patch('src.generation.rag_engine.CohereRerank')
    def test_rag_engine_initialization(self, mock_cohere, mock_openai, mock_vector_service):
        # Setup mocks
        mock_openai.return_value = MockLLM()
        mock_index = MagicMock()
        mock_vector_service.return_value.index = mock_index
        
        # Initialize engine
        engine = RAGEngine(storage_path="/tmp/test_chroma", collection_name="test_collection")
        
        # Assertions
        assert engine.index == mock_index
        
    @patch('src.generation.rag_engine.VectorService')
    @patch('src.generation.rag_engine.OpenAI')
    @patch('src.generation.rag_engine.CohereRerank')
    def test_rag_engine_ask(self, mock_cohere, mock_openai, mock_vector_service):
        # Setup mocks
        mock_openai.return_value = MockLLM()
        mock_index = MagicMock()
        mock_vector_service.return_value.index = mock_index
        
        # Initialize and ask
        engine = RAGEngine(storage_path="/tmp/test_chroma", collection_name="test_collection")
        
        # Mock query engine aquery method (since ask now calls aask -> aquery)
        engine.query_engine = MagicMock()
        expected_response = Response(response="Ceci est une réponse de test.", source_nodes=[])
        
        async def mock_aquery(q):
            return expected_response
            
        engine.query_engine.aquery = mock_aquery
        
        response = engine.ask("Quelle est la question ?")
        
        # Assertions
        assert response.response == "Ceci est une réponse de test."

    @patch('src.generation.rag_engine.VectorService')
    @patch('src.generation.rag_engine.OpenAI')
    @patch('src.generation.rag_engine.CohereRerank')
    def test_rag_engine_ask_empty_question(self, mock_cohere, mock_openai, mock_vector_service):
        # Setup mocks
        mock_openai.return_value = MockLLM()
        mock_index = MagicMock()
        mock_vector_service.return_value.index = mock_index
        
        engine = RAGEngine(storage_path="/tmp/test_chroma", collection_name="test_collection")
        response = engine.ask("")
        
        assert response == "Veuillez poser une question valide."
