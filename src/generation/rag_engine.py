import os
import logging
import asyncio
import time
import sys
from typing import List, Optional, Dict, Any

from llama_index.core import (
    Settings,
    PromptTemplate,
)
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.retrievers.fusion_retriever import FUSION_MODES

try:
    from llama_index.retrievers.bm25 import BM25Retriever
except ImportError:
    BM25Retriever = None

try:
    from llama_index.postprocessor.cohere_rerank import CohereRerank
except ImportError:
    CohereRerank = None

from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
from llama_index.core.base.response.schema import Response
from src.indexing.vector_service import VectorService

from src.config import setup_settings

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if BM25Retriever is None:
    logger.warning("BM25Retriever non trouvé dans llama_index.retrievers.bm25")
if CohereRerank is None:
    logger.warning(
        "CohereRerank non trouvé dans llama_index.postprocessor.cohere_rerank"
    )

# Paramètres de récupération
RETRIEVAL_TOP_K = 10

# Silence noisy libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("qdrant_client").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("llama_index").setLevel(logging.WARNING)
logging.getLogger("opentelemetry").setLevel(logging.ERROR)
logging.getLogger("bm25s").setLevel(logging.WARNING)
logging.getLogger("llama_index.core.llms.utils").setLevel(logging.ERROR)
logging.getLogger("llama_index.core.settings").setLevel(logging.ERROR)


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

    def _postprocess_nodes(
        self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        excluded_keys = [
            "_node_content",
            "relationships",
            "file_path",
            "file_size",
            "creation_date",
            "last_modified_date",
            "original_text",
            "window",
            "doc_id",
            "document_id",
            "ref_doc_id",
            "_node_type",
            "file_type",
            "file_name",
            "ollama_summary",
            "extracted_title",
        ]

        for node_with_score in nodes:
            node = node_with_score.node
            current_excluded = list(excluded_keys)

            # Si on a le titre extrait via Ollama, on l'utilise
            if (
                "extracted_title" in node.metadata
                and node.metadata["extracted_title"] != "Titre non extrait"
            ):
                node.metadata["titre_document"] = node.metadata["extracted_title"]

            if (
                "titre" not in node.metadata
                and "titre_document" not in node.metadata
                and "file_name" in current_excluded
            ):
                current_excluded.remove("file_name")

            node.excluded_llm_metadata_keys = current_excluded
            node.metadata_template = "{key} : {value}"

            if isinstance(node, TextNode):
                node.text_template = (
                    "THÈSE INFO :\n{metadata_str}\nEXTRAIT :\n{content}\n"
                )

            if "page_label" not in node.metadata:
                node.metadata["page_label"] = "N/A"

        return nodes


class CohereThresholdPostprocessor(BaseNodePostprocessor):
    """
    Filtre les nœuds ayant un score de reranking trop faible (PBI-082).
    """

    threshold: float = 0.6

    def _postprocess_nodes(
        self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        # On ne filtre que si les nœuds ont été rerankés (le score est généralement normalisé par Cohere)
        filtered_nodes = [
            node
            for node in nodes
            if node.score is not None and node.score >= self.threshold
        ]
        logger.info(
            f"[PBI-100] Post-filtering: {len(nodes)} nodes in, {len(filtered_nodes)} nodes out (Threshold={self.threshold})"
        )
        return filtered_nodes


class ConditionalWindowReplacementProcessor(BaseNodePostprocessor):
    """
    Remplace le texte du nœud par sa fenêtre contextuelle seulement si le score est élevé (PBI-082).
    Cela permet de garder de la précision sur les résultats moyens et du contexte sur les excellents.
    """

    threshold: float = 0.7
    target_metadata_key: str = "window"

    def _postprocess_nodes(
        self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        for node_with_score in nodes:
            if (
                node_with_score.score is not None
                and node_with_score.score >= self.threshold
            ):
                node = node_with_score.node
                window_text = node.metadata.get(self.target_metadata_key)
                if window_text:
                    node.set_content(window_text)
        return nodes


class DiversityPostprocessor(BaseNodePostprocessor):
    """
    Assure la diversité des sources tout en permettant plusieurs extraits
    par document si la pertinence est élevée (PBI-015/Review).
    """

    target_top_n: int = 5
    max_per_doc: int = 2

    def __init__(
        self,
        target_top_n: Optional[int] = None,
        max_per_doc: Optional[int] = None,
        **kwargs,
    ):
        """
        Initialise le post-processeur avec des paramètres optionnels.
        """
        super().__init__(**kwargs)
        if target_top_n is not None:
            self.target_top_n = target_top_n
        if max_per_doc is not None:
            self.max_per_doc = max_per_doc

    def _postprocess_nodes(
        self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        doc_counts = {}
        filtered_nodes = []

        for node_with_score in nodes:
            doc_id = (
                node_with_score.node.metadata.get("titre")
                or node_with_score.node.metadata.get("file_name")
                or node_with_score.node.node_id
            )

            count = doc_counts.get(doc_id, 0)
            if count < self.max_per_doc:
                filtered_nodes.append(node_with_score)
                doc_counts[doc_id] = count + 1

            if len(filtered_nodes) >= self.target_top_n:
                break

        return filtered_nodes


class RAGEngine:
    """
    Moteur RAG multi-collections pour l'isolation des thèses par domaine (PBI-023).
    """

    def __init__(
        self,
        storage_path: str = "./storage/qdrant",
        collection_name: str = "theses-default",
    ):
        # 1. Configuration globale (Lazy & Respectful of existing settings/mocks)
        setup_settings()

        self.storage_path = storage_path
        self.default_collection = collection_name
        self._query_engines: Dict[str, RetrieverQueryEngine] = {}
        self._shared_vector_service: Optional[VectorService] = None
        self.index_ref = None

        # Initialisation paresseuse du reranker
        self.reranker = None
        cohere_api_key = os.getenv("COHERE_API_KEY")
        if cohere_api_key and CohereRerank:
            try:
                self.reranker = CohereRerank(
                    api_key=cohere_api_key,
                    model="rerank-multilingual-v3.0",
                    top_n=RETRIEVAL_TOP_K,
                )
            except Exception as e:
                logger.warning(f"Échec de l'initialisation de CohereRerank: {e}")

        self.qa_prompt_tmpl = PromptTemplate(
            "Tu es un expert en analyse de thèses académiques. Ta mission est de répondre aux questions de manière 100% fidèle au contexte fourni.\n\n"
            "### RÈGLES DE RIGUEUR SCIENTIFIQUE (STRICT CONTEXT ADHERENCE) :\n"
            "1. UTILISE UNIQUEMENT LE CONTEXTE FOURNI. N'utilise aucune connaissance extérieure. Si l'information n'est pas là, tu ne l'inventes pas.\n"
            "2. RÉPONSE NÉGATIVE OBLIGATOIRE : Si le contexte ne contient pas la réponse à la question, réponds EXACTEMENT : 'Je ne sais pas (information non présente dans les sources).' Ne tente pas de déduire ou de généraliser.\n"
            "3. CITATION SYSTÉMATIQUE ET PRÉCISE : Pour chaque affirmation, cite obligatoirement la source entre crochets à la fin de la phrase. Format : [Titre, Auteur, Page X].\n"
            "4. PRIORITÉ À LA FIABILITÉ : Il vaut mieux une réponse courte et sourcée qu'une synthèse longue non prouvée.\n"
            "5. AUCUN 'SLIPPAGE' SÉMANTIQUE : Reste strictement dans le domaine défini par la question.\n\n"
            "---------------------\n"
            "CONTEXTE :\n"
            "{context_str}\n"
            "---------------------\n"
            "QUESTION : {query_str}\n"
            "RÉPONSE (Analyse factuelle et sourcée) : "
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
                storage_path=self.storage_path, collection_name=collection_name
            )
            return self._shared_vector_service

        # Si on change de collection mais qu'on garde le même storage_path (client)
        # on crée une nouvelle instance de VectorService partageant le même client
        return VectorService(
            storage_path=self.storage_path,
            collection_name=collection_name,
            client=self._shared_vector_service.client,
            aclient=self._shared_vector_service.aclient,
        )

    def _get_query_engine(self, collection_name: str) -> RetrieverQueryEngine:
        """
        Récupère ou crée un QueryEngine pour une collection spécifique (Routing PBI-023).
        """
        if collection_name in self._query_engines:
            return self._query_engines[collection_name]

        logger.info(
            f"Initialisation du QueryEngine pour la collection : {collection_name}"
        )

        vector_service = self._get_vector_service(collection_name)

        # Gestion du mode dégradé (PBI-Review)
        if not vector_service.available:
            logger.error(
                f"Impossible de créer le QueryEngine pour {collection_name} : VectorService indisponible."
            )
            raise RuntimeError(
                f"Base de données (Qdrant) injoignable pour la collection '{collection_name}'."
            )

        index = vector_service.index
        self.index_ref = index

        # Vector Retriever
        vector_retriever = index.as_retriever(similarity_top_k=RETRIEVAL_TOP_K)

        # BM25 Retriever
        try:
            nodes = vector_service.get_all_nodes()
            if nodes and BM25Retriever:
                bm25_retriever = BM25Retriever.from_defaults(
                    nodes=list(nodes), similarity_top_k=RETRIEVAL_TOP_K
                )
                retrievers = [vector_retriever, bm25_retriever]
            else:
                retrievers = [vector_retriever]
        except Exception as e:
            logger.warning(f"BM25 non disponible pour {collection_name} : {e}")
            retrievers = [vector_retriever]

        # Fusion Retriever
        # On utilise 3 requêtes si on a un vrai LLM ou si on est en environnement de test
        has_openai_key = bool(os.getenv("OPENAI_API_KEY"))
        is_test = os.getenv("IS_TESTING") == "1" or "pytest" in sys.modules
        num_queries = 3 if (has_openai_key or is_test) else 1

        # PBI-082: Configuration du LLM pour la transformation de requête avec T=0.1
        query_gen_llm = None
        if has_openai_key:
            from llama_index.llms.openai import OpenAI

            query_gen_llm = OpenAI(model="gpt-4o-mini", temperature=0.1)

        fusion_retriever = ParallelMultiQueryRetriever(
            retrievers,
            similarity_top_k=RETRIEVAL_TOP_K,
            num_queries=num_queries,
            mode=FUSION_MODES.RELATIVE_SCORE,  # PBI-082: Hybrid Tuning
            retriever_weights=[0.7, 0.3]
            if len(retrievers) > 1
            else [1.0],  # Alpha Calibration
            use_async=vector_service.aclient is not None
            and not isinstance(vector_service.aclient, (str, type(None))),
            verbose=False,
            llm=query_gen_llm or Settings.llm,
        )

        # Hack pour le wrapper AsyncQdrantLocalWrapper (qui n'est pas une instance d'AsyncQdrantClient)
        if hasattr(vector_service.aclient, "_client"):
            fusion_retriever.use_async = False  # On force sync pour le wrapper local

        # Query Engine
        all_post_processors: List[BaseNodePostprocessor] = [
            NodeCleaningProcessor(),  # PBI-012
        ]

        if self.reranker:
            all_post_processors.append(self.reranker)
            all_post_processors.append(
                CohereThresholdPostprocessor(threshold=0.6)
            )  # PBI-082

        # PBI-082: Small-to-Big Retrieval conditionnel
        all_post_processors.append(ConditionalWindowReplacementProcessor(threshold=0.7))

        all_post_processors.append(DiversityPostprocessor(target_top_n=3))

        query_engine = RetrieverQueryEngine(
            retriever=fusion_retriever, node_postprocessors=all_post_processors
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

        theme_slug = theme if theme else self.default_collection

        # Robustesse : s'assurer que le nom de la collection commence par 'theses-' (PBI-023)
        if (
            theme_slug
            and not theme_slug.startswith("theses-")
            and theme_slug != ":memory:"
        ):
            collection_name = f"theses-{theme_slug}"
        else:
            collection_name = theme_slug

        try:
            query_engine = self._get_query_engine(collection_name)
            start_time = time.time()

            use_async = getattr(query_engine.retriever, "use_async", False)
            if use_async:
                response = await query_engine.aquery(question)
            else:
                response = await asyncio.to_thread(query_engine.query, question)

            end_time = time.time()
            logger.info(
                f"Temps total aquery ({collection_name}): {end_time - start_time:.2f}s"
            )

            if isinstance(response, Response) and response.source_nodes:
                sources_text = "\n\nSources :"
                unique_sources = set()
                for node in response.source_nodes:
                    metadata = node.metadata
                    title = (
                        metadata.get("titre")
                        or metadata.get("file_name")
                        or "Thèse Inconnue"
                    )
                    author = metadata.get("auteur", "Auteur Inconnu")
                    source_id = f"- {title} ({author})"
                    if source_id not in unique_sources:
                        unique_sources.add(source_id)
                        sources_text += f"\n{source_id}"

                if response.response:
                    response.response += sources_text

            # PBI-100: Gestion de la réponse vide ou absence de sources
            if not response.response or not response.source_nodes:
                default_msg = "Je ne trouve pas d'information pertinente dans les thèses de ce domaine."
                if not response.response:
                    response.response = default_msg
                else:
                    # On a une réponse du LLM mais pas de sources valides (étrange mais possible)
                    # ou le LLM dit "Je ne sais pas"
                    if "Je ne sais pas" in response.response:
                        response.response = default_msg

            return response

        except Exception as e:
            error_msg = str(e)
            if (
                "injoignable" in error_msg.lower()
                or "connection refused" in error_msg.lower()
                or "unavailable" in error_msg.lower()
            ):
                friendly_msg = "Désolé, la base de données de thèses est actuellement inaccessible. Veuillez réessayer plus tard ou contacter un administrateur."
            else:
                friendly_msg = f"Une erreur est survenue lors du traitement de votre question : {e}"

            logger.error(
                f"Erreur lors de la génération de la réponse pour {collection_name} : {e}"
            )
            return Response(response=friendly_msg, source_nodes=[])

    def get_available_themes(self) -> List[str]:
        """
        Détecte dynamiquement les thèmes disponibles dans Qdrant (PBI-035).
        Optimisé pour le mode dégradé.
        """
        try:
            svc = self._get_vector_service(self.default_collection)
            if not svc.available:
                return []
            return svc.list_collections()
        except Exception as e:
            logger.warning(f"Erreur lors de la récupération des thèmes : {e}")
            return []

    def get_theme_stats(self, theme: str) -> Dict[str, Any]:
        """
        Récupère les stats pour un thème donné (PBI-037).
        """
        svc = self._get_vector_service(theme)
        return svc.get_collection_stats(theme)
