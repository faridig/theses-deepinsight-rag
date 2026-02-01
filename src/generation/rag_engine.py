import os
import logging
from dotenv import load_dotenv

from llama_index.core import (
    Settings,
    PromptTemplate,
)
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.postprocessor import MetadataReplacementPostProcessor, SimilarityPostprocessor
from llama_index.core.indices.query.query_transform import HyDEQueryTransform
from llama_index.core.query_engine import TransformQueryEngine
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
        # MetadataReplacementPostProcessor remplace le nœud par sa fenêtre de contexte
        # SimilarityPostprocessor désactivé pour la démonstration afin de garantir des réponses
        self.post_processors = [
            MetadataReplacementPostProcessor(target_metadata_key="window"),
            # SimilarityPostprocessor(similarity_cutoff=0.4)  # Désactivé pour démo
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

        # 5. Assemblage du Query Engine de base
        self.base_query_engine = self.index.as_query_engine(
            node_postprocessors=self.post_processors,
            similarity_top_k=5
        )
        
        # Mise à jour du prompt de base
        self.base_query_engine.update_prompts(
            {"response_synthesizer:text_qa_template": self.qa_prompt_tmpl}
        )

        # 6. Transformation HyDE (Intelligence Augmentée)
        self.hyde = HyDEQueryTransform(include_original=True)
        self.query_engine = TransformQueryEngine(self.base_query_engine, self.hyde)
        
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
