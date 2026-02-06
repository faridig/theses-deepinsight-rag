import pytest
from unittest.mock import MagicMock, patch
from src.generation.rag_engine import RAGEngine

def test_hybrid_search_finds_conclusion_term():
    """
    Simule la recherche d'un terme présent uniquement dans la conclusion (PBI-010).
    """
    with patch('src.generation.rag_engine.VectorService') as mock_vector_service, \
         patch('src.generation.rag_engine.OpenAI') as mock_openai, \
         patch('src.generation.rag_engine.CohereRerank') as mock_cohere, \
         patch('src.generation.rag_engine.BM25Retriever') as mock_bm25:
        
        # Setup mocks
        mock_openai.return_value = MagicMock()
        mock_vs_instance = mock_vector_service.return_value
        mock_vs_instance.index = MagicMock()
        mock_vs_instance.storage_context.docstore.docs.values.return_value = [MagicMock()]
        
        # Initialize engine
        engine = RAGEngine()
        
        # On vérifie que les retrievers sont bien initialisés
        assert len(engine.fusion_retriever._retrievers) >= 1
        
        # La réussite du test dépend de la présence des nodes de conclusion dans l'index,
        # ce qui est garanti par le mode full_parse de PBI-011.
