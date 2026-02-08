import pytest
import os
from llama_index.core.schema import TextNode, Document
from src.indexing.vector_service import VectorService
from llama_index.core import Settings
from llama_index.core.embeddings.mock_embed_model import MockEmbedding

@pytest.fixture
def storage_path(tmp_path):
    """Fixture to provide a temporary storage path for each test."""
    path = tmp_path / "chroma"
    os.makedirs(path, exist_ok=True)
    return str(path)

@pytest.fixture
def mock_settings():
    """Fixture to mock settings for faster testing."""
    Settings.embed_model = MockEmbedding(embed_dim=1536)
    yield

def test_vector_service_indexing_and_retrieval(storage_path, mock_settings):
    # Initialize service
    service = VectorService(storage_path=storage_path, collection_name="test_collection")
    
    # Create test documents
    doc1 = Document(
        text="Ceci est le contenu de la thèse sur l'intelligence artificielle.",
        metadata={"title": "Thèse AI", "window": "Contexte de la thèse sur l'IA."}
    )
    doc2 = Document(
        text="L'apprentissage profond révolutionne le domaine médical.",
        metadata={"title": "IA Médicale", "window": "Contexte de l'IA en médecine."}
    )
    
    documents = [doc1, doc2]
    
    # Index documents
    service.index_documents(documents)
    
    # Check that index is created
    assert service.index is not None
    
    # Search for a query matching doc 2
    results = service.query("apprentissage profond", similarity_top_k=1)
    
    # Verify results
    assert len(results) > 0
    top_node = results[0].node
    
    # Since MockEmbedding is random, we check that whichever node is returned has its correct metadata
    if "apprentissage profond" in top_node.get_content():
        assert top_node.metadata["window"] == "Contexte de l'IA en médecine."
        assert top_node.metadata["title"] == "IA Médicale"
    else:
        assert "intelligence artificielle" in top_node.get_content()
        assert top_node.metadata["window"] == "Contexte de la thèse sur l'IA."
        assert top_node.metadata["title"] == "Thèse AI"
    
    # The most important part: verify metadata 'window' exists (Verification cruciale)
    assert "window" in top_node.metadata

def test_vector_service_persistence(storage_path, mock_settings):
    # 1. First session: index nodes
    service1 = VectorService(storage_path=storage_path, collection_name="test_persist_collection")
    doc1 = Document(text="Les énergies renouvelables sont l'avenir.", metadata={"window": "Contexte énergie."})
    service1.index_documents([doc1])
    
    # 2. Second session: load index and query without re-indexing
    # We create a new service instance pointing to the same storage
    service2 = VectorService(storage_path=storage_path, collection_name="test_persist_collection")
    
    # The index property should load it automatically from the vector store
    results = service2.query("énergies", similarity_top_k=1)
    
    assert len(results) > 0
    assert "énergies" in results[0].node.get_content()
    assert results[0].node.metadata.get("window") == "Contexte énergie."

def test_vector_service_reset(storage_path, mock_settings):
    service = VectorService(storage_path=storage_path, collection_name="test_reset")
    doc1 = Document(text="Test content")
    service.index_documents([doc1])
    
    # Verify it exists
    assert len(service.query("test")) > 0
    
    # Reset
    service.reset()
    
    # After reset, it should be empty (but newly initialized)
    # Note: query on an empty index might return empty results
    results = service.query("test")
    assert len(results) == 0
