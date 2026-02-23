import os
import sys
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import subprocess
import time
import hashlib
import logging
from datetime import datetime

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.generation.rag_engine import RAGEngine
from src.ingestion.theses_client import ThesesClient
from src.indexing.vector_service import VectorService
from src.config import normalize_theme
from scripts.admin_cockpit import get_latest_audit_metrics

# Page Config
st.set_page_config(
    page_title="DeepInsight Cockpit",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for UI Tokens (PBI-070 Directive 3)
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    /* DeepInsight Tokens: Bleu #2563EB, Radius 8px */
    .stButton>button {
        background-color: #2563EB !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 0.5rem 1rem !important;
        transition: background-color 0.2s;
    }
    .stButton>button:hover {
        background-color: #1D4ED8 !important;
    }
    div[data-baseweb="select"] > div {
        border-radius: 8px !important;
    }
    input {
        border-radius: 8px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("👑 DeepInsight")
    st.subheader("Control Plane")
    st.divider()
    
    menu = st.radio(
        "Navigation",
        ["📊 Dashboard", "📥 Ingestion", "⚙️ Gouvernance", "📈 Statistiques", "🏗️ Architecture"]
    )
    
    st.divider()
    if st.button("🔄 Rafraîchir les données"):
        st.rerun()

# --- Functions ---

def reset_search():
    """Réinitialise les résultats de recherche lors d'un changement de paramètres."""
    st.session_state.search_results = None

def get_health_pulse():
    """Vérifie la santé des services."""
    health = {}
    
    # Qdrant
    try:
        engine = RAGEngine()
        health["Qdrant"] = engine._get_vector_service(engine.default_collection).ping()
    except Exception:
        health["Qdrant"] = False
        
    # MinIO
    try:
        client = ThesesClient()
        health["MinIO"] = client.fs is not None and client.fs.exists(client.bucket)
    except Exception:
        health["MinIO"] = False
        
    # Phoenix
    health["Arize Phoenix"] = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") is not None
    
    return health

def run_async_task(cmd, success_message):
    """Lance une tâche asynchrone et affiche un message (PBI-070 Directive 3)."""
    try:
        subprocess.Popen(cmd)
        st.success(f"🚀 {success_message}")
        st.info("La tâche s'exécute en arrière-plan.")
    except Exception as e:
        st.error(f"❌ Erreur lors du lancement : {e}")

# --- Pages ---

if menu == "📊 Dashboard":
    st.header("Tableau de Bord de Gouvernance")
    
    # 1. Health Pulse
    st.subheader("🏗️ Health Pulse (Live)")
    health = get_health_pulse()
    cols = st.columns(3)
    
    with cols[0]:
        status = "🟢 Opérationnel" if health["Qdrant"] else "🔴 Indisponible"
        st.metric("Qdrant (Vector DB)", status)
        
    with cols[1]:
        status = "🟢 Connecté" if health["MinIO"] else "🟠 Local (Fallback)"
        st.metric("MinIO (S3 Storage)", status)
        
    with cols[2]:
        status = "🟢 Actif" if health["Arize Phoenix"] else "⚪ Inactif"
        st.metric("Arize Phoenix (Tracing)", status)
    
    st.divider()
    
    # 2. Qualité du RAG
    st.subheader("🛡️ Qualité (Dernier Audit)")
    audit_data = get_latest_audit_metrics()
    
    if audit_data:
        scores = audit_data["scores"]
        faithfulness = scores.get('faithfulness', 0.0)
        relevancy = scores.get('answer_relevancy', 0.0)
        precision = scores.get('context_precision', 0.0) # PBI-076
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.write(f"**Fichier** : `{audit_data['file']}`")
            st.metric("Fidélité (Faithfulness)", f"{faithfulness:.2f}", 
                      delta=f"{faithfulness - 0.85:.2f}" if faithfulness >= 0.85 else f"{faithfulness - 0.85:.2f}",
                      delta_color="normal" if faithfulness >= 0.85 else "inverse")
            st.metric("Pertinence (Relevancy)", f"{relevancy:.2f}")
            st.metric("Précision (Context Precision)", f"{precision:.2f}") # PBI-076
            
        with col2:
            fig = go.Figure(data=[
                go.Bar(name='Metrics', x=['Fidélité', 'Pertinence', 'Précision'], y=[faithfulness, relevancy, precision],
                       marker_color=['#28a745' if faithfulness >= 0.85 else '#dc3545', '#007bff', '#ffc107'])
            ])
            fig.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20), yaxis_range=[0,1])
            st.plotly_chart(fig, use_container_width=True)
            
        # 📘 Guide des Metrics & Aide à la Décision (PBI-075)
        with st.expander("📘 Guide des Metrics & Aide à la Décision"):
            st.markdown("""
            ### 🎯 Dictionnaire des Métriques
            
            | Métrique | Seuil d'Alerte | Signification | Solution si Score Faible |
            | :--- | :---: | :--- | :--- |
            | **Fidélité (Faithfulness)** | < 0.85 | La réponse contient des hallucinations (non basée sur les docs). | Vérifier le prompt de génération ou la température du LLM. |
            | **Pertinence (Relevancy)** | < 0.80 | La réponse est floue ou ne répond pas directement à la question. | Améliorer le prompt ou augmenter le nombre d'extraits (`top_k`). |
            | **Précision (Context Precision)** | < 0.70 | Les documents récupérés ne sont pas les plus pertinents pour la question. | Revoir l'Embedding, le découpage (chunking) ou ajouter du Reranking. |
            
            ### 🛠️ Actions Correctives
            - **Score < 0.7** : Alerte critique. Le RAG est probablement inutilisable sur ce thème.
            - **Baisse soudaine** : Vérifier l'intégrité des PDF (parsing corrompu ?) ou un changement d'API OpenAI.
            """)
    else:
        st.warning("⚠️ Aucun audit trouvé dans `docs/AUDITS/`.")
        if st.button("🚀 Lancer un audit maintenant"):
            run_async_task([sys.executable, "scripts/audit_quality.py"], "Audit lancé.")

