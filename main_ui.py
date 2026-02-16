import os
import sys
import json
import logging
import chainlit as cl

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llama_index.core import Settings
from llama_index.core.callbacks import CallbackManager
from chainlit.llama_index.callbacks import LlamaIndexCallbackHandler

# Configuration du moteur RAG
from src.generation.rag_engine import RAGEngine
from src.config import setup_settings

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Chainlit-UI")

@cl.on_chat_start
async def start():
    """
    Initialisation de la session de chat.
    """
    setup_settings()
    
    # Intégration du handler Chainlit pour LlamaIndex (Nested Steps)
    callback_handler = LlamaIndexCallbackHandler()
    Settings.callback_manager = CallbackManager([callback_handler])
    
    try:
        # Initialisation du moteur RAG
        engine = RAGEngine()
        cl.user_session.set("query_engine", engine)
        
        # Détection dynamique des thèmes (PBI-035)
        themes = engine.get_available_themes()
        
        # Configuration des paramètres (PBI-036)
        settings = await cl.ChatSettings([
            cl.input_widget.Select(
                id="Theme",
                label="Domaine d'étude",
                values=themes if themes else ["default"],
                initial_index=0
            ),
        ]).send()
        
        selected_theme = settings.get("Theme")
        cl.user_session.set("theme", selected_theme)
        
        # Stats du thème (PBI-037)
        stats_info = ""
        if selected_theme:
            stats = engine.get_theme_stats(selected_theme)
            stats_info = f"\n📊 **Statistiques**: {stats.get('points_count', 0)} extraits indexés."

        # Éléments de l'interface (PBI-031/032)
        elements = [
            cl.Text(
                name="Observabilité",
                content="Accédez aux traces détaillées dans [Arize Phoenix](http://localhost:6006)",
                display="side"
            )
        ]
        
        # Dashboard Qualité
        dashboard_element = await get_quality_dashboard_element()
        if dashboard_element:
            elements.append(dashboard_element)
            
        # Message de bienvenue personnalisé avec les éléments attachés
        await cl.Message(
            content=f"Moteur DeepInsight prêt. Thème actif : **{selected_theme}**.{stats_info}\nPosez vos questions sur les thèses.",
            elements=elements
        ).send()
        
    except Exception as e:
        logger.error(f"Erreur d'initialisation : {e}")
        await cl.Message(content=f"Erreur d'initialisation du moteur : {e}").send()

@cl.on_settings_update
async def setup_agent(settings):
    """
    Mise à jour du thème lors du changement dans l'UI.
    """
    new_theme = settings.get("Theme")
    cl.user_session.set("theme", new_theme)
    
    engine = cl.user_session.get("query_engine")
    stats_info = ""
    if engine and new_theme:
        stats = engine.get_theme_stats(new_theme)
        stats_info = f"\n📊 **Statistiques**: {stats.get('points_count', 0)} extraits indexés."

    await cl.Message(content=f"Domaine de recherche mis à jour : **{new_theme}**.{stats_info}").send()

async def get_quality_dashboard_element():
    """
    Récupère le dernier rapport d'audit et retourne un élément cl.Text pour l'affichage.
    """
    audit_dir = "docs/AUDITS"
    if not os.path.exists(audit_dir):
        return None
        
    audit_files = sorted([f for f in os.listdir(audit_dir) if f.startswith("audit_") and f.endswith(".md")], reverse=True)
    if not audit_files:
        return None
        
    latest_audit = audit_files[0]
    try:
        with open(os.path.join(audit_dir, latest_audit), "r", encoding="utf-8") as f:
            content = f.read()
            
        # Extraction sommaire du tableau des scores
        scores_section = "## Résumé des Scores Ragas\n\n"
        if scores_section in content:
            summary = content.split(scores_section)[1].split("##")[0]
            return cl.Text(
                name="📊 Dashboard Qualité",
                content=f"Dernier Audit ({latest_audit}):\n\n{summary}\n\n*Crash Test = Synthétique*\n*Live = Traces réelles*",
                display="side"
            )
    except Exception as e:
        logger.warning(f"Erreur lors de la lecture de l'audit : {e}")
        
    return None

@cl.on_message
async def main(message: cl.Message):
    """
    Gestion des messages utilisateurs.
    """
    engine = cl.user_session.get("query_engine")
    theme = cl.user_session.get("theme")
    
    if not engine:
        await cl.Message(content="Le moteur n'est pas initialisé.").send()
        return

    # Exécution de la requête via RAG avec le thème sélectionné (PBI-036)
    response = await engine.aask(message.content, theme=theme)
    
    # Préparation de la réponse (On retire la liste brute des sources car on va utiliser les éléments)
    answer_text = str(response).split("\n\nSources :")[0]
    
    # Extraction des sources (PBI-031)
    elements = []
    source_refs = []
    
    if hasattr(response, "source_nodes"):
        for i, node in enumerate(response.source_nodes):
            source_name = f"Extrait {i+1}"
            source_refs.append(source_name)
            
            # Contenu du texte source
            content = node.get_content()
            metadata = node.metadata
            title = metadata.get('titre') or metadata.get('file_name') or 'Document'
            author = metadata.get('auteur') or 'Auteur Inconnu'
            
            # Ajout d'un élément texte pour le side panel
            elements.append(
                cl.Text(
                    name=source_name,
                    content=f"### {title}\n**Auteur**: {author}\n\n---\n\n**Extrait**:\n{content}",
                    display="side"
                )
            )
    
    if source_refs:
        answer_text += "\n\n**Sources :** " + ", ".join([f"[{ref}]" for ref in source_refs])
    
    # Envoi de la réponse avec les sources
    await cl.Message(
        content=answer_text,
        elements=elements
    ).send()

# PBI-033: Boucle de Feedback Humain
@cl.on_feedback
async def process_feedback(feedback):
    """
    Stockage des feedbacks utilisateurs dans data/feedbacks.json.
    """
    feedback_data = {
        "message_id": feedback.forId,
        "value": feedback.value, # "thumbs-up" or "thumbs-down"
        "comment": feedback.comment,
        "timestamp": cl.utils.utcnow().isoformat()
    }
    
    logger.info(f"Feedback reçu : {feedback_data}")
    
    file_path = "data/feedbacks.json"
    os.makedirs("data", exist_ok=True)
    
    feedbacks = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                feedbacks = json.load(f)
            except Exception:
                feedbacks = []
                
    feedbacks.append(feedback_data)
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(feedbacks, f, indent=4, ensure_ascii=False)
    
    await cl.Message(content="Merci pour votre feedback !").send()
