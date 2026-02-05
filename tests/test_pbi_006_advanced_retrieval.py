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
            
            # 1. Vérification du pool de candidats (PBI-006 : top_k=20 exigé pour la précision)
            mock_index.as_retriever.assert_called_with(similarity_top_k=20)
            
            # 2. Vérification de QueryFusionRetriever (Optimisation CA-4)
            mock_fusion.assert_called_once()
            _, fusion_kwargs = mock_fusion.call_args
            # num_queries=1 pour éviter l'expansion coûteuse
            assert fusion_kwargs['num_queries'] == 1
            # similarity_top_k=10 pour le compromis vitesse/reranking
            assert fusion_kwargs['similarity_top_k'] == 10
            assert "RECIPROCAL_RANK" in str(fusion_kwargs['mode'])
            assert fusion_kwargs['use_async'] is True
            
            # 3. Vérification du Reranker Cohere (Top 5 exigé)
            mock_cohere.assert_called_once()
            _, cohere_kwargs = mock_cohere.call_args
            assert cohere_kwargs['top_n'] == 5
            
            # 4. Vérification de l'assemblage final
            mock_retriever_qe.assert_called_once()
            qe_kwargs = mock_retriever_qe.call_args[1]
            assert qe_kwargs['retriever'] == mock_fusion.return_value
            # Doit inclure MetadataReplacementPostProcessor et CohereRerank
            post_processors = qe_kwargs['node_postprocessors']
            assert len(post_processors) >= 2
            # Check for CohereRerank in post-processors
            assert any(p == mock_cohere.return_value for p in post_processors)
