import os
import chromadb
from llama_index.core import StorageContext, VectorStoreIndex, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from typing import Optional, Sequence
from llama_index.core.schema import BaseNode

class VectorService:
    """
    Service for managing vector indexing and retrieval using ChromaDB and LlamaIndex.
    """
    def __init__(self, storage_path: str = "./storage/chroma", collection_name: str = "theses_collection"):
        # Configuration par défaut si non définie (évite d'écraser les mocks de test)
        try:
            from llama_index.core.embeddings import MockEmbedding
            is_mock = isinstance(Settings.embed_model, MockEmbedding)
        except ImportError:
            is_mock = False

        if not is_mock:
            Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
        
        self.storage_path = storage_path
        self.collection_name = collection_name
        
        # Ensure storage path exists
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        
        # Initialize Chroma Client
        self.db = chromadb.PersistentClient(path=self.storage_path)
        
        # Get or create collection
        self.chroma_collection = self.db.get_or_create_collection(self.collection_name)
        
        # Set up ChromaVectorStore
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        
        # Initialize StorageContext
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        
        self._index: Optional[VectorStoreIndex] = None

    @property
    def index(self) -> VectorStoreIndex:
        """Returns the current index, loading it from the vector store if necessary."""
        if self._index is None:
            # Try to load existing index from vector store
            self._index = VectorStoreIndex.from_vector_store(
                self.vector_store,
                storage_context=self.storage_context
            )
        return self._index

    def index_nodes(self, nodes: Sequence[BaseNode]) -> VectorStoreIndex:
        """
        Creates or updates the VectorStoreIndex with the given nodes.
        """
        if self._index is None:
            # If index doesn't exist, create it from nodes
            self._index = VectorStoreIndex(
                nodes, 
                storage_context=self.storage_context
            )
        else:
            # If index exists, add nodes to it
            self._index.insert_nodes(nodes)
            
        return self._index

    def get_all_nodes(self) -> Sequence[BaseNode]:
        """
        Récupère tous les nœuds de la collection Chroma.
        """
        from llama_index.core.schema import TextNode
        chroma_data = self.chroma_collection.get()
        nodes = []
        ids = chroma_data.get('ids', [])
        documents = chroma_data.get('documents', [])
        metadatas = chroma_data.get('metadatas', [])
        
        if ids and documents:
            for i in range(len(ids)):
                nodes.append(TextNode(
                    text=documents[i],
                    id_=ids[i],
                    metadata=metadatas[i] if metadatas and i < len(metadatas) else {}
                ))
        return nodes

    def get_retriever(self, similarity_top_k: int = 5):
        """
        Returns a retriever for the current index.
        """
        return self.index.as_retriever(similarity_top_k=similarity_top_k)

    def query(self, query_text: str, similarity_top_k: int = 5):
        """
        Queries the index and returns the top k results.
        """
        retriever = self.get_retriever(similarity_top_k=similarity_top_k)
        return retriever.retrieve(query_text)
