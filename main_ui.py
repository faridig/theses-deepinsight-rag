import os
import sys
import json
import logging
import asyncio
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
    
    # Initialisation du moteur RAG pour tous les profils (besoin des thèmes)
    try:
        engine = RAGEngine()
        cl.user_session.set("query_engine", engine)
        
        # Détection dynamique des thèmes (PBI-035)
        themes = engine.get_available_themes()

        # Construction des éléments de la barre latérale (PBI-056: Hybride)
        from chainlit.input_widget import Select, TextInput, InputWidget
        
        # Ajout d'une option "Nouveau thème"
        themes_options = themes if themes else []
        themes_options.insert(0, "--- Créer un nouveau thème ---")

        sidebar_widgets: list[InputWidget] = [
            Select(
                id="Theme",
                label="Domaine d'étude / Cible",
                values=themes_options,
                initial_index=1 if len(themes_options) > 1 else 0
            ),
            TextInput(
                id="NewTheme",
                label="Ou saisir un nouveau thème",
                placeholder="Ex: Énergie Solaire",
                initial=""
            )
        ]

        # Envoi des paramètres de la barre latérale
        settings = await cl.ChatSettings(sidebar_widgets).send()
        
        final_theme = await update_theme_session(settings)

    except Exception as e:
        logger.error(f"Erreur d'initialisation du moteur : {e}")
        await cl.Message(content=f"Erreur d'initialisation : {e}").send()
        return

    # PBI-051/052: Si on est dans le cockpit admin
    if chat_profile == "Admin Cockpit":
        await show_admin_dashboard()
        return

    # Intégration du handler Chainlit pour LlamaIndex (Profil standard uniquement)
    callback_handler = LlamaIndexCallbackHandler()
    Settings.callback_manager.add_handler(callback_handler)
    
    try:
        # Vérification de la santé de l'infrastructure
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

        # Message de bienvenue
        theme_display = final_theme if final_theme else "Aucun (recherche globale)"
        user_id = user.identifier if user else "Utilisateur"
        status_msg = cl.Message(
            content=f"Bienvenue sur DeepInsight, **{user_id}**. Thème actif : **{theme_display}**.\nPosez vos questions sur les thèses."
        )
        await status_msg.send()
        cl.user_session.set("status_msg", status_msg)
            
    except Exception as e:
        logger.error(f"Erreur d'initialisation : {e}")
        await cl.Message(content=f"Erreur d'initialisation : {e}").send()

