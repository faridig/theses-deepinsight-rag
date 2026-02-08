import logging
import os
import shutil
from typing import List, Optional
import chromadb
from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import BaseNode, Document
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.storage_context import StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VectorService:
    """
    Service for managing vector indexing and retrieval using ChromaDB and LlamaIndex.
    Implements a robust retrieval strategy for long documents.
    """
    def __init__(self, storage_path: str = "./storage/chroma", collection_name: str = "theses_collection"):
        """
        Initializes the VectorService.

        Args:
            storage_path (str): The path to the storage directory for ChromaDB and LlamaIndex data.
            collection_name (str): The name of the ChromaDB collection.
        """
        self.storage_path = storage_path
        self.collection_name = collection_name
        
        # Ensure the storage directory exists
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        
        # Initialize ChromaDB
        self.db = chromadb.PersistentClient(path=self.storage_path)
        self.chroma_collection = self.db.get_or_create_collection(self.collection_name)
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        
        # Initialize Docstore
        docstore_path = os.path.join(self.storage_path, "docstore.json")
        if os.path.exists(docstore_path):
            self.docstore = SimpleDocumentStore.from_persist_path(docstore_path)
        else:
            self.docstore = SimpleDocumentStore()
            
        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store,
            docstore=self.docstore
        )
        
        self._index: Optional[VectorStoreIndex] = None

    @property
    def index(self) -> VectorStoreIndex:
        """Returns the current index, loading it from the vector store if necessary."""
        if self._index is None:
            self._index = VectorStoreIndex.from_vector_store(
                self.vector_store,
                storage_context=self.storage_context
            )
        return self._index

    def index_documents(self, documents: List[Document]):
        """
        Indexes documents by parsing them into nodes and storing them in both
        the vector store and the docstore for hybrid search.
        
        Args:
            documents (List[Document]): The documents to index.
        """
        logger.info(f"Indexing {len(documents)} documents...")
        
        # Use a consistent splitter (PBI-010/011)
        splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=200)
        nodes = splitter.get_nodes_from_documents(documents)
        
        logger.info(f"Created {len(nodes)} nodes from {len(documents)} documents.")
        
        # Add nodes to docstore for BM25 (PBI-010)
        self.storage_context.docstore.add_documents(nodes)
        
        # Create/Update index from nodes
        self._index = VectorStoreIndex(
            nodes,
            storage_context=self.storage_context,
            show_progress=True
        )
        
        # Persist everything
        self.storage_context.persist(persist_dir=self.storage_path)
        logger.info(f"Indexing completed. Docstore size: {len(self.docstore.docs)}")

    def reset(self):
        """
        Completely resets the service by clearing the collection and the docstore.
        (PBI-011 Scenario 0)
        """
        logger.warning(f"Resetting vector storage for collection: {self.collection_name}")
        
        # 1. Clear in-memory state
        self._index = None
        
        # 2. Delete and recreate the collection
        try:
            self.db.delete_collection(self.collection_name)
            logger.info(f"Collection {self.collection_name} deleted.")
        except Exception as e:
            logger.warning(f"Could not delete collection: {e}")
            
        self.chroma_collection = self.db.get_or_create_collection(self.collection_name)
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        
        # 3. Clear the docstore
        self.docstore = SimpleDocumentStore()
        
        # 4. Re-initialize storage context
        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store,
            docstore=self.docstore
        )
        
        # 5. Persist the empty state to disk to overwrite old data
        if os.path.exists(self.storage_path):
            self.storage_context.persist(persist_dir=self.storage_path)
            
        logger.info("Vector service has been reset and re-initialized.")

    def get_retriever(self, similarity_top_k: int = 10):
        """
        Returns a retriever for the index.
        """
        return self.index.as_retriever(similarity_top_k=similarity_top_k)

    def query(self, query_text: str, similarity_top_k: int = 10):
        """
        Queries the index and returns the top k results.
        """
        retriever = self.get_retriever(similarity_top_k=similarity_top_k)
        return retriever.retrieve(query_text)
