import os
import sys
import json
import logging
import chainlit as cl
import phoenix as px

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llama_index.core import Settings
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
    # On ajoute le handler de Chainlit au manager existant (qui contient Phoenix)
    # au lieu de tout écraser (PBI-Fix Phoenix Tracing)
    callback_handler = LlamaIndexCallbackHandler()
    Settings.callback_manager.add_handler(callback_handler)
    
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

        # Éléments persistants de la barre latérale (PBI-Fix visibilité)
        obs_element = cl.Text(
            name="Observabilité",
            content="Accédez aux traces détaillées dans [Arize Phoenix](http://localhost:6006)",
            display="side"
        )
        # await obs_element.send()
        await cl.run_sync(obs_element.send(for_id=cl.user_session.get("status_msg").id))
        
        dashboard_element = await get_quality_dashboard_element()
        if dashboard_element:
            # await dashboard_element.send()
            await cl.run_sync(dashboard_element.send(for_id=cl.user_session.get("status_msg").id))
        else:
            # Élément par défaut si pas d'audit
            await cl.Text(
                name="📊 Dashboard Qualité",
                content="Aucun rapport d'audit trouvé dans `docs/AUDITS/`.\nLancez `python scripts/audit_quality.py` pour générer un rapport.",
                display="side"
            )
            # await cl.run_sync(cl.Text(...).send(for_id=cl.user_session.get("status_msg").id))

        # Message de bienvenue
        status_msg = cl.Message(
            content=f"Moteur DeepInsight prêt. Thème actif : **{selected_theme}**.{stats_info}\nPosez vos questions sur les thèses."
        )
        # await status_msg.send()
        await cl.run_sync(status_msg.send())
        cl.user_session.set("status_msg", status_msg)
        
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

    # Gestion propre de la notification de changement (PBI-Review)
    # On utilise un message éphémère ou on met à jour le dernier message de statut
    status_msg = cl.user_session.get("status_msg")
    content = f"Domaine de recherche mis à jour : **{new_theme}**.{stats_info}"
    
    if status_msg:
        status_msg.content = content
        await status_msg.update()
    else:
        new_status_msg = cl.Message(content=content)
        cl.user_session.set("status_msg", new_status_msg)
        await new_status_msg.send()

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
            
        # Extraction robuste du résumé (PBI-Fix)
        # On cherche la section quel que soit le nombre de sauts de ligne
        import re
        match = re.search(r"## Résumé des Scores Ragas\s+(.*?)(?=\n##|$)", content, re.DOTALL)
        if match:
            summary = match.group(1).strip()
            return cl.Text(
                name="📊 Dashboard Qualité",
                content=f"Dernier Audit ({latest_audit}):\n\n{summary}\n\n*Crash Test = Synthétique*\n*Live = Traces réelles*",
                display="side"
            )
        else:
            logger.warning(f"Section 'Résumé des Scores Ragas' non trouvée dans {latest_audit}")
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
    
    # Récupération de l'ID du span Phoenix actuel (pour PBI-033/Phoenix integration)
    # LlamaIndex stocke les IDs dans le callback manager si instrumenté
    # On va tenter de récupérer l'ID de trace pour le lier au message Chainlit
    # Note: En mode asynchrone, le span_id peut être récupéré via openinference
    try:
        from openinference.instrumentation import get_current_span
        span = get_current_span()
        if span and span.get_span_context().is_valid:
            trace_id = span.get_span_context().trace_id
            cl.user_session.set(f"trace_{response.response[:20]}", format(trace_id, '032x'))
    except Exception:
        pass

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

# PBI-033: Boucle de Feedback Humain (Intégration Phoenix)
@cl.on_feedback
async def process_feedback(feedback):
    """
    Stockage des feedbacks utilisateurs dans data/feedbacks.json 
    ET envoi vers Arize Phoenix (PBI-033).
    """
    feedback_data = {
        "message_id": feedback.forId,
        "value": feedback.value, # "thumbs-up" or "thumbs-down"
        "comment": feedback.comment,
        "timestamp": cl.utils.utcnow().isoformat()
    }
    
    logger.info(f"Feedback reçu : {feedback_data}")
    
    # 1. Envoi vers Arize Phoenix
    try:
        px_client = px.Client()
        # Envoi de l'évaluation à Phoenix (Doit être une liste)
        px_client.log_evaluations(
            [
                px.Evaluation(
                    name="Human Feedback",
                    label=feedback.value,
                    score=1 if feedback.value == "thumbs-up" else 0,
                    explanation=feedback.comment or "No comment provided",
                    metadata={"message_id": feedback.forId}
                )
            ]
        )
        logger.info(f"Feedback ({feedback.value}) envoyé à Arize Phoenix")
    except Exception as e:
        logger.warning(f"Échec de l'envoi du feedback à Phoenix : {e}")

    # 2. Stockage local JSON (Sécurité)
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
