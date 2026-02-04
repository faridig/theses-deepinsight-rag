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

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

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
            top_n=5
        )

        # 6. Assemblage du Retriever Fusionné (PBI-010 - Hybrid Search)
        self.vector_retriever = self.index.as_retriever(similarity_top_k=10)
        
        # Récupération des nodes pour BM25
        nodes = list(self.index.docstore.docs.values())
        if not nodes:
            logger.info("Docstore vide, récupération des nodes depuis Chroma pour BM25...")
            try:
                chroma_data = self.vector_service.chroma_collection.get()
                nodes = []
                if chroma_data and chroma_data.get('ids'):
                    ids = chroma_data.get('ids', [])
                    documents = chroma_data.get('documents', []) or []
                    metadatas = chroma_data.get('metadatas', []) or []
                    
                    for i in range(len(ids)):
                        text = documents[i] if i < len(documents) else ""
                        metadata = metadatas[i] if (metadatas and i < len(metadatas)) else {}
                        nodes.append(TextNode(
                            text=text,
                            id_=ids[i],
                            metadata=metadata or {}
                        ))
                logger.info(f"{len(nodes)} nodes récupérés depuis Chroma.")
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des nodes depuis Chroma : {e}")
                nodes = []

        if nodes:
            self.bm25_retriever = BM25Retriever.from_defaults(
                nodes=nodes,
                similarity_top_k=10
            )
            retrievers = [self.vector_retriever, self.bm25_retriever]
            logger.info("Recherche Hybride activée (Dense + Sparse).")
        else:
            logger.warning("BM25 désactivé (aucun node trouvé). Recherche Dense uniquement.")
            retrievers = [self.vector_retriever]

        self.fusion_retriever = QueryFusionRetriever(
            retrievers,
            similarity_top_k=10,
            num_queries=1,  # Optimisation CA-4: Pas de query expansion (trop lent), juste fusion hybride
            mode=FUSION_MODES.RECIPROCAL_RANK,
            use_async=True,
            verbose=False
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
            return response
        except Exception as e:
            logger.error(f"Erreur lors de la génération de la réponse : {e}")
            return f"Une erreur est survenue lors du traitement de votre question : {e}"
