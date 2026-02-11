import pytest
from src.indexing.vector_service import VectorService
from src.generation.rag_engine import RAGEngine
from llama_index.core.schema import TextNode
from llama_index.core import Settings
from llama_index.core.embeddings import MockEmbedding

@pytest.fixture
def mock_settings():
    Settings.embed_model = MockEmbedding(embed_dim=1536)
    yield

@pytest.mark.asyncio
async def test_multi_collection_isolation(tmp_path, mock_settings):
    storage_path = str(tmp_path / "qdrant_multi")
    
    # 1. Ingestion pour le thème IA
    vs_ia = VectorService(storage_path=storage_path, collection_name="theses-ia")
    await vs_ia.create_collection_if_not_exists("theses-ia")
    nodes_ia = [
        TextNode(text="L'intelligence artificielle est fascinante.", metadata={"titre": "Thèse IA", "theme": "ia"})
    ]
    vs_ia.index_nodes(nodes_ia)
    vs_ia.close()
    
    # 2. Ingestion pour le thème Agriculture
    vs_agri = VectorService(storage_path=storage_path, collection_name="theses-agri")
    await vs_agri.create_collection_if_not_exists("theses-agri")
    nodes_agri = [
        TextNode(text="L'agriculture biologique préserve les sols.", metadata={"titre": "Thèse Agri", "theme": "agriculture"})
    ]
    vs_agri.index_nodes(nodes_agri)
    vs_agri.close()
    
    # 3. Test de recherche isolée via RAGEngine
    engine = RAGEngine(storage_path=storage_path, collection_name="theses-ia")
    
    try:
        # Recherche sur l'IA (doit trouver le node IA)
        response_ia = await engine.aask("Quelle est la fascination ?", theme="theses-ia")
        # On vérifie que la source IA est présente (indépendant de la réponse du LLM)
        source_titles = [node.metadata.get("titre") for node in response_ia.source_nodes]
        assert "Thèse IA" in source_titles
        
        # Recherche sur l'Agriculture (doit trouver le node Agri)
        response_agri = await engine.aask("Que préserve l'agriculture ?", theme="theses-agri")
        source_titles_agri = [node.metadata.get("titre") for node in response_agri.source_nodes]
        assert "Thèse Agri" in source_titles_agri
        
        # Vérification croisée : IA ne doit pas voir Agri
        response_cross = await engine.aask("agriculture", theme="theses-ia")
        source_titles_cross = [node.metadata.get("titre") for node in response_cross.source_nodes]
        assert "Thèse Agri" not in source_titles_cross
    finally:
        # On ferme les services cachés dans l'engine
        for eng in engine._query_engines.values():
            # RetrieverQueryEngine doesn't have close, but its retriever might
            pass
        # VectorService inside engine should be closed if possible
        # Actually our refactored RAGEngine creates them on the fly
        pass
