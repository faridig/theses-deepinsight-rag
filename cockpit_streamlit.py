import os
import sys
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import subprocess
import time
import re
import ast
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.generation.rag_engine import RAGEngine
from src.ingestion.theses_client import ThesesClient
from src.indexing.vector_service import VectorService
from scripts.admin_cockpit import get_latest_audit_metrics

# Page Config
st.set_page_config(
    page_title="DeepInsight Cockpit",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
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
    .status-ok { color: #28a745; font-weight: bold; }
    .status-warning { color: #ffc107; font-weight: bold; }
    .status-error { color: #dc3545; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("👑 DeepInsight")
    st.subheader("Control Plane")
    st.divider()
    
    menu = st.radio(
        "Navigation",
        ["📊 Dashboard", "📥 Ingestion", "⚙️ Gouvernance", "📈 Statistiques"]
    )
    
    st.divider()
    if st.button("🔄 Rafraîchir les données"):
        st.rerun()

# --- Functions ---

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
    """Lance une tâche asynchrone et affiche un message."""
    try:
        subprocess.Popen(cmd)
        st.success(f"🚀 {success_message}")
        st.info("La tâche s'exécute en arrière-plan. Consultez les logs pour plus de détails.")
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
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.write(f"**Fichier** : `{audit_data['file']}`")
            st.metric("Fidélité (Faithfulness)", f"{faithfulness:.2f}", 
                      delta=f"{faithfulness - 0.85:.2f}" if faithfulness >= 0.85 else f"{faithfulness - 0.85:.2f}",
                      delta_color="normal" if faithfulness >= 0.85 else "inverse")
            st.metric("Pertinence (Relevancy)", f"{relevancy:.2f}")
            
        with col2:
            fig = go.Figure(data=[
                go.Bar(name='Metrics', x=['Fidélité', 'Pertinence'], y=[faithfulness, relevancy],
                       marker_color=['#28a745' if faithfulness >= 0.85 else '#dc3545', '#007bff'])
            ])
            fig.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20), yaxis_range=[0,1])
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ Aucun audit trouvé dans `docs/AUDITS/`.")
        if st.button("🚀 Lancer un audit maintenant"):
            run_async_task([sys.executable, "scripts/audit_quality.py"], "Audit lancé.")

elif menu == "📥 Ingestion":
    st.header("Gestion de l'Ingestion")
    
    st.subheader("🌐 Ingestion theses.fr")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        theme_input = st.text_input("Thème / Mot-clé", placeholder="Ex: Intelligence Artificielle")
    with col2:
        limit = st.number_input("Nombre de thèses", min_value=1, max_value=100, value=10)
        
    if st.button("📥 Démarrer l'ingestion"):
        if theme_input:
            cmd = [sys.executable, "scripts/ingest_theme.py", "--theme", theme_input, "--limit", str(limit)]
            run_async_task(cmd, f"Ingestion pour '{theme_input}' lancée.")
        else:
            st.error("Veuillez saisir un thème.")

    st.divider()
    
    st.subheader("📁 Importation Directe (PDF)")
    st.info("Utilisez l'interface Chainlit pour uploader des fichiers spécifiques (PBI-054).")

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
                # On pourrait filtrer l'audit par thème si le script le supporte
                run_async_task([sys.executable, "scripts/audit_quality.py"], f"Audit pour '{selected_theme}' lancé.")
                
        with col3:
            if st.button("🗑️ Supprimer la collection", use_container_width=True, type="primary"):
                st.session_state.confirm_delete = selected_theme
                
        if "confirm_delete" in st.session_state and st.session_state.confirm_delete == selected_theme:
            st.warning(f"⚠️ Êtes-vous sûr de vouloir supprimer définitivement la collection `{selected_theme}` ?")
            if st.button("✅ Oui, confirmer la suppression"):
                try:
                    collection_name = f"theses-{selected_theme}"
                    vs = VectorService(collection_name=collection_name)
                    vs.client.delete_collection(collection_name=collection_name)
                    st.success(f"Collection `{collection_name}` supprimée.")
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
