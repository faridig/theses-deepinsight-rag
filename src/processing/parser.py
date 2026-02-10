import os
from typing import List, Optional
import nest_asyncio
from llama_parse import LlamaParse
from llama_index.core import StorageContext, Document, Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.node_parser import SentenceWindowNodeParser
from llama_index.core.schema import BaseNode
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Global Settings for OpenAI
Settings.llm = OpenAI(model="gpt-4o")
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

# Apply nest_asyncio for async operations in environments that need it
nest_asyncio.apply()

class ThesisParser:
    """
    Parser class for converting thesis PDF documents into structured Nodes.
    Uses LlamaParse for high-fidelity PDF parsing and SentenceWindowNodeParser for chunking.
    """
    
    def __init__(self, api_key: Optional[str] = None, window_size: int = 3):
        self.api_key = api_key or os.getenv("LLAMA_CLOUD_API_KEY")
        if not self.api_key:
            # We don't raise error here to allow initialization in tests without API key
            # but we'll check it before calling LlamaParse
            pass
            
        self.node_parser = SentenceWindowNodeParser.from_defaults(
            window_size=window_size,
            window_metadata_key="window",
            original_text_metadata_key="original_text",
        )

    def parse_pdf(self, file_path: str) -> List[BaseNode]:
        """
        Parses a PDF file using LlamaParse and returns a list of Nodes, guaranteeing full-document parsing.
        
        Args:
            file_path: Path to the PDF file.
            
        Returns:
            A list of Nodes.
        """
        if not self.api_key:
            raise ValueError("LLAMA_CLOUD_API_KEY must be provided or set in environment.")
            
        # Initialize LlamaParse for full-document parsing (PBI-011: no arbitrary page limits)
        parser_args = {
            "api_key": self.api_key,
            "result_type": "markdown",
            "verbose": True,
            "use_vendor_multimodal_model": True,
            "vendor_multimodal_model_name": "openai-gpt4o",
        }
        
        parser = LlamaParse(**parser_args)
        
        # Load data from file
        documents = parser.load_data(file_path)
        
        # Transform documents to nodes
        nodes = self._create_nodes(documents)
        return nodes

    def _create_nodes(self, documents: List[Document]) -> List[BaseNode]:
        """
        Transforms documents into Nodes using SentenceWindowNodeParser.
        
        Args:
            documents: List of Document objects.
            
        Returns:
            List of BaseNode objects.
        """
        return self.node_parser.get_nodes_from_documents(documents)

    def save_nodes(self, nodes: List[BaseNode], storage_dir: str = "storage"):
        """
        Saves nodes to the storage directory using StorageContext.
        
        Args:
            nodes: List of nodes to save.
            storage_dir: Directory where to save the nodes.
        """
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
        
        # Create a storage context and add nodes
        storage_context = StorageContext.from_defaults()
        storage_context.docstore.add_documents(nodes)
        
        # Persist the storage context
        storage_context.persist(persist_dir=storage_dir)
        print(f"Nodes saved successfully to {storage_dir}")
