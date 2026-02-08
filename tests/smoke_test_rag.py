
import pytest
from src.generation.rag_engine import RAGEngine
from unittest.mock import MagicMock, patch
from llama_index.core.embeddings.mock_embed_model import MockEmbedding
from llama_index.core.llms.mock import MockLLM
from llama_index.core.schema import TextNode, NodeWithScore
from llama_index.core.retrievers import QueryFusionRetriever
import os

@patch('src.generation.rag_engine.VectorService')
@patch('src.generation.rag_engine.OpenAI')
@patch('src.generation.rag_engine.OpenAIEmbedding')
def test_hybrid_retriever_instantiation_reality_check(mock_embed, mock_llm, mock_vector_service):
    """
    Test de réalité pour s'assurer que QueryFusionRetriever accepte bien les arguments fournis.
    Ce test instancie réellement QueryFusionRetriever au lieu de le mocker.
    """
    # Setup minimal mocks for dependencies that would hit APIs
    mock_llm.return_value = MockLLM()
    mock_embed.return_value = MockEmbedding(embed_dim=1536)
    
    # Mock VectorService to return nodes for BM25
    mock_vs_instance = mock_vector_service.return_value
    mock_vs_instance.storage_context.docstore.docs = {
        "node_1": TextNode(text="Test content")
    }
    
    # Create a real retriever from the mock service
    mock_vs_instance.get_retriever.return_value = MagicMock()
    
    # This should NOT crash if the mode is correct
    try:
        engine = RAGEngine(storage_path="/tmp/test_smoke", collection_name="test_smoke")
        assert isinstance(engine.fusion_retriever, QueryFusionRetriever)
        print("\n✅ Smoke test passed: QueryFusionRetriever instantiated successfully.")
    except Exception as e:
        pytest.fail(f"Smoke test FAILED: QueryFusionRetriever failed to instantiate. Error: {e}")

if __name__ == "__main__":
    # Manuellement exécutable
    import sys
    from unittest.mock import MagicMock, patch
    
    # Mocking for standalone run
    with patch('src.generation.rag_engine.VectorService'), \
         patch('src.generation.rag_engine.OpenAI'), \
         patch('src.generation.rag_engine.OpenAIEmbedding'):
        test_hybrid_retriever_instantiation_reality_check(MagicMock(), MagicMock(), MagicMock())
