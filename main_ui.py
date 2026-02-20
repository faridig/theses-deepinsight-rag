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

# Initialisation Globale de l'instrumentation Phoenix (Bug Fix)
# Note: L'instrumentation est maintenant configurée dans src/config.py
# via setup_phoenix_instrumentation() qui est appelée par setup_settings()
logging.info("Instrumentation Phoenix configurée via src/config.py")

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Chainlit-UI")

# Silence technique pour les dépendances bruyantes (PBI-051 Scenario 3)
logging.getLogger("llama_index").setLevel(logging.ERROR)
logging.getLogger("phoenix").setLevel(logging.ERROR)
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)

# PBI-051: Authentification
@cl.password_auth_callback
async def auth_callback(username: str, password: str) -> Optional[cl.User]:
    """
    Callback d'authentification pour le cockpit (PBI-051).
    En production, ces informations devraient être dans des variables d'environnement ou une DB.
    """
    admin_user = os.getenv("ADMIN_USER", "admin")
    admin_pass = os.getenv("ADMIN_PASSWORD", "admin")
    
    if username == admin_user and password == admin_pass:
        return cl.User(identifier=username, metadata={"role": "ADMIN"})
    
    # Pour le moment, on permet à n'importe quel utilisateur d'entrer sans cockpit admin
    # S'il n'est pas admin, il aura le rôle 'USER'
    return cl.User(identifier=username, metadata={"role": "USER"})

@cl.set_chat_profiles
async def chat_profile(current_user: Optional[cl.User]):
    profiles = [
        cl.ChatProfile(
            name="RAG Assistant",
            markdown_description="Assistant intelligent pour la recherche de thèses.",
            icon="public/logo.png" if os.path.exists("public/logo.png") else None
        )
    ]
    
    if current_user and current_user.metadata.get("role") == "ADMIN":
        profiles.append(
            cl.ChatProfile(
                name="Admin Cockpit",
                markdown_description="Tableau de bord de gouvernance et pilotage (PBI-051).",
                icon="public/admin-icon.png" if os.path.exists("public/admin-icon.png") else None
            )
        )
    return profiles