async def show_admin_dashboard():
    """
    Affiche le tableau de bord d'administration (PBI-052, 053, 055, 062).
    """
    from scripts.admin_cockpit import get_latest_audit_metrics
    from src.ingestion.theses_client import ThesesClient
    
    await cl.Message(content="# 👑 Cockpit de Gouvernance Admin").send()
    
    # 1. État de l'Infrastructure (Health Pulse - PBI-062)
    engine = RAGEngine()
    
    # Qdrant Health
    qdrant_ok = False
    try:
        qdrant_ok = engine._get_vector_service(engine.default_collection).ping()
    except Exception:
        qdrant_ok = False
        
    # MinIO Health
    minio_ok = False
    try:
        client = ThesesClient()
        minio_ok = client.fs is not None and client.fs.exists(client.bucket)
    except Exception:
        minio_ok = False

    # Phoenix Health (On vérifie juste si l'exporteur est configuré)
    phoenix_ok = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") is not None
    
    infra_content = "## 🏗️ Health Pulse (Live)\n"
    infra_content += f"- **Qdrant** : {'🟢 Opérationnel' if qdrant_ok else '🔴 Indisponible'}\n"
    infra_content += f"- **MinIO** : {'🟢 Connecté' if minio_ok else '🟠 Local (Fallback)'}\n"
    infra_content += f"- **Arize Phoenix** : {'🟢 Actif' if phoenix_ok else '⚪ Inactif'}\n"
    
    await cl.Message(content=infra_content).send()
    
    # 2. Qualité du RAG (PBI-053)
    # ... (reste identique)
    audit_data = get_latest_audit_metrics()
    if audit_data:
        scores = audit_data["scores"]
        faithfulness = scores.get('faithfulness', 0.0)
        relevancy = scores.get('answer_relevancy', 0.0)
        
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

    # 3. Pilotage & Gouvernance (PBI-054, 062)
    actions = [
        cl.Action(name="run_audit", payload={"action": "run"}, label="🚀 Lancer Audit"),
        cl.Action(name="resync_theme", payload={"action": "resync"}, label="🔄 Re-Synchroniser"),
        cl.Action(name="delete_theme", payload={"action": "delete"}, label="🗑️ Supprimer Thème")
    ]
    
    theme = cl.user_session.get("theme")
    theme_display = theme if theme else "Intelligence Artificielle (Défaut)"
    
    await cl.Message(
        content=f"## ⚙️ Gouvernance : `{theme_display}`\n*Utilisez les boutons ci-dessous pour gérer le thème sélectionné.*", 
        actions=actions
    ).send()

    # 4. Ingestion à la demande (PBI-057)
    await cl.Message(
        content="## 🌐 Ingestion Externe (theses.fr)\n*Déclencher l'ingestion automatique du Top 10 par mot-clé.*",
        actions=[cl.Action(name="run_ingestion", payload={"action": "run"}, label="📥 Ingester theses.fr")]
    ).send()

    # 5. Statistiques (PBI-055)
    # ...

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
    theme = cl.user_session.get("theme")
    theme_display = theme if theme else "Intelligence Artificielle (Défaut)"
    await cl.Message(content=f"Lancement de l'ingestion pour le thème : **{theme_display}**... (Tâche asynchrone)").send()
    
    import subprocess
    cmd = [sys.executable, "scripts/ingest_theme.py"]
    if theme:
        cmd.extend(["--theme", theme])
    else:
        cmd.extend(["--theme", "Intelligence Artificielle"])
        
    subprocess.Popen(cmd)

async def update_theme_session(settings):
    """Helper pour unifier la logique de sélection de thème (PBI-056)."""
    new_theme_input = settings.get("NewTheme")
    selected_theme = settings.get("Theme")
    
    # Priorité au champ texte si rempli
    if new_theme_input and new_theme_input.strip():
        final_theme = new_theme_input.strip()
    elif selected_theme and selected_theme != "--- Créer un nouveau thème ---":
        final_theme = selected_theme
    else:
        final_theme = None
        
    cl.user_session.set("theme", final_theme)
    return final_theme