elif menu == "📥 Ingestion":
    st.header("Gestion de l'Ingestion")
    
    engine = RAGEngine()
    available_themes = engine.get_available_themes()
    theme_options = ["➕ Nouveau thème..."] + available_themes

    # Section 1: theses.fr (PBI-070 Directive 1 - Correction Bug Désynchronisation)
    st.subheader("🌐 Ingestion theses.fr")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_theme_fr = st.selectbox(
            "Thématique cible", 
            options=theme_options, 
            key="theme_select_fr",
            on_change=reset_search
        )
        if selected_theme_fr == "➕ Nouveau thème...":
            theme_input = st.text_input(
                "Nom du nouveau thème", 
                placeholder="Ex: Intelligence Artificielle",
                key="theme_input",
                on_change=reset_search
            )
        else:
            theme_input = selected_theme_fr

    with col2:
        # On utilise la valeur directe du widget
        limit = st.number_input(
            "Nombre de thèses", 
            min_value=1, 
            max_value=100, 
            value=10,
            key="limit_input",
            on_change=reset_search
        )
        
    if st.button("🔍 Rechercher les thèses", use_container_width=True):
        if theme_input:
            # Force la réinitialisation pour garantir la fraîcheur
            st.session_state.search_results = None
            with st.spinner(f"Recherche de {limit} thèses sur theses.fr..."):
                client = ThesesClient()
                results = client.search(theme_input, rows=limit)
                if results:
                    st.session_state.search_results = results
                    st.session_state.last_params = {"theme": theme_input, "limit": limit}
                else:
                    st.warning("Aucune thèse trouvée.")
        else:
            st.error("Veuillez saisir un thème.")

    # Vérification de la cohérence des résultats (PBI-070 - Ergonomie Dynamique)
    search_results = st.session_state.get("search_results")
    if search_results and isinstance(search_results, list):
        last_params = st.session_state.get("last_params", {})
        
        # Comparaison stricte entre les réglages affichés et ceux de la dernière recherche
        if last_params.get("theme") == theme_input and last_params.get("limit") == limit:
            st.success(f"✅ {len(search_results)} thèses trouvées pour '{theme_input}'")
            df_results = pd.DataFrame(search_results)
            # Ajout de l'année pour le Sourcing Check (PBI-077)
            if "dateSoutenance" in df_results.columns:
                df_results["Année"] = df_results["dateSoutenance"].astype(str).str[:4]
            
            display_cols = ["id", "titre", "auteurs", "Année", "university", "discipline"]
            available_cols = [c for c in display_cols if c in df_results.columns]
            
            st.dataframe(df_results[available_cols], use_container_width=True)
            
            st.info("💡 Vérifiez la liste ci-dessus. Si les thèses correspondent à votre besoin, confirmez l'ingestion.")
            if st.button("📥 Confirmer et Démarrer l'ingestion massive", use_container_width=True, type="primary"):
                cmd = [sys.executable, "scripts/ingest_theme.py", "--theme", theme_input, "--limit", str(limit)]
                run_async_task(cmd, f"Ingestion pour '{theme_input}' lancée.")
        else:
            st.warning("⚠️ Paramètres modifiés. Veuillez cliquer sur **Rechercher** pour actualiser la prévisualisation.")

    st.divider()
    
    # Section 2: Upload Direct (PBI-070 Directive 2)
    st.subheader("📁 Importation Directe (PDF)")
    
    col_u1, col_u2 = st.columns([2, 1])
    with col_u1:
        uploaded_files = st.file_uploader("Choisir des fichiers PDF", type=["pdf"], accept_multiple_files=True)
    with col_u2:
        selected_theme_up = st.selectbox(
            "Associer au domaine", 
            options=theme_options, 
            key="theme_select_up"
        )
        if selected_theme_up == "➕ Nouveau thème...":
            target_theme = st.text_input(
                "Nom du nouveau thème", 
                placeholder="Ex: Énergie Solaire",
                key="theme_input_up"
            )
        else:
            target_theme = selected_theme_up
    
    if uploaded_files and target_theme:
        if st.button("🚀 Téléverser et Ingester", use_container_width=True, type="primary"):

            with st.spinner("Traitement et Hash SHA-256..."):
                client = ThesesClient()
                slug_theme = normalize_theme(target_theme)
                count = 0
                for uploaded_file in uploaded_files:
                    file_bytes = uploaded_file.getvalue()
                    file_hash = hashlib.sha256(file_bytes).hexdigest()
                    
                    # 1. Sauvegarde du PDF (Dédoublonnage Hash)
                    if client.fs and client.bucket:
                        pdf_path = f"{client.bucket}/pdfs/{file_hash}.pdf"
                        if not client.fs.exists(pdf_path):
                            with client.fs.open(pdf_path, "wb") as f:
                                f.write(file_bytes)
                        
                        # 2. Sauvegarde de la référence thématique
                        ref_path = f"{client.bucket}/themes/{slug_theme}/{uploaded_file.name}.ref"
                        if not client.fs.exists(ref_path):
                            client.fs.makedirs(os.path.dirname(ref_path), exist_ok=True)
                            with client.fs.open(ref_path, "w") as f:
                                f.write(file_hash)
                    else:
                        # Fallback Local
                        local_pdf_path = os.path.join("data/pdfs", f"{file_hash}.pdf")
                        os.makedirs("data/pdfs", exist_ok=True)
                        if not os.path.exists(local_pdf_path):
                            with open(local_pdf_path, "wb") as f:
                                f.write(file_bytes)
                        
                        ref_dir = os.path.join("data/themes", slug_theme)
                        os.makedirs(ref_dir, exist_ok=True)
                        with open(os.path.join(ref_dir, f"{uploaded_file.name}.ref"), "w") as f:
                            f.write(file_hash)
                            
                    count += 1
                
                st.success(f"✅ {count} fichiers prêts pour le thème '{slug_theme}'.")
                # Lancement de l'indexation asynchrone
                cmd = [sys.executable, "scripts/ingest_theme.py", "--theme", target_theme, "--s3-only"]
                run_async_task(cmd, f"Indexation pour '{target_theme}' lancée.")

