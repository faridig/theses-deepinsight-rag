import os
from src.processing.parser import ThesisParser
from llama_index.core.schema import TextNode, BaseNode
from llama_index.core import Document
from unittest.mock import patch
from typing import List

def test_thesis_parser_initialization():
    parser = ThesisParser(api_key="fake_key")
    assert parser is not None

def test_sentence_window_node_parser_metadata():
    # Ce test vérifiera que les nodes produits par le SentenceWindowNodeParser
    # contiennent bien la clé 'window' dans les métadonnées.
    parser = ThesisParser(api_key="fake_key")
    text = "Ceci est la première phrase. Ceci est la deuxième phrase. Ceci est la troisième phrase. Ceci est la quatrième phrase. Ceci est la cinquième phrase."
    doc = Document(text=text)
    
    nodes = parser._create_nodes([doc])
    
    assert len(nodes) > 0
    # Vérifier si au moins un node a la métadonnée 'window'
    assert 'window' in nodes[0].metadata

def test_parse_pdf_dev_mode():
    parser = ThesisParser(api_key="fake_key")
    
    with patch('src.processing.parser.LlamaParse') as mock_llama_parse:
        mock_instance = mock_llama_parse.return_value
        mock_instance.load_data.return_value = [Document(text="Test content", metadata={"page_number": 1})]
        
        nodes = parser.parse_pdf("dummy.pdf", is_dev=True)
        
        # Check if LlamaParse was called with target_pages="0-9"
        mock_llama_parse.assert_called_once()
        _, kwargs = mock_llama_parse.call_args
        assert kwargs['target_pages'] == "0-9"
        assert len(nodes) > 0

def test_save_nodes(tmp_path):
    parser = ThesisParser(api_key="fake_key")
    # Cast explicitly to List[BaseNode] to satisfy type checker if needed
    nodes: List[BaseNode] = [TextNode(text="Test node", metadata={"window": "context"})]
    
    storage_dir = tmp_path / "storage"
    parser.save_nodes(nodes, storage_dir=str(storage_dir))
    
    assert os.path.exists(storage_dir)
    # LlamaIndex persists multiple files, check for one of them
    assert any(os.path.exists(storage_dir / f) for f in ["docstore.json", "default__vector_store.json"])
