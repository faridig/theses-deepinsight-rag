
import pytest
from unittest.mock import MagicMock, patch
from src.generation.rag_engine import RAGEngine
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.llms.mock import MockLLM

class TestHybridSearch:

    @patch('src.generation.rag_engine.VectorService')
    @patch('src.generation.rag_engine.OpenAI')
    @patch('src.generation.rag_engine.CohereRerank')
    @patch('src.generation.rag_engine.BM25Retriever')
    def test_hybrid_search_initialization(self, mock_bm25, mock_cohere, mock_openai, mock_vector_service):
        # Setup mocks
        mock_openai.return_value = MockLLM()
        mock_index = MagicMock()
        # Mock docstore to have some nodes
        mock_node = MagicMock()
        mock_index.docstore.docs.values.return_value = [mock_node]
        mock_vector_service.return_value.index = mock_index
        mock_vector_service.return_value.chroma_collection.count.return_value = 1
        
        # Initialize engine
        engine = RAGEngine(storage_path="/tmp/test_chroma", collection_name="test_collection")
        
        # Assertions
        assert isinstance(engine.fusion_retriever, QueryFusionRetriever)
        # Check that BM25 was initialized
        mock_bm25.from_defaults.assert_called()
        assert len(engine.fusion_retriever._retrievers) == 2
