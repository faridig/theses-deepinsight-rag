import os
import logging
import asyncio
import time
from typing import List, Optional, Dict
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
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
from llama_index.core.base.response.schema import Response
from src.indexing.vector_service import VectorService

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paramètres de récupération
RETRIEVAL_TOP_K = 10

# Silence noisy libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("qdrant_client").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("llama_index").setLevel(logging.WARNING)
logging.getLogger("opentelemetry").setLevel(logging.ERROR)
logging.getLogger("bm25s").setLevel(logging.WARNING)

load_dotenv()

class ParallelMultiQueryRetriever(QueryFusionRetriever):
    """
    Version optimisée du QueryFusionRetriever utilisant asyncio.gather
    pour paralléliser les appels aux retrievers (PBI-019).
    """
    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        logger.info(f"Début retrieval multi-requêtes pour: {query_bundle.query_str}")
        start_time = time.time()
        res = await super()._aretrieve(query_bundle)
        end_time = time.time()
        logger.info(f"Fin retrieval multi-requêtes en {end_time - start_time:.2f}s")
        return res

class NodeCleaningProcessor(BaseNodePostprocessor):
    """
    Nettoie les métadonnées techniques pour réduire la consommation de tokens (PBI-012).
    """
    def _postprocess_nodes(self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None) -> List[NodeWithScore]:
        excluded_keys = [
            "_node_content", "relationships", "file_path", "file_size", 
            "creation_date", "last_modified_date", "original_text", 
            "window", "doc_id", "document_id", "ref_doc_id", 
            "_node_type", "file_type", "file_name"
        ]
        
        for node_with_score in nodes:
            node = node_with_score.node
            current_excluded = list(excluded_keys)
            if "titre" not in node.metadata and "file_name" in current_excluded:
                current_excluded.remove("file_name")
            
            node.excluded_llm_metadata_keys = current_excluded
            node.metadata_template = "{key} : {value}"
            
            if isinstance(node, TextNode):
                node.text_template = "THÈSE INFO :\n{metadata_str}\nEXTRAIT :\n{content}\n"
            
            if "page_label" not in node.metadata:
                node.metadata["page_label"] = "N/A"
                
        return nodes

class DiversityPostprocessor(BaseNodePostprocessor):
    """
    Assure la diversité des sources (PBI-015).
    """
    target_top_n: int = 3

    def _postprocess_nodes(self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None) -> List[NodeWithScore]:
        unique_docs = {}
        for node_with_score in nodes:
            doc_id = node_with_score.node.metadata.get("titre") or \
                     node_with_score.node.metadata.get("file_name") or \
                     node_with_score.node.node_id
            
            if doc_id not in unique_docs:
                unique_docs[doc_id] = node_with_score
            
        filtered_nodes = list(unique_docs.values())
        return filtered_nodes[:self.target_top_n]

