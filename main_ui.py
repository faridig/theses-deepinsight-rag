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
        
        # Message de bienvenue personnalisé
        await cl.Message(
            content="Moteur DeepInsight prêt. Posez vos questions sur les thèses."
        ).send()
        
        # Ajout du lien Phoenix dans la barre latérale (PBI-032)
        await cl.Text(
            name="Observabilité",
            content="Accédez aux traces détaillées dans [Arize Phoenix](http://localhost:6006)",
            display="side"
        ).send()
        
        # Dashboard Qualité (PBI-031/032)
        await display_quality_dashboard()
        
    except Exception as e:
        logger.error(f"Erreur d'initialisation : {e}")
        await cl.Message(content=f"Erreur d'initialisation du moteur : {e}").send()

async def display_quality_dashboard():
    """
    Affiche les derniers scores d'audit dans la barre latérale.
    """
    audit_dir = "docs/AUDITS"
    if not os.path.exists(audit_dir):
        return
        
    audit_files = sorted([f for f in os.listdir(audit_dir) if f.startswith("audit_") and f.endswith(".md")], reverse=True)
    if not audit_files:
        return
        
    latest_audit = audit_files[0]
    with open(os.path.join(audit_dir, latest_audit), "r", encoding="utf-8") as f:
        content = f.read()
        
    # Extraction sommaire du tableau des scores
    scores_section = "## Résumé des Scores Ragas\n\n"
    if scores_section in content:
        summary = content.split(scores_section)[1].split("##")[0]
        await cl.Text(
            name="📊 Dashboard Qualité",
            content=f"Dernier Audit ({latest_audit}):\n\n{summary}\n\n*Crash Test = Synthétique*\n*Live = Traces réelles*",
            display="side"
        ).send()

@cl.on_message
async def main(message: cl.Message):
    """
    Gestion des messages utilisateurs.
    """
    engine = cl.user_session.get("query_engine")
    if not engine:
        await cl.Message(content="Le moteur n'est pas initialisé.").send()
        return

    # Message d'attente
    msg = cl.Message(content="")
    
    # Exécution de la requête via RAG
    # Note: On utilise le query_engine interne de RAGEngine pour profiter des callbacks automatiques
    # mais on garde la logique de post-processing de RAGEngine.
    response = await cl.make_async(engine.ask)(message.content)
    
    # Préparation de la réponse
    answer_text = str(response)
    
    # Extraction des sources (PBI-031)
    elements = []
    source_names = []
    
    if hasattr(response, "source_nodes"):
        for i, node in enumerate(response.source_nodes):
            source_id = f"Source {i+1}"
            source_names.append(source_id)
            
            # Contenu du texte source
            content = node.get_content()
            metadata = node.metadata
            
            # Ajout d'un élément texte pour le side panel
            elements.append(
                cl.Text(
                    name=source_id,
                    content=f"**Titre**: {metadata.get('titre', 'N/A')}\n\n**Extrait**:\n{content}",
                    display="side"
                )
            )
            
            # Si on a un lien vers le PDF (Local ou URL)
            # Pour le MVP, on affiche le texte, mais on pourrait ajouter cl.Pdf
    
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
            except:
                feedbacks = []
                
    feedbacks.append(feedback_data)
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(feedbacks, f, indent=4, ensure_ascii=False)
    
    await cl.Message(content="Merci pour votre feedback !").send()
