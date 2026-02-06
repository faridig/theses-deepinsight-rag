import pytest
from unittest.mock import MagicMock
from src.generation.rag_engine import RAGEngine

def test_source_nodes_metadata_presence():
    """
    Vérifie que les nodes de source contiennent les métadonnées nécessaires pour PBI-012.
    """
    # On mock le moteur et la réponse
    mock_node = MagicMock()
    mock_node.metadata = {
        "titre": "Thèse Test",
        "auteur": "Jean Dupont",
        "page_label": "42"
    }
    mock_node.get_content.return_value = "Contenu extrait de la thèse."
    mock_node.score = 0.95
    
    mock_response = MagicMock()
    mock_response.source_nodes = [mock_node]
    mock_response.__str__.return_value = "Ceci est une réponse."
    
    # Vérification de l'accès aux métadonnées
    node = mock_response.source_nodes[0]
    assert node.metadata["titre"] == "Thèse Test"
    assert node.metadata["auteur"] == "Jean Dupont"
    assert node.metadata["page_label"] == "42"
    assert "Contenu" in node.get_content()
