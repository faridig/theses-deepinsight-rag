import os
import logging
import warnings
from dotenv import load_dotenv

from llama_index.core import (
    Settings,
    PromptTemplate,
    get_response_synthesizer
)
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.postprocessor import MetadataReplacementPostProcessor
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.retrievers.fusion_retriever import FUSION_MODES
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.postprocessor.cohere_rerank import CohereRerank
from llama_index.core.query_engine import RetrieverQueryEngine
from typing import List, Optional
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import TextNode
from src.indexing.vector_service import VectorService

# Configuration des logs - Silence Technique Strict (Directive Alpha)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Suppression de la pollution visuelle
for lib in ["chromadb", "bm25s", "httpx", "urllib3", "llama_index", "openai", "cohere"]:
    logging.getLogger(lib).setLevel(logging.ERROR)
logging.getLogger("opentelemetry").setLevel(logging.CRITICAL)

warnings.filterwarnings("ignore", category=DeprecationWarning)

load_dotenv()

class RAGEngine:
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
        
        self.fusion_retriever = self._setup_retrievers(storage_path)
        self.reranker = self._setup_reranker()
        self._setup_query_engine()

    def _setup_settings(self):
        Settings.llm = OpenAI(model="gpt-4o-mini", request_timeout=30.0, max_retries=2)
        Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

    def _setup_retrievers(self, storage_path: str):
        # Pool de candidats optimisé (12 au lieu de 20 pour CA-4)
        candidate_top_k = 12
        
        vector_retriever = self.index.as_retriever(similarity_top_k=candidate_top_k)
        
        nodes = list(self.vector_service.storage_context.docstore.docs.values())
        if not nodes:
            nodes = self._recover_nodes_from_chroma(storage_path)
            
        retrievers = [vector_retriever]
        if nodes:
            # BM25 est très rapide, mais on limite quand même le pool
            bm25_retriever = BM25Retriever.from_defaults(
                nodes=nodes,
                similarity_top_k=candidate_top_k
            )
            retrievers.append(bm25_retriever)

        # Optimisation CA-4:
        # 1. num_queries=1 -> Éviter l'appel LLM de QueryExpansion (Gain ~2s)
        # 2. similarity_top_k=8 -> Réduire le pool pour le reranking (Gain ~0.5s)
        return QueryFusionRetriever(
            retrievers,
            similarity_top_k=8,
            num_queries=1,
            mode=FUSION_MODES.RECIPROCAL_RANK,
            use_async=True,
            verbose=False
        )

    def _recover_nodes_from_chroma(self, storage_path: str):
        nodes = []
        try:
            chroma_data = self.vector_service.chroma_collection.get()
            if chroma_data and chroma_data.get('ids'):
                ids = chroma_data['ids']
                docs = chroma_data.get('documents') or []
                metas = chroma_data.get('metadatas') or []
                for i in range(len(ids)):
                    text = docs[i] if i < len(docs) else ""
                    metadata = metas[i] if i < len(metas) else {}
                    nodes.append(TextNode(text=text, id_=ids[i], metadata=metadata or {}))
                self.vector_service.storage_context.docstore.add_documents(nodes)
                self.vector_service.storage_context.persist(persist_dir=storage_path)
        except Exception as e:
            logger.error(f"Erreur recouvrement nodes: {e}")
        return nodes

    def _setup_reranker(self) -> Optional[BaseNodePostprocessor]:
        api_key = os.getenv("COHERE_API_KEY")
        if not api_key:
            return None
        return CohereRerank(api_key=api_key, model="rerank-multilingual-v3.0", top_n=5)

    def _setup_query_engine(self):
        qa_prompt = PromptTemplate(
            "Tu es un assistant académique expert. Réponds en utilisant UNIQUEMENT le contexte fourni.\n"
            "Cite auteur et titre. Sois précis sur les acronymes (ex: L2TI).\n"
            "Si inconnu, dis : 'Je ne trouve pas d'information dans les thèses.'\n"
            "---------------------\nCONTEXTE :\n{context_str}\n---------------------\nQUESTION : {query_str}\nRÉPONSE : "
        )

        # Optimisation CA-4: Ordre des post-processeurs
        # 1. On reranke d'abord pour ne garder que les 5 meilleurs
        # 2. On ne fait le remplacement de métadonnées (coûteux) que sur ces 5 nodes
        pps: List[BaseNodePostprocessor] = []
        if self.reranker:
            pps.append(self.reranker)
        pps.extend(self.post_processors)
            
        # Optimisation CA-4: ResponseMode.COMPACT est le plus équilibré
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
            import asyncio
            # Utilisation de aquery pour maximiser les performances asynchrones (CA-4)
            try:
                return asyncio.run(self.query_engine.aquery(question))
            except RuntimeError:
                # Fallback pour les environnements avec une boucle déjà active
                return self.query_engine.query(question)
        except Exception as e:
            err_msg = str(e).lower()
            if "429" in err_msg or "rate limit" in err_msg:
                return "Le service est temporairement saturé (Limite API). Veuillez réessayer dans une minute."
            if "authentication" in err_msg or "api key" in err_msg:
                return "Erreur d'authentification aux services de recherche."
            
            # Pas de traceback dans la console, log uniquement
            logger.error(f"Erreur RAG: {e}")
            return "Une erreur technique est survenue lors de la recherche."