class RAGEngine:
    """
    Moteur RAG multi-collections pour l'isolation des thèses par domaine (PBI-023).
    """
    def __init__(self, storage_path: str = "./storage/qdrant", collection_name: str = "theses-default"):
        # 1. Configuration globale
        Settings.llm = OpenAI(model="gpt-4o-mini")
        Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
        
        self.storage_path = storage_path
        self.default_collection = collection_name
        self._query_engines: Dict[str, RetrieverQueryEngine] = {}
        self._shared_vector_service: Optional[VectorService] = None
        self.index_ref = None 
        
        # 2. Pipeline de Post-Processing commun
        self.post_processors: List[BaseNodePostprocessor] = [
            MetadataReplacementPostProcessor(target_metadata_key="window"),
            NodeCleaningProcessor(),
        ]
        
        cohere_api_key = os.getenv("COHERE_API_KEY")
        self.reranker = CohereRerank(
            api_key=cohere_api_key,
            model="rerank-multilingual-v3.0",
            top_n=RETRIEVAL_TOP_K
        )

        self.qa_prompt_tmpl = PromptTemplate(
            "Tu es un assistant de recherche académique. "
            "Réponds à la question en utilisant uniquement les extraits de thèses fournis.\n"
            "Cite le titre et l'auteur pour chaque fait mentionné.\n"
            "Si l'information n'est pas disponible dans le contexte fourni, "
            "réponds : 'Je suis désolé, mais je ne trouve pas d'information à ce sujet dans les thèses analysées.'\n"
            "---------------------\n"
            "CONTEXTE :\n"
            "{context_str}\n"
            "---------------------\n"
            "QUESTION : {query_str}\n"
            "RÉPONSE : "
        )

    @property
    def index(self):
        """Compatibilité descendante pour l'accès à l'index."""
        if not self.index_ref:
            # On initialise la collection par défaut si nécessaire
            self._get_query_engine(self.default_collection)
        return self.index_ref

    @property
    def fusion_retriever(self):
        """Compatibilité pour les tests (PBI-010)."""
        return self._get_query_engine(self.default_collection).retriever

    @property
    def retriever(self):
        """Alias pour fusion_retriever."""
        return self.fusion_retriever

    def _get_vector_service(self, collection_name: str) -> VectorService:
        """
        Gère le partage du client Qdrant pour éviter les verrous de fichiers (PBI-023).
        """
        if self._shared_vector_service is None:
            self._shared_vector_service = VectorService(
                storage_path=self.storage_path, 
                collection_name=collection_name
            )
            return self._shared_vector_service
        
        # Si on change de collection mais qu'on garde le même storage_path (client)
        # on crée une nouvelle instance de VectorService partageant le même client
        return VectorService(
            storage_path=self.storage_path,
            collection_name=collection_name,
            client=self._shared_vector_service.client,
            aclient=self._shared_vector_service.aclient
        )

    def _get_query_engine(self, collection_name: str) -> RetrieverQueryEngine:
        """
        Récupère ou crée un QueryEngine pour une collection spécifique (Routing PBI-023).
        """
        if collection_name in self._query_engines:
            return self._query_engines[collection_name]
        
        logger.info(f"Initialisation du QueryEngine pour la collection : {collection_name}")
        
        vector_service = self._get_vector_service(collection_name)
        index = vector_service.index
        self.index_ref = index
        
        # Vector Retriever
        vector_retriever = index.as_retriever(similarity_top_k=RETRIEVAL_TOP_K)
        
        # BM25 Retriever
        try:
            nodes = vector_service.get_all_nodes()
            if nodes:
                bm25_retriever = BM25Retriever.from_defaults(
                    nodes=list(nodes),
                    similarity_top_k=RETRIEVAL_TOP_K
                )
                retrievers = [vector_retriever, bm25_retriever]
            else:
                retrievers = [vector_retriever]
        except Exception as e:
            logger.warning(f"BM25 non disponible pour {collection_name} : {e}")
            retrievers = [vector_retriever]

        # Fusion Retriever
        fusion_retriever = ParallelMultiQueryRetriever(
            retrievers,
            similarity_top_k=RETRIEVAL_TOP_K,
            num_queries=3,
            mode=FUSION_MODES.RECIPROCAL_RANK,
            use_async=vector_service.aclient is not None and not isinstance(vector_service.aclient, (str, type(None))),
            verbose=False
        )
        
        # Hack pour le wrapper AsyncQdrantLocalWrapper (qui n'est pas une instance d'AsyncQdrantClient)
        if hasattr(vector_service.aclient, "_client"):
            fusion_retriever.use_async = False # On force sync pour le wrapper local

        # Query Engine
        all_post_processors = [
            *self.post_processors,
            self.reranker,
            DiversityPostprocessor(target_top_n=3)
        ]
        
        query_engine = RetrieverQueryEngine(
            retriever=fusion_retriever,
            node_postprocessors=all_post_processors
        )
        
        query_engine.update_prompts(
            {"response_synthesizer:text_qa_template": self.qa_prompt_tmpl}
        )
        
        self._query_engines[collection_name] = query_engine
        return query_engine

    def ask(self, question: str, theme: Optional[str] = None):
        """
        Exécute une requête RAG sur un thème spécifique ou par défaut.
        """
        return asyncio.run(self.aask(question, theme))

    async def aask(self, question: str, theme: Optional[str] = None):
        """
        Version asynchrone de ask avec routage de collection.
        """
        if not question or not question.strip():
            return "Veuillez poser une question valide."
        
        collection_name = theme if theme else self.default_collection
        
        try:
            query_engine = self._get_query_engine(collection_name)
            start_time = time.time()
            
            use_async = getattr(query_engine.retriever, "use_async", False)
            if use_async:
                response = await query_engine.aquery(question)
            else:
                response = await asyncio.to_thread(query_engine.query, question)
                
            end_time = time.time()
            logger.info(f"Temps total aquery ({collection_name}): {end_time - start_time:.2f}s")
            
            if isinstance(response, Response) and response.source_nodes:
                sources_text = "\n\nSources :"
                unique_sources = set()
                for node in response.source_nodes:
                    metadata = node.metadata
                    title = metadata.get("titre") or metadata.get("file_name") or "Thèse Inconnue"
                    author = metadata.get("auteur", "Auteur Inconnu")
                    source_id = f"- {title} ({author})"
                    if source_id not in unique_sources:
                        unique_sources.add(source_id)
                        sources_text += f"\n{source_id}"
                
                if response.response:
                    response.response += sources_text
                
            return response
        except Exception as e:
            logger.error(f"Erreur lors de la génération de la réponse pour {collection_name} : {e}")
            return Response(
                response=f"Une erreur est survenue lors du traitement de votre question : {e}", 
                source_nodes=[]
            )
