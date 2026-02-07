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


    """
    Moteur RAG optimisé pour la précision (CA-1) et la performance (CA-4).
    Temps de réponse cible : < 5s.
    """
    def __init__(self, storage_path: str = "./storage/chroma", collection_name: str = "theses_collection"):
        self._setup_settings()
        
        try:
            self.vector_service = VectorService(storage_path=storage_path, collection_name=collection_name)
            self.index = self.vector_service.index
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
        Sets up a robust retrieval pipeline using ParentDocumentRetriever and BM25.
        """
        candidate_top_k = 15
        
        # 1. Parent Document Retriever for semantic search
        parent_retriever = self.vector_service.get_retriever(similarity_top_k=candidate_top_k)
        
        # 2. BM25 Retriever for keyword-based search
        # This requires recovering all nodes from the docstore first.
        all_nodes = list(self.vector_service.docstore.docs.values())
            
        retrievers = [parent_retriever]
        if all_nodes:
            bm25_retriever = BM25Retriever.from_defaults(
                nodes=all_nodes,
                similarity_top_k=candidate_top_k
            )
            retrievers.append(bm25_retriever)

        return parent_retriever

        # Optimisation CA-1 & CA-4:
        # 1. On remplace d'abord les métadonnées (MetadataReplacement)
        # 2. Le Reranker voit ainsi le texte enrichi (évite le Reranker Blindness)
        pps: List[BaseNodePostprocessor] = []
        pps.extend(self.post_processors)
            
        # Optimisation CA-1: Fusion plus robuste
        # num_queries=2 permet une expansion légère pour capturer les termes exacts (BM25)
        # tout en restant sous la barre des 5s (CA-4)
        response_synthesizer = get_response_synthesizer(
            response_mode=ResponseMode.COMPACT,
            text_qa_template=qa_prompt,
            use_async=True
        )

        self.query_engine = RetrieverQueryEngine(
            retriever=self.fusion_retriever,
            node_postprocessors=pps,
            response_synthesizer=response_synthesizer
        )

    def ask(self, question: str):
        if not question or not question.strip():
            return "Veuillez poser une question valide."
        try:
            # Récupère l'objet Response qui contient la réponse et les sources
            # Utilisation de aquery pour maximiser les performances asynchrones (CA-4)
            try:
                import asyncio
                response = asyncio.run(self.query_engine.aquery(question))
            except RuntimeError:
                # Fallback pour les environnements avec une boucle déjà active
                response = self.query_engine.query(question)
            except NameError:
                 # Si 'asyncio' n'est pas importé pour une raison ou une autre, utiliser query synchrone
                 response = self.query_engine.query(question)
            
            # 1. Réponse principale
            final_answer = str(response)
            
            # 2. Construction du bloc Sources (PBI-012: Preuve d'Extraction)
            source_block = "\n\n---------------------\nSources:\n"
            
            # Utiliser un dictionnaire pour garantir l'unicité des sources (même titre/page)
            unique_sources = {}
            for node_with_score in response.source_nodes:
                node = node_with_score.node
                metadata = node.metadata
                
                # Extraction des métadonnées
                page_label = metadata.get("page_label", "N/A")
                file_name = metadata.get("file_name", metadata.get("file_path", "Document Inconnu"))
                title = metadata.get("titre", file_name)
                
                # Nettoyage et troncation du snippet
                text_snippet = node.get_text()[:150].strip().replace('\n', ' ')
                if len(node.get_text()) > 150:
                    text_snippet += "..."
                
                # Clé d'unicité
                unique_key = (title, page_label)
                
                if unique_key not in unique_sources:
                    unique_sources[unique_key] = {
                        "page_label": page_label,
                        "title": title,
                        "snippet": text_snippet
                    }
                    
            if not unique_sources:
                return final_answer # Pas de sources trouvées
                
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
            if "authentication" in err_msg or "api key" in err_msg:
                return "Erreur d'authentification aux services de recherche."
            
            # Pas de traceback dans la console, log uniquement
            logger.error(f"Erreur RAG: {e}")
            return "Une erreur technique est survenue lors de la recherche."