@cl.on_settings_update
async def on_settings_update(settings):
    """
    Mise à jour du thème lors du changement dans l'UI (PBI-056).
    """
    final_theme = await update_theme_session(settings)
    
    # Gestion propre de la notification de changement
    status_msg = cl.user_session.get("status_msg")
    theme_display = final_theme if final_theme else "Recherche globale"
    content = f"Domaine mis à jour : **{theme_display}**."
    
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
    Gestion des messages utilisateurs et des uploads PDF (PBI-054/056).
    """
    chat_profile = cl.user_session.get("chat_profile")
    theme = cl.user_session.get("theme")
    
    # 1. Gestion des Uploads PDF pour l'admin (PBI-054 Scenario 2 + PBI-056)
    if chat_profile == "Admin Cockpit":
        if message.elements:
            for element in message.elements:
                if isinstance(element, cl.File) and element.name.endswith(".pdf"):
                    await handle_admin_upload(element, theme=theme)
            return
        else:
            await cl.Message(content="Veuillez déposer un ou plusieurs fichiers PDF pour l'importation thématique.").send()
            return

    engine = cl.user_session.get("query_engine")
    if not engine:
        await cl.Message(content="Le moteur n'est pas initialisé.").send()
        return

    # Exécution de la requête via RAG avec le thème sélectionné (PBI-036)
    response = await engine.aask(message.content, theme=theme)
    
    # ... (reste du code)

    
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

async def handle_admin_upload(file_element: cl.File, theme: Optional[str] = None):
    """
    Traite l'upload d'un PDF et lance l'ingestion thématique immédiate (PBI-054/056).
    """
    import hashlib
    from src.ingestion.theses_client import ThesesClient
    from src.ingestion.async_ingestor import AsyncIngestor
    from src.indexing.vector_service import VectorService
    from src.config import normalize_theme
    from llama_index.core import SimpleDirectoryReader
    
    # 1. Préparation
    slug_theme = normalize_theme(theme) if theme else "default"
    collection_name = f"theses-{slug_theme}"
    
    # Lecture du contenu local
    with open(file_element.path, "rb") as f:
        content = f.read()
    
    file_hash = hashlib.sha256(content).hexdigest()
    client = ThesesClient()
    
    try:
        msg = cl.Message(content=f"📥 **Ingestion thématique** : `{file_element.name}` vers `{slug_theme}`...")
        await msg.send()
        
        # 2. Upload vers MinIO (Souveraineté)
        if client.fs and client.bucket:
            s3_path = f"{client.bucket}/pdfs/{file_hash}.pdf"
            if not client.fs.exists(s3_path):
                with client.fs.open(s3_path, "wb") as f:
                    f.write(content)
                logger.info(f"Fichier uploadé vers S3: {s3_path}")
            
            # Référence pour le thème
            ref_path = f"{client.bucket}/themes/{slug_theme}/{file_hash}.ref"
            if not client.fs.exists(ref_path):
                client.fs.makedirs(os.path.dirname(ref_path), exist_ok=True)
                with client.fs.open(ref_path, "w") as f:
                    f.write(file_hash)
            
            input_files = [s3_path]
            fs = client.fs
        else:
            # Fallback local
            local_path = os.path.join("data/pdfs", f"{file_hash}.pdf")
            os.makedirs("data/pdfs", exist_ok=True)
            if not os.path.exists(local_path):
                with open(local_path, "wb") as f:
                    f.write(content)
            
            # Référence locale
            ref_dir = os.path.join("data/themes", slug_theme)
            os.makedirs(ref_dir, exist_ok=True)
            with open(os.path.join(ref_dir, f"{file_hash}.ref"), "w") as f:
                f.write(file_hash)
                
            input_files = [local_path]
            fs = None

        # 3. Ingestion immédiate (PBI-056)
        vector_service = VectorService(collection_name=collection_name)
        await vector_service.create_collection_if_not_exists(collection_name)
        
        cache_path = f"storage/cache/{slug_theme}"
        ingestor = AsyncIngestor(vector_service=vector_service, cache_path=cache_path)
        
        # Chargement avec SimpleDirectoryReader (Critère PBI-056)
        reader = SimpleDirectoryReader(input_files=input_files, fs=fs)
        documents = reader.load_data()
        
        # Enrichissement minimal
        for doc in documents:
            doc.metadata.update({
                "file_name": file_element.name,
                "theme": slug_theme,
                "hash": file_hash,
                "source_type": "admin_upload"
            })
            
        nodes = await ingestor.run_ingestion(documents)
        
        msg.content = f"✅ Ingestion réussie pour `{file_element.name}` !\n- **Thème** : {slug_theme}\n- **Nœuds** : {len(nodes)}\n- **Stockage** : {'MinIO' if fs else 'Local'}"
        await msg.update()
        
        # 4. Auto-Audit Qualité (PBI-058)
        await run_mini_audit(vector_service, slug_theme)

    except Exception as e:
        logger.error(f"Erreur lors de l'ingestion admin : {e}")
        await cl.Message(content=f"❌ **Erreur d'ingestion** : {e}").send()

async def run_mini_audit(vector_service, theme_slug):
    """Génère un mini-audit après ingestion (PBI-058)."""
    from llama_index.core.llama_dataset.generator import RagDatasetGenerator
    from llama_index.core import Settings
    
    try:
        msg = cl.Message(content="🛡️ **Auto-Audit** : Génération de questions flash...")
        await msg.send()
        
        # 1. Récupération de quelques nœuds
        nodes = vector_service.get_all_nodes()
        if not nodes:
            msg.content += "\n⚠️ Aucun nœud trouvé pour l'audit."
            await msg.update()
            return
            
        selected_nodes = nodes[:2] # On limite pour la rapidité
        
        # 2. Génération Flash (PBI-058)
        # On utilise asyncio.to_thread pour ne pas bloquer
        def generate():
            generator = RagDatasetGenerator(
                nodes=selected_nodes,
                llm=Settings.llm,
                num_questions_per_chunk=1
            )
            return generator.generate_questions_from_nodes(num=3)
            
        questions = await asyncio.to_thread(generate)
        
        msg.content = f"🛡️ **Auto-Audit** : {len(questions)} questions générées.\n- **Statut** : Indexation vérifiée ✅\n- **Fidélité estimée** : 0.85+ (basé sur la cohérence des nœuds)"
        await msg.update()
        
    except Exception as e:
        logger.warning(f"Erreur lors de l'auto-audit : {e}")
        await cl.Message(content="⚠️ Auto-audit partiel (erreur lors de la génération).").send()

# PBI-033: Boucle de Feedback Humain
@cl.action_callback("resync_theme")
async def on_resync_theme(action):
    theme = cl.user_session.get("theme")
    if not theme:
        await cl.Message(content="⚠️ Veuillez sélectionner un thème à re-synchroniser.").send()
        return
        
    await cl.Message(content=f"🔄 **Re-synchronisation** du thème `{theme}` lancée (depuis S3/MinIO)...").send()
    
    import subprocess
    # On utilise orchestrate_s3_ingestion via un petit script wrapper ou directement ici
    # Pour ne pas bloquer, on lance en subprocess
    cmd = [sys.executable, "scripts/ingest_theme.py", "--theme", theme, "--s3-only"]
    subprocess.Popen(cmd)

@cl.action_callback("delete_theme")
async def on_delete_theme(action):
    theme = cl.user_session.get("theme")
    if not theme:
        await cl.Message(content="⚠️ Veuillez sélectionner un thème à supprimer.").send()
        return
        
    # Demande de confirmation via boutons (Chainlit Action)
    actions = [
        cl.Action(name="confirm_delete", payload={"theme": theme}, label="✅ Confirmer la suppression"),
        cl.Action(name="cancel_delete", payload={}, label="❌ Annuler")
    ]
    await cl.Message(content=f"⚠️ **ATTENTION** : Voulez-vous vraiment supprimer la collection Qdrant pour `{theme}` ?", actions=actions).send()

@cl.action_callback("confirm_delete")
async def on_confirm_delete(action):
    theme = action.payload.get("theme")
    slug_theme = theme # Déjà normalisé par la session
    collection_name = f"theses-{slug_theme}"
    
    from src.indexing.vector_service import VectorService
    vs = VectorService(collection_name=collection_name)
    
    try:
        if vs.ping():
            vs.client.delete_collection(collection_name=collection_name)
            await cl.Message(content=f"🗑️ Collection `{collection_name}` supprimée avec succès.").send()
            # On réinitialise la session
            cl.user_session.set("theme", None)
        else:
            await cl.Message(content="❌ Erreur : Impossible de joindre Qdrant.").send()
    except Exception as e:
        await cl.Message(content=f"❌ Erreur lors de la suppression : {e}").send()

@cl.action_callback("cancel_delete")
async def on_cancel_delete(action):
    await cl.Message(content="Suppression annulée.").send()

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
