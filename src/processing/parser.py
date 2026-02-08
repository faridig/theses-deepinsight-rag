import os
from typing import List, Optional, Dict
import nest_asyncio
from llama_parse import LlamaParse
from llama_index.core import Document
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Apply nest_asyncio for async operations in environments that need it
nest_asyncio.apply()

class ThesisParser:
    """
    Parser class for converting thesis PDF documents into LlamaIndex Document objects.
    Uses LlamaParse for high-fidelity PDF parsing.
    The node creation logic is now delegated to the VectorService.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("LLAMA_CLOUD_API_KEY")
        if not self.api_key:
            # We don't raise error here to allow initialization in tests without API key
            # but we'll check it before calling LlamaParse
            pass

    def parse_pdf(self, file_path: str, extra_metadata: Optional[Dict] = None) -> List[Document]:
        """
        Parses a PDF file using LlamaParse and returns a list of Document objects.
        
        Args:
            file_path: Path to the PDF file.
            extra_metadata: Optional metadata to add to the documents.
            
        Returns:
            A list of Document objects.
        """
        if not self.api_key:
            raise ValueError("LLAMA_CLOUD_API_KEY must be provided or set in environment.")
            
        parser_args = {
            "api_key": self.api_key,
            "result_type": "markdown",
            "verbose": True,
            "language": "fr",
            "full_parse": True,
        }
        
        parser = LlamaParse(**parser_args)
        
        documents = parser.load_data(file_path)
        
        if extra_metadata:
            for doc in documents:
                doc.metadata.update(extra_metadata)
                
        return documents

