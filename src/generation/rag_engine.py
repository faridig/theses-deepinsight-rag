from llama_index.core import (
    Settings,
    PromptTemplate,
    get_response_synthesizer,
)
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.postprocessor import MetadataReplacementPostProcessor
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.postprocessor.cohere_rerank import CohereRerank
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from typing import List, Optional, Dict
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, TextNode
from src.indexing.vector_service import VectorService
import logging
import os
import warnings
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class RAGEngine:
    """
    Moteur RAG optimisé pour la précision (CA-1) et la performance (CA-4).
    Temps de réponse cible : < 5s.
    """
    def __init__(self, storage_path: str = "./storage/chroma", collection_name: str = "theses_collection"):
        load_dotenv()
        self._setup_settings()
        
        try:
            self.vector_service = VectorService(storage_path=storage_path, collection_name=collection_name)
        except Exception as e:
            logger.error(f"Échec critique VectorService: {e}")
            raise RuntimeError(f"Initialisation impossible : {e}")

        self.post_processors: List[BaseNodePostprocessor] = [
            MetadataReplacementPostProcessor(target_metadata_key="window"),
        ]
        
        self.fusion_retriever = self._setup_retrievers()
        self.reranker = self._setup_reranker()
        if self.reranker:
            self.post_processors.append(self.reranker)
        self._setup_query_engine()

    def _setup_settings(self):
        Settings.llm = OpenAI(model="gpt-4o-mini", request_timeout=30.0, max_retries=2)
        Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

    def _setup_retrievers(self):
        """
        Sets up Hybrid Retrieval pipeline (BM25 + Vectorial).
        (PBI-010: Recherche Hybride)
        """
        candidate_top_k = 15
        
        # 1. Vector Retriever
        vector_retriever = self.vector_service.get_retriever(similarity_top_k=candidate_top_k)
        
        # 2. BM25 Retriever
        # We need nodes for BM25. We get them from the docstore.
        nodes = list(self.vector_service.storage_context.docstore.docs.values())
        
        if not nodes:
            logger.warning("Docstore vide. Utilisation du retriever vectoriel uniquement.")
            return vector_retriever
            
        bm25_retriever = BM25Retriever.from_defaults(
            nodes=nodes,
            similarity_top_k=candidate_top_k
        )
        
        # 3. Hybrid Fusion
        # On combine les deux avec un QueryFusionRetriever
        fusion_retriever = QueryFusionRetriever(
            [vector_retriever, bm25_retriever],
            similarity_top_k=candidate_top_k,
            num_queries=1, # On ne fait pas de multi-query pour rester dans les clous de performance
            mode="reciprocal_rerank",
            use_async=True
        )
        
        return fusion_retriever

    def _setup_reranker(self):
        api_key = os.getenv("COHERE_API_KEY")
        if api_key:
            return CohereRerank(api_key=api_key, top_n=5)
        logger.warning("COHERE_API_KEY non trouvée. Le Reranker est désactivé.")
        return None

    def _setup_query_engine(self):
        qa_prompt_tmpl = (
            "Context information is below.\n"
            "---------------------\n"
            "{context_str}\n"
            "---------------------\n"
            "Given the context information and not prior knowledge, "
            "answer the query. If the answer is not in the context, say that you don't know.\n"
            "Query: {query_str}\n"
            "Answer: "
        )
        qa_prompt = PromptTemplate(qa_prompt_tmpl)

        response_synthesizer = get_response_synthesizer(
            response_mode=ResponseMode.COMPACT,
            text_qa_template=qa_prompt,
            use_async=True
        )

        self.query_engine = RetrieverQueryEngine(
            retriever=self.fusion_retriever,
            node_postprocessors=self.post_processors,
            response_synthesizer=response_synthesizer
        )

    def ask(self, question: str):
        if not question or not question.strip():
            return "Veuillez poser une question valide."
        try:
            import asyncio
            try:
                # Check if there is an existing event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If running, we might need to use another approach, 
                    # but for CLI scripts, this is usually fine or we are in a new thread.
                    # In some environments, nest_asyncio is needed.
                    response = self.query_engine.query(question)
                else:
                    response = loop.run_until_complete(self.query_engine.aquery(question))
            except Exception:
                response = self.query_engine.query(question)
            
            # 1. Réponse principale
            final_answer = str(response)
            
            # 2. Construction du bloc Sources (PBI-012: Preuve d'Extraction)
            source_block = "\n\n---------------------\nSources:\n"
            
            unique_sources = {}
            if hasattr(response, 'source_nodes'):
                for node_with_score in response.source_nodes:
                    node = node_with_score.node
                    metadata = node.metadata
                    
                    page_label = metadata.get("page_number", metadata.get("page_label", "N/A"))
                    file_name = metadata.get("file_name", metadata.get("file_path", "Document Inconnu"))
                    title = metadata.get("titre", file_name)
                    
                    text_snippet = node.get_content()[:150].strip().replace('\n', ' ')
                    if len(node.get_content()) > 150:
                        text_snippet += "..."
                    
                    unique_key = (title, page_label)
                    
                    if unique_key not in unique_sources:
                        unique_sources[unique_key] = {
                            "page_label": page_label,
                            "title": title,
                            "snippet": text_snippet
                        }
                        
            if not unique_sources:
                return final_answer
                
            source_list = []
            for source in unique_sources.values():
                source_list.append(
                    f"- [Page {source['page_label']} - {source['title']}] : {source['snippet']}"
                )
            
            source_block += "\n".join(source_list)
            return final_answer + source_block
            
        except Exception as e:
            err_msg = str(e).lower()
            if "429" in err_msg or "rate limit" in err_msg:
                return "Le service est temporairement saturé (Limite API). Veuillez réessayer dans une minute."
            
            logger.error(f"Erreur RAG: {e}")
            return "Une erreur technique est survenue lors de la recherche."
