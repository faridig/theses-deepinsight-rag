import os
from typing import List, Optional, Any
import nest_asyncio
import torch
from llama_parse import LlamaParse
from llama_index.core import StorageContext, Document, SimpleDirectoryReader
from llama_index.core.node_parser import SentenceWindowNodeParser
from llama_index.core.schema import BaseNode
from llama_index.readers.docling import DoclingReader
from llama_index.node_parser.docling import DoclingNodeParser
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice
from docling.datamodel.pipeline_options import PdfPipelineOptions
from src.config import setup_settings

# Apply nest_asyncio for async operations in environments that need it
nest_asyncio.apply()

# Initialisation des paramètres globaux
setup_settings()

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

    def parse_pdf(self, file_path: str, is_dev: bool = False, fs: Optional[Any] = None) -> List[BaseNode]:
        """
        Parses a PDF file using the selected mode and returns a list of Nodes.
        
        Args:
            file_path: Path to the PDF file (local or remote).
            is_dev: If True, limit parsing for development.
            fs: Optional fsspec-compatible filesystem.
            
        Returns:
            A list of Nodes.
        """
        if fs:
            return self._parse_with_fs(file_path, fs, is_dev=is_dev)
            
        if self.mode == "docling":
            return self._parse_with_docling(file_path, is_dev=is_dev)
        else:
            return self._parse_with_llama_parse(file_path, is_dev=is_dev)

    def _parse_with_fs(self, file_path: str, fs: Any, is_dev: bool = False) -> List[BaseNode]:
        """
        Parses a file from a remote filesystem using SimpleDirectoryReader.
        """
        if self.mode == "docling":
            # Setup DoclingReader for SimpleDirectoryReader
            device = AcceleratorDevice.CUDA if torch.cuda.is_available() else AcceleratorDevice.CPU
            accelerator_options = AcceleratorOptions(device=device)
            pipeline_options = PdfPipelineOptions()
            pipeline_options.accelerator_options = accelerator_options
            pipeline_options.do_ocr = True
            
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )
            
            reader_instance = DoclingReader(
                converter=converter,
                export_type=DoclingReader.ExportType.JSON
            )
            
            file_extractor = {".pdf": reader_instance}
        else:
            # LlamaParse doesn't easily plug into SimpleDirectoryReader with fs for single files
            # without downloading it. For simplicity, if it's LlamaParse + fs, we download to temp.
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                with fs.open(file_path, "rb") as f:
                    tmp.write(f.read())
                tmp_path = tmp.name
            
            try:
                nodes = self._parse_with_llama_parse(tmp_path, is_dev=is_dev)
                # Cleanup
                os.unlink(tmp_path)
                return nodes
            except Exception as e:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise e

        # Using SimpleDirectoryReader for Docling
        loader = SimpleDirectoryReader(
            input_files=[file_path],
            fs=fs,
            file_extractor=file_extractor if self.mode == "docling" else None
        )
        documents = loader.load_data()
        
        # Manually add file_name if missing
        file_name = os.path.basename(file_path)
        for doc in documents:
            if "file_name" not in doc.metadata:
                doc.metadata["file_name"] = file_name
        
        return self._create_nodes(documents)

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
        return self._create_nodes(documents)

    def _create_nodes(self, documents: List[Document]) -> List[BaseNode]:
        """
        Transforms documents into Nodes using the appropriate parser for the current mode.
        """
        if self.mode == "docling":
            nodes = self.docling_node_parser.get_nodes_from_documents(documents)
            
            # Post-process nodes for Docling mode (metadata cleaning for Chroma)
            for node in nodes:
                if "page_label" not in node.metadata and "page_no" in node.metadata:
                    node.metadata["page_label"] = str(node.metadata["page_no"])
                
                # Ensure file_name is propagated if available in documents
                # Normally llama-index does this, but we keep it for safety
                
                # Clean up metadata for Chroma (must be flat and simple types)
                keys_to_clean = []
                for k, v in node.metadata.items():
                    if isinstance(v, (list, dict)):
                        keys_to_clean.append(k)
                
                for k in keys_to_clean:
                    if k == "headings" and isinstance(node.metadata[k], list):
                        node.metadata[k] = " > ".join([str(h) for h in node.metadata[k]])
                    elif k == "doc_items":
                        del node.metadata[k]
                    else:
                        node.metadata[k] = str(node.metadata[k])
            return nodes
        else:
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
        return self._create_nodes(documents)

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
