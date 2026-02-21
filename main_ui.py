import os
import sys
import json
import logging
from typing import Optional
import chainlit as cl
import phoenix as px

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llama_index.core import Settings
from chainlit.llama_index.callbacks import LlamaIndexCallbackHandler

# Configuration du moteur RAG
from src.generation.rag_engine import RAGEngine
from src.config import setup_settings

# Initialisation des paramètres et des variables d'environnement (Fix Bloquant Review)
setup_settings()

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Chainlit-UI")

# Silence technique pour les dépendances bruyantes (PBI-051 Scenario 3)
logging.getLogger("llama_index").setLevel(logging.ERROR)
logging.getLogger("phoenix").setLevel(logging.ERROR)
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)

# PBI-070: Silence UX - On simplifie l'authentification (plus de cockpit admin)
@cl.password_auth_callback
async def auth_callback(username: str, password: str) -> Optional[cl.User]:
    """
    Authentification simplifiée. Tous les utilisateurs ont le rôle USER.
    Le cockpit admin est désormais déporté sur Streamlit (PBI-070).
    """
    return cl.User(identifier=username, metadata={"role": "USER"})

@cl.set_chat_profiles
async def chat_profile(current_user: Optional[cl.User]):
    """
    Seul le profil standard est visible pour l'utilisateur final (PBI-070).
    """
    return [
        cl.ChatProfile(
            name="RAG Assistant",
            markdown_description="Assistant intelligent pour la recherche de thèses.",
            icon="public/logo.png" if os.path.exists("public/logo.png") else None
        )
    ]

@cl.on_chat_start
async def start():
    """
    Initialisation de la session de chat pour l'utilisateur final.
    """
    setup_settings()
    user = cl.user_session.get("user")
    
    try:
        engine = RAGEngine()
        cl.user_session.set("query_engine", engine)
        
        # Détection dynamique des thèmes existants uniquement (PBI-070: Silence UX)
        themes = engine.get_available_themes()

        from chainlit.input_widget import Select, InputWidget
        
        # On ne propose plus de créer un thème depuis l'interface utilisateur
        sidebar_widgets: list[InputWidget] = []
        
        if themes:
            sidebar_widgets.append(
                Select(
                    id="Theme",
                    label="Domaine d'étude",
                    values=themes,
                    initial_index=0
                )
            )
            # Envoi des paramètres de la barre latérale
            settings = await cl.ChatSettings(sidebar_widgets).send()
            final_theme = await update_theme_session(settings)
        else:
            final_theme = None

    except Exception as e:
        logger.error(f"Erreur d'initialisation du moteur : {e}")
        await cl.Message(content="Désolé, une erreur est survenue lors de l'initialisation du service.").send()
        return

    # Intégration du handler Chainlit pour LlamaIndex
    callback_handler = LlamaIndexCallbackHandler()
    Settings.callback_manager.add_handler(callback_handler)
    
    try:
        # Vérification discrète de la santé de l'infrastructure
        svc = engine._get_vector_service(engine.default_collection)
        if not svc.ping():
            logger.error("Infrastructure Qdrant non disponible.")
            await cl.Message(content="Le service de recherche est temporairement indisponible. Veuillez réessayer plus tard.").send()
            return

        # Message de bienvenue épuré
        theme_display = final_theme if final_theme else "Recherche globale"
        user_id = user.identifier if user else "Invité"
        status_msg = cl.Message(
            content=f"Bienvenue **{user_id}**. Thème actif : **{theme_display}**.\nPosez vos questions sur les thèses."
        )
        await status_msg.send()
        cl.user_session.set("status_msg", status_msg)
            
    except Exception as e:
        logger.error(f"Erreur d'initialisation : {e}")

async def update_theme_session(settings):
    """Helper pour mettre à jour le thème sélectionné."""
    selected_theme = settings.get("Theme")
    cl.user_session.set("theme", selected_theme)
    return selected_theme

@cl.on_settings_update
async def on_settings_update(settings):
    """Mise à jour du thème lors du changement dans l'UI."""
    final_theme = await update_theme_session(settings)
    status_msg = cl.user_session.get("status_msg")
    theme_display = final_theme if final_theme else "Recherche globale"
    
    if status_msg:
        status_msg.content = f"Domaine mis à jour : **{theme_display}**."
        await status_msg.update()

@cl.on_message
async def main(message: cl.Message):
    """Gestion des messages utilisateurs (Recherche uniquement)."""
    theme = cl.user_session.get("theme")
    engine = cl.user_session.get("query_engine")
    
    if not engine:
        await cl.Message(content="Le service n'est pas prêt.").send()
        return

    # Exécution de la requête via RAG
    response = await engine.aask(message.content, theme=theme)
    
    # Phoenix Tracing
    try:
        from opentelemetry import trace
        current_span = trace.get_current_span()
        if current_span and current_span.get_span_context().is_valid:
            trace_id = current_span.get_span_context().trace_id
            cl.user_session.set(f"trace_{response.response[:20]}", format(trace_id, '032x'))
    except Exception:
        pass

    # Préparation de la réponse
    answer_text = str(response).split("\n\nSources :")[0]
    
    # Extraction des sources
    elements = []
    source_refs = []
    
    if hasattr(response, "source_nodes"):
        for i, node in enumerate(response.source_nodes):
            source_name = f"Extrait {i+1}"
            source_refs.append(source_name)
            metadata = node.metadata
            title = metadata.get('titre') or metadata.get('file_name') or 'Document'
            author = metadata.get('auteur') or 'Auteur Inconnu'
            
            elements.append(
                cl.Text(
                    name=source_name,
                    content=f"### {title}\n**Auteur**: {author}\n\n---\n\n**Extrait**:\n{node.get_content()}",
                    display="side"
                )
            )
    
    if source_refs:
        answer_text += "\n\n**Sources :** " + ", ".join([f"[{ref}]" for ref in source_refs])
    
    await cl.Message(content=answer_text, elements=elements).send()

@cl.on_feedback
async def process_feedback(feedback):
    """Conservation du feedback utilisateur (PBI-033)."""
    feedback_data = {
        "message_id": feedback.forId,
        "value": feedback.value,
        "comment": feedback.comment,
        "timestamp": cl.utils.utcnow().isoformat()
    }
    
    # Log vers Phoenix
    try:
        px_client = px.Client()
        import pandas as pd
        from phoenix.trace import SpanEvaluations
        eval_df = pd.DataFrame([{
            "span_id": feedback.forId,
            "label": feedback.value,
            "score": 1.0 if feedback.value == "thumbs-up" else 0.0,
            "explanation": feedback.comment or "No comment provided"
        }])
        px_client.log_evaluations(SpanEvaluations(dataframe=eval_df, eval_name="Human Feedback"))
    except Exception as e:
        logger.warning(f"Phoenix feedback failed: {e}")

    # Stockage local
    file_path = "data/feedbacks.json"
    os.makedirs("data", exist_ok=True)
    feedbacks = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                feedbacks = json.load(f)
            except Exception:
                pass
    feedbacks.append(feedback_data)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(feedbacks, f, indent=4, ensure_ascii=False)
    
    await cl.Message(content="Merci pour votre feedback !").send()