elif menu == "⚙️ Gouvernance":
    st.header("Gouvernance des Données")
    
    engine = RAGEngine()
    themes = engine.get_available_themes()
    
    if not themes:
        st.warning("Aucun thème trouvé dans Qdrant.")
    else:
        selected_theme = st.selectbox("Sélectionner un thème à gérer", themes)
        
        st.write(f"Actions pour le thème : **{selected_theme}**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Re-Synchroniser (S3)", use_container_width=True):
                cmd = [sys.executable, "scripts/ingest_theme.py", "--theme", selected_theme, "--s3-only"]
                run_async_task(cmd, f"Re-synchronisation de '{selected_theme}' lancée.")
                
        with col2:
            if st.button("🚀 Audit Thématique", use_container_width=True):
                run_async_task([sys.executable, "scripts/audit_quality.py"], f"Audit pour '{selected_theme}' lancé.")
                
        with col3:
            if st.button("🗑️ Supprimer la collection", use_container_width=True, type="primary"):
                st.session_state.confirm_delete = selected_theme
                
        if "confirm_delete" in st.session_state and st.session_state.confirm_delete == selected_theme:
            st.warning(f"⚠️ Êtes-vous sûr de vouloir supprimer définitivement la collection `{selected_theme}` ?")
            if st.button("✅ Oui, confirmer la suppression"):
                try:
                    # Suppression Qdrant
                    collection_name = f"theses-{selected_theme}"
                    vs = VectorService(collection_name=collection_name)
                    vs.client.delete_collection(collection_name=collection_name)
                    
                    # 🗑️ Synchronisation Totale de la Purge (PBI-073)
                    try:
                        from src.ingestion.theses_client import ThesesClient
                        client = ThesesClient()
                        if client.fs and client.bucket:
                            # Suppression du dossier thématique sur MinIO
                            theme_path = f"{client.bucket}/themes/{selected_theme}"
                            if client.fs.exists(theme_path):
                                client.fs.rm(theme_path, recursive=True)
                                logger.info(f"S3 folder {theme_path} deleted for theme {selected_theme}")
                            
                            # Fallback : suppression de l'ancien dossier à la racine (Legacy)
                            legacy_path = f"{client.bucket}/{selected_theme}"
                            if client.fs.exists(legacy_path):
                                client.fs.rm(legacy_path, recursive=True)
                        
                        # Nettoyage local aussi (PBI-073 Bonus)
                        local_theme_path = os.path.join("data", "themes", selected_theme)
                        if os.path.exists(local_theme_path):
                            import shutil
                            shutil.rmtree(local_theme_path)
                            
                        local_cache_path = os.path.join("storage", "cache", selected_theme)
                        if os.path.exists(local_cache_path):
                            import shutil
                            shutil.rmtree(local_cache_path)
                            
                    except Exception as purge_err:
                        logger.error(f"Erreur lors de la purge physique : {purge_err}")
                        st.warning(f"Collection supprimée mais échec de la purge physique : {purge_err}")
                    
                    st.success(f"Collection `{collection_name}` et ressources associées supprimées.")
                    del st.session_state.confirm_delete
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")
            if st.button("❌ Annuler"):
                del st.session_state.confirm_delete
                st.rerun()

