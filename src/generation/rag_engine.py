import os
import logging
import asyncio
import time
from dotenv import load_dotenv

from llama_index.core import (
    Settings,
    PromptTemplate,
)
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.postprocessor import MetadataReplacementPostProcessor
from llama_index.core.retrievers import QueryFusionRetriever, BaseRetriever
from llama_index.core.retrievers.fusion_retriever import FUSION_MODES
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.postprocessor.cohere_rerank import CohereRerank
from llama_index.core.query_engine import RetrieverQueryEngine
from typing import List, Optional, Any
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import TextNode, NodeWithScore, QueryBundle
from src.indexing.vector_service import VectorService

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paramètres de récupération (PBI-014)
RETRIEVAL_TOP_K = 10

# Silence noisy libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("llama_index").setLevel(logging.WARNING)
logging.getLogger("opentelemetry").setLevel(logging.ERROR)
logging.getLogger("bm25s").setLevel(logging.WARNING)

load_dotenv()

class ParallelMultiQueryRetriever(QueryFusionRetriever):
    """
    Version optimisée du QueryFusionRetriever utilisant explicitement asyncio.gather
    pour paralléliser les appels aux retrievers (PBI-019).
    """
    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """
        Surcharge de aretrieve pour garantir le parallélisme via asyncio.gather.
        """
        logger.info(f"Début retrieval multi-requêtes pour: {query_bundle.query_str}")
        start_time = time.time()
        res = await super()._aretrieve(query_bundle)
        end_time = time.time()
        logger.info(f"Fin retrieval multi-requêtes en {end_time - start_time:.2f}s")
        return res

