import os
from typing import List, Optional
import nest_asyncio
import torch
from llama_parse import LlamaParse
from llama_index.core import StorageContext, Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.node_parser import SentenceWindowNodeParser
from llama_index.core.schema import BaseNode
from llama_index.readers.docling import DoclingReader
from llama_index.node_parser.docling import DoclingNodeParser
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice
from docling.datamodel.pipeline_options import PdfPipelineOptions
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
    Supports LlamaParse and Docling (local GPU).
    """
    
    def __init__(self, mode: str = "llama-parse", api_key: Optional[str] = None, window_size: int = 3):
        self.mode = mode.lower()
        self.api_key = api_key or os.getenv("LLAMA_CLOUD_API_KEY")
        
        # Configure chunking
        if self.mode == "docling":
            self.docling_node_parser = DoclingNodeParser()
        else:
            self.node_parser = SentenceWindowNodeParser.from_defaults(
                window_size=window_size,
                window_metadata_key="window",
                original_text_metadata_key="original_text",
            )

    def parse_pdf(self, file_path: str, is_dev: bool = False) -> List[BaseNode]:
        """
        Parses a PDF file using the selected mode and returns a list of Nodes.
        
        Args:
            file_path: Path to the PDF file.
            is_dev: If True, limit parsing for development (only for LlamaParse).
            
        Returns:
            A list of Nodes.
        """
        if self.mode == "docling":
            return self._parse_with_docling(file_path, is_dev=is_dev)
        else:
            return self._parse_with_llama_parse(file_path, is_dev=is_dev)

    def _parse_with_llama_parse(self, file_path: str, is_dev: bool = False) -> List[BaseNode]:
        if not self.api_key:
            raise ValueError("LLAMA_CLOUD_API_KEY must be provided or set in environment.")
            
        parser_args = {
            "api_key": self.api_key,
            "result_type": "markdown",
            "verbose": True,
            "use_vendor_multimodal_model": True,
            "vendor_multimodal_model_name": "openai-gpt4o",
        }
        
        if is_dev:
            # PBI-011: is_dev usually means we want to limit pages for speed/cost
            # llama-parse supports target_pages or similar
            # For now, we'll keep it simple as it was before
            pass
            
        parser = LlamaParse(**parser_args)
        documents = parser.load_data(file_path)
        return self.node_parser.get_nodes_from_documents(documents)

    def _parse_with_docling(self, file_path: str, is_dev: bool = False) -> List[BaseNode]:
        """
        Parses a PDF file using Docling with CUDA acceleration.
        """
        # Configure Docling with CUDA if available
        device = AcceleratorDevice.CUDA if torch.cuda.is_available() else AcceleratorDevice.CPU
        print(f"Using Docling with device: {device}")
        
        accelerator_options = AcceleratorOptions(device=device)
        pipeline_options = PdfPipelineOptions()
        pipeline_options.accelerator_options = accelerator_options
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        
        reader = DoclingReader(
            converter=converter,
            export_type=DoclingReader.ExportType.JSON
        )
        
        # Load data
        documents = reader.load_data(file_path)
        
        # Add file_name to metadata for each document
        file_name = os.path.basename(file_path)
        for doc in documents:
            doc.metadata["file_name"] = file_name
        
        # Transform to nodes
        nodes = self.docling_node_parser.get_nodes_from_documents(documents)
        
        # Ensure page_label is populated if missing but page_no is present
        # and flatten/clean metadata for Chroma compatibility
        for node in nodes:
            if "page_label" not in node.metadata and "page_no" in node.metadata:
                node.metadata["page_label"] = str(node.metadata["page_no"])
            # Ensure file_name is in node metadata too
            if "file_name" not in node.metadata:
                node.metadata["file_name"] = file_name
            
            # Clean up metadata for Chroma (must be flat and simple types)
            # We convert lists/dicts to strings or remove them
            keys_to_clean = []
            for k, v in node.metadata.items():
                if isinstance(v, (list, dict)):
                    keys_to_clean.append(k)
            
            for k in keys_to_clean:
                # For docling specifically, doc_items is a large list of refs, we can drop it
                # For headings, we can join them
                if k == "headings" and isinstance(node.metadata[k], list):
                    node.metadata[k] = " > ".join([str(h) for h in node.metadata[k]])
                elif k == "doc_items":
                    # Dropping doc_items as it's too complex and large for Chroma metadata
                    del node.metadata[k]
                else:
                    # Convert others to string
                    node.metadata[k] = str(node.metadata[k])

        return nodes

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