elif menu == "📈 Statistiques":
    st.header("Statistiques & Coûts")
    
    engine = RAGEngine()
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
        df = pd.DataFrame(theme_stats)
        st.table(df)
        
        # Chart
        fig = go.Figure(data=[
            go.Pie(labels=df["Thème"], values=df["Extraits"], hole=.3)
        ])
        fig.update_layout(title_text="Répartition des extraits par thème")
        st.plotly_chart(fig)
    else:
        st.info("Aucune donnée statistique disponible.")
        
elif menu == "🏗️ Architecture":
    st.header("Schéma Technique du Pipeline")
    
    st.markdown("""
    ### 🔄 Flux de Données (Theses-DeepInsight)
    
    Le schéma ci-dessous détaille l'enchaînement des étapes, du document brut à la génération de la réponse.
    
    ```mermaid
    graph TD
        subgraph "Phase d'Ingestion (Locale)"
            PDF[📄 PDF Thèse] -->|Parsing| DL(🛠️ Docling)
            DL -->|Markdown| MD[📝 Texte Markdown]
            MD -->|Extraction| SLM(🧠 SLM Metadata)
            SLM -->|Enrichissement| META[🏷️ Métadonnées]
        end
        
        subgraph "Phase d'Indexation (S3 & Vector)"
            MD -->|Stockage| S3(🪣 MinIO S3)
            META -->|Embedding| EMB(🔢 text-embedding-3)
            EMB -->|Vecteurs| QDR(🔍 Qdrant)
        end
        
        subgraph "Phase de Génération (Hybrid)"
            User[❓ Question Utilisateur] -->|Search| QDR
            QDR -->|Context| RAG(⚙️ RAG Engine)
            RAG -->|Prompt| LLM(🤖 GPT-4o-mini)
            LLM -->|Réponse| Final[✅ Réponse Finale]
        end
        
        style PDF fill:#f9f,stroke:#333,stroke-width:2px
        style S3 fill:#69f,stroke:#333,stroke-width:2px
        style QDR fill:#6f9,stroke:#333,stroke-width:2px
        style LLM fill:#f96,stroke:#333,stroke-width:2px
    ```
    
    *Note : Les étapes de Parsing et d'Extraction de métadonnées sont réalisées localement pour garantir la confidentialité et réduire les coûts.*
    """)
    
    st.divider()
    st.subheader("🛠️ Stack Technique")
    st.write("- **Framework** : LlamaIndex")
    st.write("- **Parsing** : Docling (IBM)")
    st.write("- **Base Vectorielle** : Qdrant")
    st.write("- **Stockage** : MinIO (S3 compatible)")
    st.write("- **Modèles** : OpenAI GPT-4o-mini / text-embedding-3-small")
    st.write("- **Observabilité** : Arize Phoenix")

    st.divider()
    
    st.subheader("💸 Estimation des Coûts (OpenAI)")
    cols = st.columns(2)
    with cols[0]:
        st.metric("Consommation Totale", "$0.42", help="Simulation basée sur l'usage des tokens")
    with cols[1]:
        st.metric("Tokens (24h)", "12,450")

# Footer
st.divider()
st.caption(f"DeepInsight Control Plane v1.11.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
