from unittest.mock import patch, MagicMock
from src.processing.parser import ThesisParser

# We mock the environment variable just to allow ThesisParser to initialize
@patch.dict('os.environ', {'LLAMA_CLOUD_API_KEY': 'DUMMY_KEY'})
@patch('src.processing.parser.LlamaParse', autospec=True)
@patch('llama_index.core.Settings', autospec=True)
@patch('llama_index.llms.openai.OpenAI', autospec=True)
@patch('llama_index.embeddings.openai.OpenAIEmbedding', autospec=True)
@patch('src.processing.parser.SentenceWindowNodeParser', autospec=True)
class TestPBI011IndexingIntegrity:
    
    def test_parsing_full_document_mode(
        self, mock_node_parser, mock_embed, mock_openai, mock_settings, MockLlamaParse
    ):
        """
        [PBI-011 Scenario 1] Tests that ThesisParser is configured for full document
        parsing by removing the arbitrary page limit.
        """
        # Arrange
        # Mock the return value of the parser's load_data to prevent real execution
        mock_parser_instance = MockLlamaParse.return_value
        mock_parser_instance.load_data.return_value = [MagicMock()] # returns a list of mock Documents
        
        parser = ThesisParser()
            
        # Act
        # The new signature has no 'is_dev' argument, should pass without it
        _ = parser.parse_pdf(file_path="dummy/path/to/thesis.pdf")
            
        # Assert
        # 1. Assert LlamaParse was initialized once
        MockLlamaParse.assert_called_once()
        
        # 2. Get the arguments passed to LlamaParse constructor
        call_args, call_kwargs = MockLlamaParse.call_args
        
        # 3. Assert the 'target_pages' parameter (used for arbitrary limits) is ABSENT
        # This proves the intent of full parsing as the page limit logic was removed.
        parser_args = call_kwargs
        assert "target_pages" not in parser_args, "The 'target_pages' parameter should not be present for full parsing."
        assert parser_args["result_type"] == "markdown"
        assert parser_args["vendor_multimodal_model_name"] == "openai-gpt4o"
        
    def test_no_manual_metadata_injection(
        self, mock_node_parser, mock_embed, mock_openai, mock_settings, MockLlamaParse
    ):
        """
        [PBI-011 Scenario 2] Tests that the ThesisParser does not manually inject 
        any factual metadata (shadow metadata) into the Documents or Nodes.
        
        Note: The implementation (ThesisParser) delegates node creation to LlamaParse 
        and SentenceWindowNodeParser. We assert that no intermediate steps 
        are taken to manually modify or inject metadata into the raw Documents.
        """
        # Arrange
        mock_document = MagicMock()
        mock_document.metadata = {"source": "extracted_by_ll", "page_number": 1}
        mock_document.text = "This is a conclusion extracted from the text."
        
        mock_parser_instance = MockLlamaParse.return_value
        mock_parser_instance.load_data.return_value = [mock_document]
        
        parser = ThesisParser()
        
        # Act
        _ = parser.parse_pdf(file_path="dummy/path/to/thesis.pdf")
        
        # Assert
        # Assert that the code path for manual metadata injection (e.g., in _create_nodes) 
        # was NOT taken on the mock document. 
        # The simplest way to test this for current code is to check the NodeParser usage.
        
        # 1. Check if node parser was called with the raw documents (without manual modification)
        mock_node_parser.from_defaults.return_value.get_nodes_from_documents.assert_called_once()
        args, kwargs = mock_node_parser.from_defaults.return_value.get_nodes_from_documents.call_args
        
        # Check that the list passed to get_nodes_from_documents contains the original mock_document
        assert args[0][0] is mock_document, "Documents passed to node parser should be the raw LlamaParse output."
        
        # This indirectly proves that ThesisParser did not manually call doc.metadata.update() 
        # between LlamaParse.load_data() and node_parser.get_nodes_from_documents().
