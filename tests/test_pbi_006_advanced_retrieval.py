import os
from unittest.mock import MagicMock, patch
from src.generation.rag_engine import RAGEngine
from llama_index.core.llms.mock import MockLLM

class TestAdvancedRetrieval:
    @patch('src.generation.rag_engine.VectorService')
    @patch('src.generation.rag_engine.OpenAI')
    @patch('src.generation.rag_engine.CohereRerank')
    @patch('src.generation.rag_engine.QueryFusionRetriever')
    @patch('src.generation.rag_engine.RetrieverQueryEngine')
    def test_advanced_retrieval_setup(self, mock_retriever_qe, mock_fusion, mock_cohere, mock_openai, mock_vector_service):
        # Setup environment variable for Cohere
        with patch.dict(os.environ, {"COHERE_API_KEY": "test_key"}):
            # Setup mocks
            mock_openai.return_value = MockLLM()
            mock_index = MagicMock()
            mock_vector_service.return_value.index = mock_index
            mock_base_retriever = MagicMock()
            mock_index.as_retriever.return_value = mock_base_retriever
            
            # Initialize engine
            _ = RAGEngine(storage_path="/tmp/test_chroma", collection_name="test_collection")
            
            # Assertions for QueryFusionRetriever
            mock_fusion.assert_called_once()
            args, kwargs = mock_fusion.call_args
            # The first arg should be a list containing the base retriever
            assert mock_base_retriever in args[0]
            # PBI-006: similarity_top_k=20 exigé pour la précision technique
            assert kwargs['num_queries'] == 1
            assert kwargs['similarity_top_k'] == 20
            # mode is an enum
            assert "RECIPROCAL_RANK" in str(kwargs['mode'])
            assert kwargs['use_async'] is True
            
            # Assertions for CohereRerank
            mock_cohere.assert_called_once()
            _, cohere_kwargs = mock_cohere.call_args
            assert cohere_kwargs['top_n'] == 5
            assert cohere_kwargs['api_key'] == "test_key"
            assert cohere_kwargs['model'] == "rerank-multilingual-v3.0"
            
            # Assertions for RetrieverQueryEngine
            mock_retriever_qe.assert_called_once()
            qe_args, qe_kwargs = mock_retriever_qe.call_args
            # Check retriever (could be positional or keyword)
            retriever = qe_kwargs.get('retriever') or qe_args[0]
            assert retriever == mock_fusion.return_value
            # Should have node_postprocessors including cohere and MetadataReplacementPostProcessor
            post_processors = qe_kwargs['node_postprocessors']
            assert any(isinstance(p, MagicMock) and p == mock_cohere.return_value for p in post_processors)
            # Check for the presence of MetadataReplacementPostProcessor (which is in self.post_processors)
            assert any('MetadataReplacementPostProcessor' in str(type(p)) or p.__class__.__name__ == 'MetadataReplacementPostProcessor' for p in post_processors)
