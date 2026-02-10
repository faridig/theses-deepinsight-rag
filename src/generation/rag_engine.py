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
from llama_index.core.schema import TextNode, NodeWithScore, QueryBundle
from src.indexing.vector_service import VectorService
from typing import List, Optional

# Configuration des logs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Silence noisy libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("llama_index").setLevel(logging.WARNING)
logging.getLogger("opentelemetry").setLevel(logging.ERROR)
logging.getLogger("bm25s").setLevel(logging.WARNING)

load_dotenv()

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
            # 1. Exclusion des clés techniques
            node.excluded_llm_metadata_keys = excluded_keys
            # 2. Simplification du formatage du texte (via templates LlamaIndex)
            node.metadata_template = "{key} : {value}"
            node.text_template = "THÈSE INFO :\n{metadata_str}\nEXTRAIT :\n{content}\n"
            # 3. Garantie que page_label existe
            if "page_label" not in node.metadata:
                node.metadata["page_label"] = "N/A"
                
        return nodes

class RAGEngine:
    """
    Moteur RAG pour interroger les thèses avec Sentence Window Retrieval.
    """
    def __init__(self, storage_path: str = "./storage/chroma", collection_name: str = "theses_collection"):
        # 1. Configuration du LLM et de l'Embedding
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY non trouvée dans l'environnement.")
        
        Settings.llm = OpenAI(model="gpt-4o-mini")
        Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
        
        # 2. Chargement de l'index via VectorService
        try:
            self.vector_service = VectorService(storage_path=storage_path, collection_name=collection_name)
            self.index = self.vector_service.index
            
            # Vérifier si l'index contient des documents (approximatif via chroma)
            if self.vector_service.chroma_collection.count() == 0:
                logger.warning("L'index Chroma est vide. Les réponses seront limitées ou absentes.")
                
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
        if not cohere_api_key:
            logger.warning("COHERE_API_KEY non trouvée dans l'environnement. Le Reranking Cohere risque d'échouer.")
        
        self.reranker = CohereRerank(
            api_key=cohere_api_key,
            model="rerank-multilingual-v3.0",
            top_n=3
        )

        # 6. Assemblage du Retriever Fusionné (PBI-010 - Hybrid Search)
        self.vector_retriever = self.index.as_retriever(similarity_top_k=20)
        
        # Récupération des nodes pour BM25
        nodes = list(self.index.docstore.docs.values())
        if not nodes:
            logger.info("Docstore vide, récupération des nodes depuis Chroma pour BM25...")
            try:
                chroma_data = self.vector_service.chroma_collection.get()
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
                    logger.info(f"{len(nodes)} nodes récupérés depuis Chroma.")
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des nodes depuis Chroma : {e}")
                nodes = []

        if nodes:
            self.bm25_retriever = BM25Retriever.from_defaults(
                nodes=nodes,
                similarity_top_k=20
            )
            retrievers = [self.vector_retriever, self.bm25_retriever]
            logger.info("Recherche Hybride activée (Dense + Sparse).")
        else:
            logger.warning("BM25 désactivé (aucun node trouvé). Recherche Dense uniquement.")
            retrievers = [self.vector_retriever]

        self.fusion_retriever = QueryFusionRetriever(
            retrievers,
            similarity_top_k=20,
            num_queries=3,
            mode=FUSION_MODES.RECIPROCAL_RANK,
            use_async=True,
            verbose=False # Moins de bruit
        )

        # 7. Assemblage du Query Engine final
        # Note: On fusionne les post-processeurs
        all_post_processors: List[BaseNodePostprocessor] = [
            *self.post_processors,
            self.reranker
        ]
        
        self.query_engine = RetrieverQueryEngine(
            retriever=self.fusion_retriever,
            node_postprocessors=all_post_processors
        )
        
        # Mise à jour du prompt
        self.query_engine.update_prompts(
            {"response_synthesizer:text_qa_template": self.qa_prompt_tmpl}
        )
        
    def ask(self, question: str):
        """
        Exécute une requête RAG et retourne la réponse.
        """
        if not question or not question.strip():
            return "Veuillez poser une question valide."
        
        try:
            response = self.query_engine.query(question)
            
            # Post-traitement pour inclure les sources dans le texte de la réponse (PBI-012)
            if hasattr(response, "source_nodes") and response.source_nodes:
                sources_text = "\n\nSources :"
                unique_sources = set()
                for node in response.source_nodes:
                    # Extraction sécurisée des métadonnées
                    metadata = getattr(node, "metadata", {})
                    title = metadata.get("titre", "Thèse Inconnue")
                    author = metadata.get("auteur", "Auteur Inconnu")
                    source_id = f"- {title} ({author})"
                    if source_id not in unique_sources:
                        unique_sources.add(source_id)
                        sources_text += f"\n{source_id}"
                
                # Ajout au texte de la réponse si c'est une réponse standard (non-streaming)
                if hasattr(response, "response") and isinstance(response.response, str):
                    response.response += sources_text
                
            return response
        except Exception as e:
            logger.error(f"Erreur lors de la génération de la réponse : {e}")
            return f"Une erreur est survenue lors du traitement de votre question : {e}"
