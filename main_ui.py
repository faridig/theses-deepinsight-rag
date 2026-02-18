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

# Initialisation Globale de l'instrumentation Phoenix (Bug Fix)
# Note: L'instrumentation est maintenant configurée dans src/config.py
# via setup_phoenix_instrumentation() qui est appelée par setup_settings()
logging.info("Instrumentation Phoenix configurée via src/config.py")

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
        
        # Vérification de la santé de l'infrastructure (Audit-Fix)
        try:
            svc = engine._get_vector_service(engine.default_collection)
            if not svc.ping():
                logger.error("Infrastructure Qdrant non disponible au démarrage.")
                await cl.Message(
                    content="❌ **ERREUR CRITIQUE** : Le serveur de base de données (Qdrant) est injoignable.\n\n"
                            "L'application nécessite Qdrant pour fonctionner. "
                            "Veuillez démarrer vos services (`docker-compose up -d`) et rafraîchir la page."
                ).send()
                return
        except Exception as e:
            logger.error(f"Erreur lors du ping Qdrant : {e}")
            await cl.Message(content=f"Erreur critique d'infrastructure : {e}").send()
            return

        # Détection dynamique des thèmes (PBI-035)
        themes = engine.get_available_themes()

        # Construction des éléments de la barre latérale
        from chainlit.input_widget import InputWidget
        
        sidebar_widgets: list[InputWidget] = [
            cl.input_widget.Select(
                id="Theme",
                label="Domaine d'étude",
                values=themes if themes else ["Aucun thème disponible"],
                initial_index=0
            )
        ]

        # Envoi des paramètres de la barre latérale
        settings = await cl.ChatSettings(sidebar_widgets).send()
        
        selected_theme = settings.get("Theme")
        if selected_theme == "Aucun thème disponible":
            selected_theme = None
        cl.user_session.set("theme", selected_theme)
        
        # Envoi des éléments d'affichage (Text) via un message unique
        ui_elements = []
        
        # Dashboard qualité
        dashboard_element = await get_quality_dashboard_element()
        if dashboard_element:
            ui_elements.append(dashboard_element)
        else:
            ui_elements.append(cl.Text(
                name="📊 Dashboard Qualité",
                content="Aucun rapport d'audit trouvé dans `docs/AUDITS/`.",
                display="side"
            ))
            
        # Lien d'observabilité
        ui_elements.append(cl.Text(
            name="Observabilité",
            content="Accédez aux traces détaillées dans [Arize Phoenix](http://localhost:6006)",
            display="side"
        ))
        
        # Envoi groupé des éléments side (Fix for_id crash)
        await cl.Message(
            content="Système initialisé.",
            elements=ui_elements,
            author="Système"
        ).send()
        
        # Stats du thème
        stats_info = ""
        if selected_theme:
            stats = engine.get_theme_stats(selected_theme)
            points_count = stats.get('points_count', 0)
            status = stats.get('status', 'unknown')
            
            if points_count == 0:
                if status == 'error':
                    stats_info = f"\n⚠️ **Attention**: La collection '{selected_theme}' est inaccessible ou n'existe pas."
                else:
                    stats_info = f"\n📊 **Statistiques**: {points_count} extraits indexés. (Collection vide)"
            else:
                stats_info = f"\n📊 **Statistiques**: {points_count} extraits indexés."

        # Message de bienvenue (indépendant de la sidebar)
        theme_display = selected_theme if selected_theme else "Aucun (recherche globale)"
        status_msg = cl.Message(
            content=f"Moteur DeepInsight prêt. Thème actif : **{theme_display}**.{stats_info}\nPosez vos questions sur les thèses."
        )
        await status_msg.send()
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
    # Si aucun thème n'est disponible, on utilise une valeur par défaut
    if new_theme == "Aucun thème disponible":
        new_theme = None
    cl.user_session.set("theme", new_theme)
    
    engine = cl.user_session.get("query_engine")
    stats_info = ""
    if engine and new_theme:
        stats = engine.get_theme_stats(new_theme)
        points_count = stats.get('points_count', 0)
        status = stats.get('status', 'unknown')
        
        if points_count == 0:
            if status == 'error':
                stats_info = f"\n⚠️ **Attention**: La collection '{new_theme}' est inaccessible ou n'existe pas."
            else:
                stats_info = f"\n📊 **Statistiques**: {points_count} extraits indexés. (Collection vide)"
        else:
            stats_info = f"\n📊 **Statistiques**: {points_count} extraits indexés."

    # Gestion propre de la notification de changement (PBI-Review)
    # On utilise un message éphémère ou on met à jour le dernier message de statut
    status_msg = cl.user_session.get("status_msg")
    theme_display = new_theme if new_theme else "Aucun (recherche globale)"
    content = f"Domaine de recherche mis à jour : **{theme_display}**.{stats_info}"
    
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
    # Avec OpenInference, on utilise l'API OpenTelemetry standard
    try:
        from opentelemetry import trace
        current_span = trace.get_current_span()
        if current_span and current_span.get_span_context().is_valid:
            trace_id = current_span.get_span_context().trace_id
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
        # Envoi de l'évaluation à Phoenix (API moderne avec SpanEvaluations)
        import pandas as pd
        from phoenix.trace import SpanEvaluations
        
        # Création d'un DataFrame pour l'évaluation
        eval_df = pd.DataFrame([{
            "span_id": feedback.forId,
            "label": feedback.value,
            "score": 1.0 if feedback.value == "thumbs-up" else 0.0,
            "explanation": feedback.comment or "No comment provided",
            "metadata": json.dumps({"message_id": feedback.forId})
        }])
        
        px_client.log_evaluations(
            SpanEvaluations(
                dataframe=eval_df,
                eval_name="Human Feedback"
            )
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
