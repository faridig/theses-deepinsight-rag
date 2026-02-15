import os
import logging
from dotenv import load_dotenv
from llama_index.core import Settings
import llama_index.llms.openai
import llama_index.embeddings.openai
from llama_index.core.llms import MockLLM
from llama_index.core.embeddings import MockEmbedding

logger = logging.getLogger(__name__)

# Silence technique (PBI-027)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Normalisation des thèmes (PBI-026/Review)
CANONICAL_THEMES = {
    "ia": "intelligence-artificielle",
    "ai": "intelligence-artificielle",
    "intelligence artificielle": "intelligence-artificielle",
    "agri": "agriculture",
    "agriculture": "agriculture",
    "bio": "biologie",
    "biologie": "biologie",
    "medecine": "sante",
    "santé": "sante",
    "sante": "sante"
}

def normalize_theme(theme_name: str) -> str:
    """
    Retourne le nom canonique d'un thème ou un slug standardisé.
    """
    raw_name = theme_name.lower().strip()
    # 1. Vérifier si c'est un alias connu
    if raw_name in CANONICAL_THEMES:
        return CANONICAL_THEMES[raw_name]
    
    # 2. Sinon, retourner un slug standardisé
    return raw_name.replace(" ", "-")

def setup_settings():
    """
    Initialise les paramètres globaux de LlamaIndex (LLM et Embeddings).
    Charge les variables d'environnement depuis le fichier .env.
    """
    # 1. Charger les variables d'environnement
    load_dotenv()
    
    # 2. Vérifier la présence de la clé API OpenAI
    has_openai_key = bool(os.getenv("OPENAI_API_KEY"))
    
    # Si pas de clé, on force le mode test pour utiliser des Mocks
    if not has_openai_key:
        if os.getenv("IS_TESTING") != "1":
            logger.info("OPENAI_API_KEY non trouvée. Basculement en mode Mock (IS_TESTING=1).")
            os.environ["IS_TESTING"] = "1"
    
    # 3. Configuration du LLM
    try:
        if has_openai_key:
            Settings.llm = llama_index.llms.openai.OpenAI(model="gpt-4o-mini")
        else:
            Settings.llm = MockLLM()
    except Exception as e:
        logger.warning(f"Erreur lors de l'initialisation du LLM OpenAI : {e}. Utilisation de MockLLM.")
        Settings.llm = MockLLM()
        
    # 4. Configuration de l'Embedding Model
    try:
        if has_openai_key:
            Settings.embed_model = llama_index.embeddings.openai.OpenAIEmbedding(model="text-embedding-3-small")
        else:
            Settings.embed_model = MockEmbedding(embed_dim=1536)
    except Exception as e:
        logger.warning(f"Erreur lors de l'initialisation de l'Embedding OpenAI : {e}. Utilisation de MockEmbedding.")
        Settings.embed_model = MockEmbedding(embed_dim=1536)
    
    logger.info(f"LlamaIndex Settings initialisés (LLM: {type(Settings.llm).__name__}, Embed: {type(Settings.embed_model).__name__})")
