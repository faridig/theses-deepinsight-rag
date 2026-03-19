import pytest
from unittest.mock import MagicMock, patch
from src.generation.rag_engine import RAGEngine, CohereThresholdPostprocessor
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.base.response.schema import Response


class TestPBI100_EmptyResponse:
    def test_cohere_threshold_filtering(self):
        """Vérifie que les nœuds sous le seuil sont filtrés."""
        postprocessor = CohereThresholdPostprocessor(threshold=0.6)
        nodes = [
            NodeWithScore(node=TextNode(text="P1"), score=0.7),
            NodeWithScore(node=TextNode(text="P2"), score=0.5),
            NodeWithScore(node=TextNode(text="P3"), score=0.8),
        ]

        filtered = postprocessor._postprocess_nodes(nodes)

        assert len(filtered) == 2
        assert all(n.score >= 0.6 for n in filtered)

    @patch("src.generation.rag_engine.VectorService")
    @patch("llama_index.llms.openai.OpenAI")
    @patch("src.generation.rag_engine.CohereRerank")
    @pytest.mark.asyncio
    async def test_rag_engine_handles_empty_retrieval(
        self, mock_cohere, mock_openai, mock_vector_service
    ):
        """Simule un cas où aucun document ne passe le filtre et vérifie la réponse par défaut."""
        # Setup mocks
        mock_openai.return_value = MagicMock()
        mock_index = MagicMock()
        mock_vector_service.return_value.index = mock_index
        mock_vector_service.return_value.available = True

        engine = RAGEngine(
            storage_path="/tmp/test_chroma", collection_name="test_collection"
        )

        # Mock query engine return with NO source nodes
        mock_query_engine = MagicMock()
        # On simule un retour vide de LlamaIndex (ce qui arrive quand tout est filtré)
        empty_response = Response(response="", source_nodes=[])

        async def mock_aquery(q):
            return empty_response

        mock_query_engine.aquery = mock_aquery
        mock_query_engine.retriever.use_async = True

        with patch.object(
            RAGEngine, "_get_query_engine", return_value=mock_query_engine
        ):
            response = await engine.aask("Une question hors sujet")

        # PBI-100: On s'attend à un message explicite au lieu de vide
        assert "Je ne trouve pas d'information pertinente" in str(response)
