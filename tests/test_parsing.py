import os
from src.processing.parser import ThesisParser
from llama_index.core import Document
from unittest.mock import patch
from typing import List

def test_thesis_parser_initialization():
    parser = ThesisParser(api_key="fake_key")
    assert parser is not None

def test_parse_pdf_full_mode():
    parser = ThesisParser(api_key="fake_key")
    
    with patch('src.processing.parser.LlamaParse') as mock_llama_parse:
        mock_instance = mock_llama_parse.return_value
        mock_instance.load_data.return_value = [Document(text="Test content", metadata={"page_number": 1})]
        
        # Test without is_dev parameter which was removed
        documents = parser.parse_pdf("dummy.pdf")
        
        mock_llama_parse.assert_called_once()
        _, kwargs = mock_llama_parse.call_args
        # Verify that max_pages is NOT in kwargs
        assert 'max_pages' not in kwargs
        assert kwargs.get('full_parse') is True
        assert len(documents) > 0

def test_parse_pdf_with_metadata():
    parser = ThesisParser(api_key="fake_key")
    extra_meta = {"thesis_id": "123", "author": "John Doe"}
    
    with patch('src.processing.parser.LlamaParse') as mock_llama_parse:
        mock_instance = mock_llama_parse.return_value
        mock_instance.load_data.return_value = [Document(text="Test content")]
        
        documents = parser.parse_pdf("dummy.pdf", extra_metadata=extra_meta)
        
        assert len(documents) == 1
        assert documents[0].metadata["thesis_id"] == "123"
        assert documents[0].metadata["author"] == "John Doe"
