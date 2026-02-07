from llama_index.core.schema import BaseNode, Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.retrievers import ParentDocumentRetriever
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.ingestion import IngestionPipeline

class VectorService:
    """
    Service for managing vector indexing and retrieval using ChromaDB and LlamaIndex.
    Implements a Parent-Child retrieval strategy for robust search on long documents.
    """
    def __init__(self, storage_path: str = "./storage/chroma", collection_name: str = "theses_collection"):
        try:
            from llama_index.core.embeddings import MockEmbedding
            is_mock = isinstance(Settings.embed_model, MockEmbedding)
        except ImportError:
            is_mock = False

        if not is_mock:
            Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
        
        self.storage_path = storage_path
        self.collection_name = collection_name
        self.child_collection_name = f"{collection_name}_children"
        
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        
        self.db = chromadb.PersistentClient(path=self.storage_path)
        
        # Collection for parent document chunks
        self.chroma_collection = self.db.get_or_create_collection(self.collection_name)
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        
        # Collection for child document chunks
        self.child_chroma_collection = self.db.get_or_create_collection(self.child_collection_name)
        self.child_vector_store = ChromaVectorStore(chroma_collection=self.child_chroma_collection)
        
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
        Indexes documents using a Parent-Child strategy.
        - Large chunks (parents) are stored in the docstore.
        - Small chunks (children) are stored in the vector store for retrieval.
        """
        # Ingest documents into the docstore
        for doc in documents:
            self.docstore.add_documents([doc], allow_update=True)
            
        # Create child nodes from parent documents
        child_parser = SentenceSplitter(chunk_size=512)
        
        pipeline = IngestionPipeline(
            transformations=[child_parser],
            vector_store=self.child_vector_store,
            docstore=self.docstore
        )
        
        # This will run the pipeline and store child nodes in the child_vector_store
        pipeline.run(documents=documents, show_progress=True)
        
        # Persist the docstore
        self.storage_context.persist(persist_dir=self.storage_path)

    def get_retriever(self, similarity_top_k: int = 10):
        """
        Returns a ParentDocumentRetriever for robust retrieval on long documents.
        """
        return ParentDocumentRetriever(
            vector_store=self.child_vector_store,
            docstore=self.docstore,
            similarity_top_k=similarity_top_k
        )

    def query(self, query_text: str, similarity_top_k: int = 10):
        """
        Queries the index and returns the top k results.
        """
        retriever = self.get_retriever(similarity_top_k=similarity_top_k)
        return retriever.retrieve(query_text)

    def reset_collection(self):
        """
        Deletes and recreates the ChromaDB collections and clears LlamaIndex storage.
        """
        print(f"ATTENTION: Deleting collections '{self.collection_name}', '{self.child_collection_name}' and storage files in {self.storage_path}...")
        
        llama_index_files = ["docstore.json", "index_store.json", "graph_store.json", "image_store.json"]
        for filename in llama_index_files:
            file_path = os.path.join(self.storage_path, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Deleted {filename}")
        
        try:
            self.db.delete_collection(name=self.collection_name)
            self.db.delete_collection(name=self.child_collection_name)
        except Exception as e:
            print(f"Could not delete collection, it might not exist: {e}")
        
        self.chroma_collection = self.db.get_or_create_collection(self.collection_name)
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        
        self.child_chroma_collection = self.db.get_or_create_collection(self.child_collection_name)
        self.child_vector_store = ChromaVectorStore(chroma_collection=self.child_chroma_collection)

        self.docstore = SimpleDocumentStore()
        
        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store,
            docstore=self.docstore
        )
        self._index = None
        
        print(f"Collections and storage fully reset.")

