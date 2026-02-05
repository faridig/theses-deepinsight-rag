import os
import logging
from dotenv import load_dotenv

from llama_index.core import (
    Settings,
    PromptTemplate,
)
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.postprocessor import MetadataReplacementPostProcessor
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.retrievers.fusion_retriever import FUSION_MODES
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.postprocessor.cohere_rerank import CohereRerank
from llama_index.core.query_engine import RetrieverQueryEngine
from typing import List
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import TextNode
from src.indexing.vector_service import VectorService

# Configuration des logs - Silence Technique (Directive Alpha)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Silence sélectif pour les bibliothèques bruyantes
for lib in ["chromadb", "bm25s", "httpx", "urllib3", "llama_index"]:
    logging.getLogger(lib).setLevel(logging.WARNING)
logging.getLogger("opentelemetry").setLevel(logging.CRITICAL)

load_dotenv()

class RAGEngine:
    """
    Moteur RAG pour interroger les thèses avec Sentence Window Retrieval.
    Optimisé pour la précision chirurgicale acronymes/termes techniques.
    """
    def __init__(self, storage_path: str = "./storage/chroma", collection_name: str = "theses_collection"):
        # 1. Configuration des modèles
        self._setup_settings()
        
        # 2. Chargement de l'index
        try:
            self.vector_service = VectorService(storage_path=storage_path, collection_name=collection_name)
            self.index = self.vector_service.index
        except Exception as e:
            logger.error(f"Échec initialisation VectorService: {e}")
            raise RuntimeError(f"Impossible d'initialiser le RAGEngine : {e}")

        # 3. Composants du Pipeline
        self.post_processors = [
            MetadataReplacementPostProcessor(target_metadata_key="window"),
        ]
        
        # 4. Configuration des Retrievers (Hybrid Search)
        self.fusion_retriever = self._setup_retrievers(storage_path)
        
        # 5. Reranker Cohere
        self.reranker = self._setup_reranker()
        
        # 6. Assemblage du Query Engine
        self._setup_query_engine()

    def _setup_settings(self):
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY manquante.")
        Settings.llm = OpenAI(model="gpt-4o-mini")
        Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

    def _setup_retrievers(self, storage_path: str):
        # Top_k=20 exigé pour la précision technique (PBI-006)
        similarity_top_k = 20
        
        vector_retriever = self.index.as_retriever(similarity_top_k=similarity_top_k)
        
        # Récupération des nodes pour BM25
        nodes = list(self.vector_service.storage_context.docstore.docs.values())
        if not nodes:
            nodes = self._recover_nodes_from_chroma(storage_path)
            
        retrievers = [vector_retriever]
        if nodes:
            bm25_retriever = BM25Retriever.from_defaults(
                nodes=nodes,
                similarity_top_k=similarity_top_k
            )
            retrievers.append(bm25_retriever)
            logger.info(f"Recherche Hybride activée ({len(nodes)} nodes).")
        else:
            logger.warning("BM25 désactivé (aucun node trouvé).")

        return QueryFusionRetriever(
            retrievers,
            similarity_top_k=similarity_top_k,
            num_queries=1,
            mode=FUSION_MODES.RECIPROCAL_RANK,
            use_async=True,
            verbose=False
        )

    def _recover_nodes_from_chroma(self, storage_path: str):
        logger.info("Docstore vide, récupération depuis Chroma...")
        nodes = []
        try:
            chroma_data = self.vector_service.chroma_collection.get()
            if chroma_data and chroma_data.get('ids'):
                ids = chroma_data.get('ids', [])
                documents = chroma_data.get('documents', []) or []
                metadatas = chroma_data.get('metadatas', []) or []
                
                for i in range(len(ids)):
                    text = documents[i] if i < len(documents) else ""
                    metadata = metadatas[i] if (metadatas and i < len(metadatas)) else {}
                    nodes.append(TextNode(text=text, id_=ids[i], metadata=metadata or {}))
                
                self.vector_service.storage_context.docstore.add_documents(nodes)
                self.vector_service.storage_context.persist(persist_dir=storage_path)
        except Exception as e:
            logger.error(f"Erreur récupération nodes: {e}")
        return nodes

    def _setup_reranker(self):
        cohere_api_key = os.getenv("COHERE_API_KEY")
        if not cohere_api_key:
            logger.warning("COHERE_API_KEY manquante, Reranking désactivé.")
            return None
        return CohereRerank(
            api_key=cohere_api_key,
            model="rerank-multilingual-v3.0",
            top_n=5
        )

    def _setup_query_engine(self):
        qa_prompt_tmpl_str = (
            "Tu es un assistant de recherche académique expert. "
            "Réponds à la question en utilisant uniquement les extraits de thèses fournis.\n"
            "Cite le titre et l'auteur pour chaque fait mentionné.\n"
            "Sois extrêmement précis sur les termes techniques et acronymes (ex: L2TI).\n"
            "Si l'information n'est pas disponible, réponds : 'Je suis désolé, mais je ne trouve pas d'information à ce sujet dans les thèses analysées.'\n"
            "---------------------\n"
            "CONTEXTE :\n"
            "{context_str}\n"
            "---------------------\n"
            "QUESTION : {query_str}\n"
            "RÉPONSE : "
        )
        qa_prompt_tmpl = PromptTemplate(qa_prompt_tmpl_str)

        all_post_processors = [*self.post_processors]
        if self.reranker:
            all_post_processors.append(self.reranker)
            
        self.query_engine = RetrieverQueryEngine(
            retriever=self.fusion_retriever,
            node_postprocessors=all_post_processors
        )
        
        self.query_engine.update_prompts(
            {"response_synthesizer:text_qa_template": qa_prompt_tmpl}
        )

    def ask(self, question: str):
        if not question or not question.strip():
            return "Veuillez poser une question valide."
        
        try:
            return self.query_engine.query(question)
        except Exception as e:
            logger.error(f"Erreur génération réponse: {e}")
            return f"Une erreur est survenue : {e}"
