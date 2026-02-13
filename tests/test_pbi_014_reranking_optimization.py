
from unittest.mock import MagicMock, patch
from src.generation.rag_engine import RAGEngine, RETRIEVAL_TOP_K
from llama_index.core.llms.mock import MockLLM

class TestRerankingOptimization:

    @patch('src.generation.rag_engine.VectorService')
    @patch('llama_index.llms.openai.OpenAI')
    @patch('src.generation.rag_engine.CohereRerank')
    @patch('src.generation.rag_engine.BM25Retriever')
    def test_top_k_reduction_config(self, mock_bm25, mock_cohere, mock_openai, mock_vector_service):
        """
        Vérifie que le top_k est bien réduit à 10 comme spécifié dans le PBI-014.
        """
        # Setup mocks
        mock_openai.return_value = MockLLM()
        mock_index = MagicMock()
        mock_node = MagicMock()
        mock_index.docstore.docs.values.return_value = [mock_node]
        mock_index.as_retriever.return_value = MagicMock()
        mock_vector_service.return_value.index = mock_index
        mock_vector_service.return_value.chroma_collection.count.return_value = 1
        
        # Initialize engine
        engine = RAGEngine(storage_path="/tmp/test_chroma", collection_name="test_collection")
        _ = engine.index # Déclenche l'initialisation
        
        # Scenario 1: Réduction du top_k
        assert RETRIEVAL_TOP_K == 10
        
        # Vérification des appels aux retrievers
        mock_index.as_retriever.assert_called_with(similarity_top_k=10)
        mock_bm25.from_defaults.assert_called()
        args, kwargs = mock_bm25.from_defaults.call_args
        assert kwargs['similarity_top_k'] == 10
        
        # Vérification du FusionRetriever
        assert engine.fusion_retriever.similarity_top_k == 10
        
    def test_top_k_value_is_10(self):
        assert RETRIEVAL_TOP_K == 10
