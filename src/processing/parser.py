import os
from typing import List, Optional, Dict
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

    def parse_pdf(self, file_path: str, is_dev: bool = True, extra_metadata: Optional[Dict] = None) -> List[BaseNode]:
        """
        Parses a PDF file using LlamaParse and returns a list of Nodes.
        
        Args:
            file_path: Path to the PDF file.
            is_dev: If True, limits parsing to the first 10 pages to save quota.
            extra_metadata: Optional metadata to add to the documents before node creation.
            
        Returns:
            A list of Nodes.
        """
        if not self.api_key:
            raise ValueError("LLAMA_CLOUD_API_KEY must be provided or set in environment.")
            
        # Initialize LlamaParse
        # Optimisation : On utilise le mode 'balanced' ou standard pour plus de stabilité
        parser_args = {
            "api_key": self.api_key,
            "result_type": "markdown",
            "verbose": True,
            "language": "fr", # On précise la langue pour CA-1
        }
        
        if is_dev:
            # On passe à 20 pages pour assurer d'avoir l'introduction et les objectifs (CA-1)
            parser_args["target_pages"] = "0-19"
            
        parser = LlamaParse(**parser_args)
        
        # Load data from file
        documents = parser.load_data(file_path)
        
        # Transform documents to nodes
        nodes = self._create_nodes(documents, extra_metadata=extra_metadata)
        return nodes

    def _create_nodes(self, documents: List[Document], extra_metadata: Optional[Dict] = None) -> List[BaseNode]:
        """
        Transforms documents into Nodes using SentenceWindowNodeParser.
        """
        if extra_metadata:
            for doc in documents:
                doc.metadata.update(extra_metadata)
                # On injecte uniquement l'ID et le Titre dans le texte pour aider le BM25 (CA-1)
                # Sans polluer avec des résumés pré-rédigés
                header = f"[THÈSE ID: {extra_metadata.get('id')}] [TITRE: {extra_metadata.get('titre')}]\n"
                doc.set_content(header + doc.get_content())
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