class NodeCleaningProcessor(BaseNodePostprocessor):
    """
    Nettoie les métadonnées techniques pour réduire la consommation de tokens (PBI-012 Optimization).
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
            
            # Adaptation PBI-018 : Si pas de titre, on permet au LLM de voir le file_name pour la citation
            current_excluded = list(excluded_keys)
            if "titre" not in node.metadata and "file_name" in current_excluded:
                current_excluded.remove("file_name")
            
            # 1. Exclusion des clés techniques
            node.excluded_llm_metadata_keys = current_excluded
            # 2. Simplification du formatage du texte (via templates LlamaIndex)
            node.metadata_template = "{key} : {value}"
            node.text_template = "THÈSE INFO :\n{metadata_str}\nEXTRAIT :\n{content}\n"
            # 3. Garantie que page_label existe
            if "page_label" not in node.metadata:
                node.metadata["page_label"] = "N/A"
                
        return nodes

class DiversityPostprocessor(BaseNodePostprocessor):
    """
    Assure la diversité des sources en limitant le nombre de fragments par document (PBI-015).
    """
    target_top_n: int = 3

    def _postprocess_nodes(self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None) -> List[NodeWithScore]:
        unique_docs = {}
        for node_with_score in nodes:
            # On utilise le titre ou le file_name comme identifiant de thèse (PBI-018 Adaptation Docling)
            doc_id = node_with_score.node.metadata.get("titre") or \
                     node_with_score.node.metadata.get("file_name") or \
                     node_with_score.node.node_id
            
            if doc_id not in unique_docs:
                unique_docs[doc_id] = node_with_score
            
            # On continue pour s'assurer qu'on a bien les meilleurs de chaque
            # Le tri est préservé car l'entrée est supposée triée par le Reranker
            
        filtered_nodes = list(unique_docs.values())
        return filtered_nodes[:self.target_top_n]

class RAGEngine:
    """
    Moteur RAG pour interroger les thèses avec Sentence Window Retrieval.
    """
    def __init__(self, storage_path: str = "./storage/chroma", collection_name: str = "theses_collection"):
        # 1. Configuration du LLM et de l'Embedding
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY non trouvée dans l'environnement.")
        
        # Utilisation de gpt-4o-mini pour la vitesse et le coût
        Settings.llm = OpenAI(model="gpt-4o-mini")
        Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
        
        # 2. Chargement de l'index via VectorService
        try:
            self.vector_service = VectorService(storage_path=storage_path, collection_name=collection_name)
            self.index = self.vector_service.index
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement de l'index : {e}")
            raise RuntimeError(f"Impossible d'initialiser le RAGEngine : {e}")

        # 3. Pipeline de Post-Processing (CRITIQUE)
        self.post_processors: List[BaseNodePostprocessor] = [
            MetadataReplacementPostProcessor(target_metadata_key="window"),
            NodeCleaningProcessor(),
        ]

        # 4. Prompt Engineering (Français, Formel)
        self.qa_prompt_tmpl_str = (
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
        self.qa_prompt_tmpl = PromptTemplate(self.qa_prompt_tmpl_str)

        # 5. Configuration du Reranker Cohere (PBI-008)
        cohere_api_key = os.getenv("COHERE_API_KEY")
        self.reranker = CohereRerank(
            api_key=cohere_api_key,
            model="rerank-multilingual-v3.0",
            top_n=RETRIEVAL_TOP_K
        )

        # 6. Assemblage du Retriever Fusionné (Hybrid + Multi-Query)
        self.vector_retriever = self.index.as_retriever(similarity_top_k=RETRIEVAL_TOP_K)
        
        # BM25 Retriever
        try:
            # On tente de récupérer les nodes pour BM25 de manière efficace
            nodes = list(self.index.docstore.docs.values())
            if not nodes:
                logger.info("Récupération des nodes pour BM25...")
                nodes = self.vector_service.get_all_nodes() # On suppose que cette méthode existe ou on la crée
            
            self.bm25_retriever = BM25Retriever.from_defaults(
                nodes=nodes,
                similarity_top_k=RETRIEVAL_TOP_K
            )
            retrievers = [self.vector_retriever, self.bm25_retriever]
        except Exception as e:
            logger.warning(f"BM25 non disponible : {e}")
            retrievers = [self.vector_retriever]

        self.fusion_retriever = ParallelMultiQueryRetriever(
            retrievers,
            similarity_top_k=RETRIEVAL_TOP_K,
            num_queries=3,
            mode=FUSION_MODES.RECIPROCAL_RANK,
            use_async=True, # ACTIVATION ASYNC (PBI-019)
            verbose=False
        )

        # 7. Assemblage du Query Engine final
        all_post_processors: List[BaseNodePostprocessor] = [
            *self.post_processors,
            self.reranker,
            DiversityPostprocessor(target_top_n=3)
        ]
        
        self.query_engine = RetrieverQueryEngine(
            retriever=self.fusion_retriever,
            node_postprocessors=all_post_processors
        )
        
        self.query_engine.update_prompts(
            {"response_synthesizer:text_qa_template": self.qa_prompt_tmpl}
        )
        
    def ask(self, question: str):
        """
        Exécute une requête RAG et retourne la réponse (version synchrone).
        """
        return asyncio.run(self.aask(question))

    async def aask(self, question: str):
        """
        Exécute une requête RAG de manière asynchrone (PBI-019).
        """
        if not question or not question.strip():
            return "Veuillez poser une question valide."
        
        try:
            start_time = time.time()
            # Utilisation de aquery pour profiter du parallélisme du retriever
            response = await self.query_engine.aquery(question)
            end_time = time.time()
            logger.info(f"Temps total aquery: {end_time - start_time:.2f}s")
            
            if hasattr(response, "source_nodes") and response.source_nodes:
                sources_text = "\n\nSources :"
                unique_sources = set()
                for node in response.source_nodes:
                    metadata = getattr(node, "metadata", {})
                    title = metadata.get("titre") or metadata.get("file_name") or "Thèse Inconnue"
                    author = metadata.get("auteur", "Auteur Inconnu")
                    source_id = f"- {title} ({author})"
                    if source_id not in unique_sources:
                        unique_sources.add(source_id)
                        sources_text += f"\n{source_id}"
                
                if hasattr(response, "response") and isinstance(response.response, str):
                    response.response += sources_text
                
            return response
        except Exception as e:
            logger.error(f"Erreur lors de la génération de la réponse : {e}")
            return f"Une erreur est survenue lors du traitement de votre question : {e}"

