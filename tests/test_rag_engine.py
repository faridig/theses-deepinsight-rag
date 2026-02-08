from unittest.mock import MagicMock, patch, AsyncMock
from src.generation.rag_engine import RAGEngine
from llama_index.core.base.response.schema import Response
from llama_index.core.embeddings.mock_embed_model import MockEmbedding
from llama_index.core.llms.mock import MockLLM
from llama_index.core.schema import NodeWithScore, TextNode

class TestRAGEngine:

    @patch('src.generation.rag_engine.VectorService')
    @patch('src.generation.rag_engine.OpenAI')
    @patch('src.generation.rag_engine.CohereRerank')
    @patch('src.generation.rag_engine.OpenAIEmbedding')
    def test_rag_engine_initialization(self, mock_embed, mock_cohere, mock_openai, mock_vector_service):
        # Setup mocks
        mock_openai.return_value = MockLLM()
        mock_embed.return_value = MockEmbedding(embed_dim=1536)
        mock_vector_service.return_value.index = MagicMock()
    
        # Initialize engine
        engine = RAGEngine(storage_path="/tmp/test_chroma", collection_name="test_collection")
        
        # Assertions
        assert engine.vector_service is not None
        
    @patch('src.generation.rag_engine.VectorService')
    @patch('src.generation.rag_engine.OpenAI')
    @patch('src.generation.rag_engine.CohereRerank')
    @patch('src.generation.rag_engine.OpenAIEmbedding')
    def test_rag_engine_ask(self, mock_embed, mock_cohere, mock_openai, mock_vector_service):
        # Setup mocks
        mock_openai.return_value = MockLLM()
        mock_embed.return_value = MockEmbedding(embed_dim=1536)
        mock_vector_service.return_value.index = MagicMock()
    
        # Initialize
        engine = RAGEngine(storage_path="/tmp/test_chroma", collection_name="test_collection")
        
        # Mock query engine
        engine.query_engine = MagicMock()
        
        # Create a mock source node
        node = TextNode(text="Le texte extrait de la thèse.", metadata={"page_label": "42", "titre": "Ma Thèse"})
        source_nodes = [NodeWithScore(node=node, score=0.9)]
        
        expected_response = Response(response="Ceci est une réponse de test.", source_nodes=source_nodes)
        engine.query_engine.aquery = AsyncMock(return_value=expected_response)
        
        response = engine.ask("Quelle est la question ?")
        
        # Assertions
        assert "Ceci est une réponse de test." in response
        assert "Sources:" in response
        assert "Page 42" in response
        assert "Ma Thèse" in response
        assert "Le texte extrait" in response

    @patch('src.generation.rag_engine.VectorService')
    @patch('src.generation.rag_engine.OpenAI')
    @patch('src.generation.rag_engine.CohereRerank')
    @patch('src.generation.rag_engine.OpenAIEmbedding')
    def test_rag_engine_ask_empty_question(self, mock_embed, mock_cohere, mock_openai, mock_vector_service):
        # Setup mocks
        mock_openai.return_value = MockLLM()
        mock_embed.return_value = MockEmbedding(embed_dim=1536)
    
        engine = RAGEngine(storage_path="/tmp/test_chroma", collection_name="test_collection")
        response = engine.ask("")
        
        assert response == "Veuillez poser une question valide."