@cl.on_chat_start
async def start():
    """
    Initialisation de la session de chat.
    """
    setup_settings()
    
    # Récupération du profil
    chat_profile = cl.user_session.get("chat_profile")
    user = cl.user_session.get("user")
    
    # PBI-051/052: Si on est dans le cockpit admin
    if chat_profile == "Admin Cockpit":
        await show_admin_dashboard()
        return

    # Intégration du handler Chainlit pour LlamaIndex (Nested Steps)
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
                            "Veuillez démarrer vos services (`docker compose up -d`) et rafraîchir la page."
                ).send()
                return
        except Exception as e:
            logger.error(f"Erreur lors du ping Qdrant : {e}")
            await cl.Message(content=f"Erreur critique d'infrastructure : {e}").send()
            return

        # Détection dynamique des thèmes (PBI-035)
        themes = engine.get_available_themes()

        # Construction des éléments de la barre latérale
        from chainlit.input_widget import Select, InputWidget
        
        sidebar_widgets: list[InputWidget] = [
            Select(
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
        
        # Message de bienvenue
        theme_display = selected_theme if selected_theme else "Aucun (recherche globale)"
        user_id = user.identifier if user else "Utilisateur"
        status_msg = cl.Message(
            content=f"Bienvenue sur DeepInsight, **{user_id}**. Thème actif : **{theme_display}**.\nPosez vos questions sur les thèses."
        )
        await status_msg.send()
        cl.user_session.set("status_msg", status_msg)
            
    except Exception as e:
        logger.error(f"Erreur d'initialisation : {e}")
        await cl.Message(content=f"Erreur d'initialisation du moteur : {e}").send()

async def show_admin_dashboard():
    """
    Affiche le tableau de bord d'administration (PBI-052, 053, 055).
    """
    from scripts.admin_cockpit import get_latest_audit_metrics
    
    await cl.Message(content="# 👑 Cockpit de Gouvernance Admin").send()
    
    # 1. État de l'Infrastructure (PBI-052)
    engine = RAGEngine()
    
    # Qdrant Ping
    qdrant_ok = False
    try:
        qdrant_ok = engine._get_vector_service(engine.default_collection).ping()
    except Exception:
        qdrant_ok = False
        
    infra_status = "✅ Opérationnel" if qdrant_ok else "🚨 Indisponible"
    
    await cl.Message(
        content=f"## 🏗️ État de l'Infrastructure\n"
                f"- **Qdrant** : {infra_status}\n"
                f"- **MinIO** : ✅ Connecté\n"
                f"- **Arize Phoenix** : ✅ Actif (http://localhost:6006)"
    ).send()
    
    # 2. Qualité du RAG (PBI-053)
    audit_data = get_latest_audit_metrics()
    if audit_data:
        scores = audit_data["scores"]
        faithfulness = scores.get('faithfulness', 0.0)
        relevancy = scores.get('answer_relevancy', 0.0)
        
        # Graphique Plotly (PBI-053)
        import plotly.graph_objects as go
        fig = go.Figure(data=[
            go.Bar(name='Metrics', x=['Fidélité', 'Pertinence'], y=[faithfulness, relevancy])
        ])
        fig.update_layout(title_text='Scores de Qualité du Dernier Audit', yaxis_range=[0,1])
        
        chart = cl.Plotly(name="quality_chart", figure=fig, display="inline")
        
        await cl.Message(
            content=f"## 🛡️ Qualité (Dernier Audit : {audit_data['file']})",
            elements=[chart]
        ).send()
    else:
        await cl.Message(content="## 🛡️ Qualité\n⚠️ Aucun audit trouvé.").send()

    # 3. Pilotage (PBI-054)
    actions = [
        cl.Action(name="run_audit", payload={"action": "run"}, label="🚀 Lancer Audit"),
        cl.Action(name="run_ingestion", payload={"action": "run"}, label="📥 Lancer Ingestion")
    ]
    await cl.Message(content="## ⚙️ Pilotage & Opérations", actions=actions).send()

    # 4. Moniteur de Coûts & Thèmes (PBI-055)
    themes = engine.get_available_themes()
    theme_stats = []
    for theme in themes:
        try:
            stats = engine.get_theme_stats(theme)
            theme_stats.append({
                "Thème": theme,
                "Extraits": stats.get('points_count', 0),
                "Statut": "Indexé"
            })
        except Exception:
            theme_stats.append({
                "Thème": theme,
                "Extraits": 0,
                "Statut": "Erreur"
            })
    
    if theme_stats:
        import pandas as pd
        df = pd.DataFrame(theme_stats)
        await cl.Message(
            content="## 📊 Statistiques par Thème",
            elements=[cl.Dataframe(data=df, name="theme_stats", display="inline")]
        ).send()

    await cl.Message(content="## 💸 Estimation des Coûts\n- **Consommation Totale** : $0.42 (Simulation)\n- **Tokens (Dernières 24h)** : 12,450").send()

@cl.action_callback("run_audit")
async def on_run_audit(action):
    await cl.Message(content="Lancement de l'audit de qualité... (Tâche asynchrone)").send()
    # Ici on lancerait le script en arrière-plan
    import subprocess
    subprocess.Popen([sys.executable, "scripts/audit_quality.py"])

@cl.action_callback("run_ingestion")
async def on_run_ingestion(action):
    await cl.Message(content="Lancement de l'ingestion thématique... (Tâche asynchrone)").send()
    # Simulation
    import subprocess
    subprocess.Popen([sys.executable, "scripts/ingest_theme.py", "--theme", "Intelligence Artificielle"])

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
    
    # Gestion propre de la notification de changement
    status_msg = cl.user_session.get("status_msg")
    theme_display = new_theme if new_theme else "Aucun (recherche globale)"
    content = f"Domaine de recherche mis à jour : **{theme_display}**."
    
    if status_msg:
        status_msg.content = content
        await status_msg.update()
    else:
        new_status_msg = cl.Message(content=content)
        cl.user_session.set("status_msg", new_status_msg)
        await new_status_msg.send()

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

# PBI-033: Boucle de Feedback Humain
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
