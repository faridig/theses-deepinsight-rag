import os
import sys
import logging
from dotenv import load_dotenv
from llama_index.core import Settings
import llama_index.llms.openai
import llama_index.embeddings.openai
import llama_index.llms.ollama
from llama_index.core.llms import MockLLM
from llama_index.core.embeddings import MockEmbedding

logger = logging.getLogger(__name__)


# Initialisation de l'instrumentation Phoenix via OpenInference (Bug Fix)
def setup_phoenix_instrumentation():
    """
    Configure l'instrumentation OpenInference pour exporter les traces vers Phoenix.
    """
    try:
        from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk import trace as trace_sdk
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor

        # Détection du mode test - plusieurs méthodes
        is_test_mode = (
            os.getenv("IS_TESTING") == "1"
            or os.getenv("PYTEST_CURRENT_TEST") is not None
            or "pytest" in sys.modules
            or "unittest" in sys.modules
        )

        if is_test_mode:
            logger.info(
                "Mode test détecté - instrumentation simplifiée sans export OTLP"
            )
            # En mode test, on crée un tracer provider minimal sans export
            tracer_provider = trace_sdk.TracerProvider()
            trace.set_tracer_provider(tracer_provider)
        else:
            # Configuration de l'export OTLP vers Phoenix
            # Priorité aux variables d'environnement standard OTEL
            endpoint = os.getenv(
                "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:6006/v1/traces"
            )

            # Création du tracer provider avec export OTLP
            tracer_provider = trace_sdk.TracerProvider()

            try:
                # Si l'endpoint ne finit pas par /v1/traces et qu'on utilise OTLPSpanExporter (HTTP),
                # on pourrait avoir des problèmes, mais OTLPSpanExporter gère souvent la base.
                span_exporter = OTLPSpanExporter(endpoint=endpoint)
                span_processor = SimpleSpanProcessor(span_exporter=span_exporter)
                tracer_provider.add_span_processor(span_processor=span_processor)
                trace.set_tracer_provider(tracer_provider)
                logger.info(f"Export OTLP configuré vers {endpoint}")
            except Exception as export_error:
                logger.warning(
                    f"Impossible de configurer l'export OTLP : {export_error}. "
                    "Les traces seront générées localement mais non exportées."
                )

        # Instrumentation de LlamaIndex
        LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info("Instrumentation Arize Phoenix activée via OpenInference")

    except ImportError as e:
        logger.warning(
            f"OpenInference non disponible : {e}. Les traces Phoenix seront désactivées."
        )
    except Exception as e:
        logger.warning(f"Impossible d'activer l'instrumentation Phoenix : {e}")


# Appel de la fonction d'instrumentation
setup_phoenix_instrumentation()

# Silence technique (PBI-027)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("engineio").setLevel(logging.WARNING)
logging.getLogger("socketio").setLevel(logging.WARNING)

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
    "sante": "sante",
}


def normalize_theme(theme_name: str) -> str:
    """
    Retourne le nom canonique d'un thème ou un slug standardisé.
    Idempotent vis-à-vis du préfixe 'theses-' (PBI-073 Correction).
    """
    raw_name = theme_name.lower().strip()

    # Suppression du préfixe technique si présent
    if raw_name.startswith("theses-"):
        raw_name = raw_name.replace("theses-", "", 1)

    # 1. Vérifier si c'est un alias connu
    if raw_name in CANONICAL_THEMES:
        return CANONICAL_THEMES[raw_name]

    # 2. Sinon, retourner un slug standardisé
    return raw_name.replace(" ", "-")


def setup_settings():
    """
    Initialise les paramètres globaux de LlamaIndex (LLM et Embeddings).
    Charge les variables d'environnement depuis le fichier .env.
    Gère la robustesse technique (Secrets manquants).
    """
    # 1. Charger les variables d'environnement
    load_dotenv()

    # 2. Robustesse Chainlit (PBI-051 Fix)
    if not os.getenv("CHAINLIT_AUTH_SECRET"):
        logger.warning(
            "⚠️  CHAINLIT_AUTH_SECRET non trouvé dans l'environnement. "
            "Utilisation d'un secret de développement par défaut. "
            "Pour la production, lancez 'chainlit create-secret' et ajoutez-le au .env"
        )
        # On injecte une valeur par défaut pour éviter le crash au démarrage
        os.environ["CHAINLIT_AUTH_SECRET"] = "dev-secret-change-me-in-production-12345"

    # 3. Vérifier la présence de la clé API OpenAI
    has_openai_key = bool(os.getenv("OPENAI_API_KEY"))

    # Si pas de clé, on force le mode test pour utiliser des Mocks
    if not has_openai_key:
        if os.getenv("IS_TESTING") != "1":
            logger.info(
                "OPENAI_API_KEY non trouvée. Basculement en mode Mock (IS_TESTING=1)."
            )
            os.environ["IS_TESTING"] = "1"

    # 3. Configuration du LLM
    use_local_llm = os.getenv("USE_LOCAL_LLM") == "1"

    try:
        if use_local_llm:
            model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
            logger.info(f"Activation du LLM local (Ollama) : {model}")
            Settings.llm = get_ollama_llm(model=model)
        elif has_openai_key:
            Settings.llm = llama_index.llms.openai.OpenAI(model="gpt-4o-mini")
        else:
            Settings.llm = MockLLM()
    except Exception as e:
        logger.warning(
            f"Erreur lors de l'initialisation du LLM : {e}. Utilisation de MockLLM."
        )
        Settings.llm = MockLLM()

    # 4. Configuration de l'Embedding Model
    try:
        if has_openai_key:
            Settings.embed_model = llama_index.embeddings.openai.OpenAIEmbedding(
                model="text-embedding-3-small"
            )
        else:
            Settings.embed_model = MockEmbedding(embed_dim=1536)
    except Exception as e:
        logger.warning(
            f"Erreur lors de l'initialisation de l'Embedding OpenAI : {e}. Utilisation de MockEmbedding."
        )
        Settings.embed_model = MockEmbedding(embed_dim=1536)

    logger.info(
        f"LlamaIndex Settings initialisés (LLM: {type(Settings.llm).__name__}, Embed: {type(Settings.embed_model).__name__})"
    )


def get_ollama_llm(model: str = "llama3.2:3b"):
    """
    Retourne une instance de LLM Ollama pour les tâches locales (PBI-079).
    """
    base_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    return llama_index.llms.ollama.Ollama(
        model=model, base_url=base_url, request_timeout=120.0
    )
