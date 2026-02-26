import os
import sys
import logging
from datetime import datetime
import subprocess
import time
import hashlib
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.generation.rag_engine import RAGEngine
from src.ingestion.theses_client import ThesesClient
from src.indexing.vector_service import VectorService
from src.config import normalize_theme
from scripts.admin_cockpit import (
    get_latest_audit_metrics,
    get_all_themes_latest_metrics,
)

# ... (rest of imports)

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page Config
st.set_page_config(
    page_title="DeepInsight Cockpit",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for UI Tokens (PBI-070 Directive 3)
st.markdown(
    """
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
    """,
    unsafe_allow_html=True,
)

# Sidebar
with st.sidebar:
    st.title("👑 DeepInsight")
    st.subheader("Control Plane")
    st.divider()

    menu = st.radio(
        "Navigation",
        [
            "📊 Dashboard",
            "📥 Ingestion",
            "⚙️ Gouvernance",
            "📈 Statistiques",
            "🏗️ Architecture",
        ],
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


def st_mermaid(code: str, height: int = 1200):
    """Rendu d'un diagramme Mermaid dans Streamlit (PBI-078)."""
    html_code = f"""
    <div class="mermaid" style="display: flex; justify-content: center; padding-top: 20px;">
        {code}
    </div>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ 
            startOnLoad: true,
            theme: 'base',
            flowchart: {{ useMaxWidth: false }} ,
            themeVariables: {{
                'primaryColor': '#2563EB',
                'primaryTextColor': '#ffffff',
                'primaryBorderColor': '#1D4ED8',
                'lineColor': '#2563EB',
                'secondaryColor': '#007bff',
                'tertiaryColor': '#ffffff',
                'edgeLabelBackground':'#2563EB',
                'edgeLabelTextColor':'#ffffff',
                'fontFamily': 'Segoe UI, Arial',
                'fontSize': '14px'
            }}
        }});
    </script>
    """
    components.html(html_code, height=height, scrolling=True)


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
        faithfulness = scores.get("faithfulness", 0.0)
        relevancy = scores.get("answer_relevancy", 0.0)
        precision = scores.get("context_precision", 0.0)
        recall = scores.get("context_recall", 0.0)

        col1, col2 = st.columns([1, 2])

        with col1:
            st.write(f"**Thème** : `{audit_data.get('theme', 'default')}`")
            st.metric(
                "Fidélité (Faithfulness)",
                f"{faithfulness:.2f}",
                delta=f"{faithfulness - 0.85:.2f}"
                if faithfulness >= 0.85
                else f"{faithfulness - 0.85:.2f}",
                delta_color="normal" if faithfulness >= 0.85 else "inverse",
            )
            st.metric("Pertinence (Relevancy)", f"{relevancy:.2f}")
            st.metric("Précision (Context Precision)", f"{precision:.2f}")
            st.metric("Rappel (Context Recall)", f"{recall:.2f}")

        with col2:
            fig = go.Figure(
                data=[
                    go.Bar(
                        name="Metrics",
                        x=["Fidélité", "Pertinence", "Précision", "Rappel"],
                        y=[faithfulness, relevancy, precision, recall],
                        marker_color=[
                            "#28a745" if faithfulness >= 0.85 else "#dc3545",
                            "#007bff",
                            "#ffc107",
                            "#e83e8c",
                        ],
                    )
                ]
            )
            fig.update_layout(
                height=350, margin=dict(l=20, r=20, t=20, b=20), yaxis_range=[0, 1]
            )
            st.plotly_chart(fig, use_container_width=True)

    # 3. Global Overview & Benchmarking (PBI-092)
    st.divider()
    st.subheader("📊 Global Overview & Benchmarking")

    all_theme_metrics = get_all_themes_latest_metrics()

    if all_theme_metrics:
        # Préparation des données pour Plotly
        data_bench = []
        for m in all_theme_metrics:
            theme_name = m["theme"]
            sc = m["scores"]
            data_bench.append(
                {
                    "Thème": theme_name,
                    "Fidélité": sc.get("faithfulness", 0.0),
                    "Pertinence": sc.get("answer_relevancy", 0.0),
                    "Précision": sc.get("context_precision", 0.0),
                    "Rappel": sc.get(
                        "context_recall", 0.0
                    ),  # Supposant que recall peut être là
                }
            )

        df_bench = pd.DataFrame(data_bench)

        # Graphique Comparatif Plotly
        fig_bench = go.Figure()
        metrics_to_plot = ["Fidélité", "Pertinence", "Précision", "Rappel"]
        colors = ["#2563EB", "#10B981", "#F59E0B", "#EF4444"]

        for i, metric in enumerate(metrics_to_plot):
            if metric in df_bench.columns:
                fig_bench.add_trace(
                    go.Bar(
                        name=metric,
                        x=df_bench["Thème"],
                        y=df_bench[metric],
                        marker_color=colors[i],
                    )
                )

        fig_bench.update_layout(
            barmode="group",
            height=400,
            xaxis_title="Thématiques",
            yaxis_title="Scores",
            yaxis_range=[0, 1],
            legend_title="Métriques Ragas",
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig_bench, use_container_width=True)

        # Summary Dashboard (PBI-092 Summary)
        col_s1, col_s2 = st.columns(2)

        # Calcul des extrêmes sur la Fidélité par défaut
        if not df_bench.empty:
            best_theme = df_bench.loc[df_bench["Fidélité"].idxmax()]
            worst_theme = df_bench.loc[df_bench["Fidélité"].idxmin()]

            with col_s1:
                st.info(
                    f"🏆 **Thème le plus performant** : `{best_theme['Thème']}` (Fidélité: {best_theme['Fidélité']:.2f})"
                )
            with col_s2:
                alert_color = "🔴" if worst_theme["Fidélité"] < 0.7 else "🟠"
                st.warning(
                    f"{alert_color} **Thème en alerte** : `{worst_theme['Thème']}` (Fidélité: {worst_theme['Fidélité']:.2f})"
                )

        # 4. Interprétation Intelligente (PBI-093)
        st.divider()
        st.subheader("🧠 Interprétation & Conseils")

        # On affiche les conseils pour le dernier audit sélectionné ou le global
        if audit_data:
            faith = audit_data["scores"].get("faithfulness", 0.0)
            prec = audit_data["scores"].get("context_precision", 0.0)

            if faith < 0.4:
                label = "🔴 CRITIQUE - Amélioration du prompt nécessaire"
                st.error(label)
            elif faith < 0.7:
                label = "🟠 ACCEPTABLE - Vérifier la précision du parsing"
                st.warning(label)
            else:
                label = "🟢 EXCELLENT - Prêt pour la production"
                st.success(label)

            with st.expander("📖 Lexique interactif des métriques"):
                st.markdown("""
                - **Fidélité (Faithfulness)** : Mesure si la réponse est uniquement basée sur le contexte fourni. Évite les hallucinations.
                - **Pertinence (Relevancy)** : Mesure si la réponse répond effectivement à la question posée.
                - **Précision (Context Precision)** : Mesure si les extraits les plus utiles sont classés en haut du contexte.
                - **Rappel (Context Recall)** : Mesure si toutes les informations nécessaires pour répondre à la question ont été trouvées dans les documents.
                """)
    else:
        st.info("Lancez des audits sur différents thèmes pour voir la vue comparative.")


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
            on_change=reset_search,
        )
        if selected_theme_fr == "➕ Nouveau thème...":
            theme_input = st.text_input(
                "Nom du nouveau thème",
                placeholder="Ex: Intelligence Artificielle",
                key="theme_input",
                on_change=reset_search,
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
            on_change=reset_search,
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
                    st.session_state.last_params = {
                        "theme": theme_input,
                        "limit": limit,
                    }
                else:
                    st.warning("Aucune thèse trouvée.")
        else:
            st.error("Veuillez saisir un thème.")

    # Vérification de la cohérence des résultats (PBI-070 - Ergonomie Dynamique)
    search_results = st.session_state.get("search_results")
    if search_results and isinstance(search_results, list):
        last_params = st.session_state.get("last_params", {})

        # Comparaison stricte entre les réglages affichés et ceux de la dernière recherche
        if (
            last_params.get("theme") == theme_input
            and last_params.get("limit") == limit
        ):
            st.success(f"✅ {len(search_results)} thèses trouvées pour '{theme_input}'")
            df_results = pd.DataFrame(search_results)
            # Ajout de l'année pour le Sourcing Check (PBI-077)
            if "dateSoutenance" in df_results.columns:
                df_results["Année"] = df_results["dateSoutenance"].astype(str).str[:4]

            display_cols = [
                "id",
                "titre",
                "auteurs",
                "Année",
                "university",
                "discipline",
            ]
            available_cols = [c for c in display_cols if c in df_results.columns]

            st.dataframe(df_results[available_cols], use_container_width=True)

            st.info(
                "💡 Vérifiez la liste ci-dessus. Si les thèses correspondent à votre besoin, confirmez l'ingestion."
            )
            if st.button(
                "📥 Confirmer et Démarrer l'ingestion massive",
                use_container_width=True,
                type="primary",
            ):
                cmd = [
                    sys.executable,
                    "scripts/ingest_theme.py",
                    "--theme",
                    theme_input,
                    "--limit",
                    str(limit),
                ]
                run_async_task(cmd, f"Ingestion pour '{theme_input}' lancée.")
        else:
            st.warning(
                "⚠️ Paramètres modifiés. Veuillez cliquer sur **Rechercher** pour actualiser la prévisualisation."
            )

    st.divider()

    # Section 2: Upload Direct (PBI-070 Directive 2)
    st.subheader("📁 Importation Directe (PDF)")

    col_u1, col_u2 = st.columns([2, 1])
    with col_u1:
        uploaded_files = st.file_uploader(
            "Choisir des fichiers PDF", type=["pdf"], accept_multiple_files=True
        )
    with col_u2:
        selected_theme_up = st.selectbox(
            "Associer au domaine", options=theme_options, key="theme_select_up"
        )
        if selected_theme_up == "➕ Nouveau thème...":
            target_theme = st.text_input(
                "Nom du nouveau thème",
                placeholder="Ex: Énergie Solaire",
                key="theme_input_up",
            )
        else:
            target_theme = selected_theme_up

    if uploaded_files and target_theme:
        if st.button(
            "🚀 Téléverser et Ingester", use_container_width=True, type="primary"
        ):
            with st.spinner("Traitement et Hash SHA-256..."):
                client = ThesesClient()
                slug_theme = normalize_theme(target_theme)
                count = 0
                for uploaded_file in uploaded_files:
                    file_bytes = uploaded_file.getvalue()
                    file_hash = hashlib.sha256(file_bytes).hexdigest()
                    thesis_id = uploaded_file.name.replace(".pdf", "")

                    # 1. Sauvegarde du PDF (Nouvelle Structure Thématique PBI-072)
                    if client.fs and client.bucket:
                        pdf_path = f"{client.bucket}/themes/{slug_theme}/docs/{uploaded_file.name}"
                        if not client.fs.exists(pdf_path):
                            client.fs.makedirs(os.path.dirname(pdf_path), exist_ok=True)
                            with client.fs.open(pdf_path, "wb") as f:
                                f.write(file_bytes)

                        # 2. Sauvegarde de la référence thématique (Hash)
                        ref_path = (
                            f"{client.bucket}/themes/{slug_theme}/{thesis_id}.ref"
                        )
                        if not client.fs.exists(ref_path):
                            client.fs.makedirs(os.path.dirname(ref_path), exist_ok=True)
                            with client.fs.open(ref_path, "w") as f:
                                f.write(file_hash)
                    else:
                        # Fallback Local (Nouvelle Structure PBI-072)
                        local_pdf_dir = os.path.join(
                            "data", "themes", slug_theme, "docs"
                        )
                        os.makedirs(local_pdf_dir, exist_ok=True)
                        local_pdf_path = os.path.join(local_pdf_dir, uploaded_file.name)

                        if not os.path.exists(local_pdf_path):
                            with open(local_pdf_path, "wb") as f:
                                f.write(file_bytes)

                        ref_dir = os.path.join("data", "themes", slug_theme)
                        os.makedirs(ref_dir, exist_ok=True)
                        with open(os.path.join(ref_dir, f"{thesis_id}.ref"), "w") as f:
                            f.write(file_hash)

                    count += 1

                st.success(f"✅ {count} fichiers prêts pour le thème '{slug_theme}'.")
                # Lancement de l'indexation asynchrone
                cmd = [
                    sys.executable,
                    "scripts/ingest_theme.py",
                    "--theme",
                    target_theme,
                    "--s3-only",
                ]
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

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔄 Re-Synchroniser (S3)", use_container_width=True):
                cmd = [
                    sys.executable,
                    "scripts/ingest_theme.py",
                    "--theme",
                    selected_theme,
                    "--s3-only",
                ]
                run_async_task(cmd, f"Re-synchronisation de '{selected_theme}' lancée.")

        with col2:
            if st.button(
                "🗑️ Supprimer la collection", use_container_width=True, type="secondary"
            ):
                st.session_state.confirm_delete = selected_theme

        st.divider()
        st.subheader("🛡️ Audit Qualité (PBI-091)")

        col_a1, col_a2 = st.columns([1, 1])
        with col_a1:
            audit_mode = st.radio(
                "Mode d'audit",
                ["Dataset (Lab)", "Traces (Terrain)"],
                horizontal=True,
                help="Lab: utilise un dataset de vérité. Terrain: utilise les traces réelles de Phoenix.",
            )

        with col_a2:
            # On utilise une clé unique pour éviter les conflits avec d'autres sélecteurs
            selected_theme_audit = st.selectbox(
                "Thème à auditer",
                themes,
                key="audit_theme_sel",
                index=themes.index(selected_theme) if selected_theme in themes else 0,
            )

        if st.button("🏁 Lancer l'Audit", use_container_width=True, type="primary"):
            mode_arg = "lab" if audit_mode == "Dataset (Lab)" else "terrain"
            cmd = [
                sys.executable,
                "scripts/audit_quality.py",
                "--theme",
                selected_theme_audit,
                "--mode",
                mode_arg,
            ]

            with st.status(
                f"Audit {audit_mode} en cours sur '{selected_theme_audit}'...",
                expanded=True,
            ) as status:
                st.write(
                    "Initialisation de l'audit et chargement de l'environnement..."
                )
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )

                # Lecture des logs en temps réel
                for line in process.stdout:
                    clean_line = line.strip()
                    if clean_line:
                        st.write(f"`{clean_line}`")

                process.wait()
                if process.returncode == 0:
                    status.update(
                        label=f"✅ Audit {audit_mode} terminé !",
                        state="complete",
                        expanded=False,
                    )
                    st.success(
                        f"L'audit pour '{selected_theme_audit}' a réussi. Consultez le Dashboard pour les nouveaux scores."
                    )
                else:
                    status.update(
                        label="❌ L'audit a échoué", state="error", expanded=True
                    )
                    st.error(f"Erreur lors de l'audit (code {process.returncode})")

        if (
            "confirm_delete" in st.session_state
            and st.session_state.confirm_delete == selected_theme
        ):
            st.warning(
                f"⚠️ Êtes-vous sûr de vouloir supprimer définitivement la collection `{selected_theme}` ?"
            )
            if st.button("✅ Oui, confirmer la suppression"):
                try:
                    # 🔍 Extraction du slug canonique (PBI-073 Correction)
                    # selected_theme contient déjà le préfixe 'theses-' (ex: 'theses-ia')
                    collection_name = selected_theme
                    slug = normalize_theme(selected_theme)

                    # Suppression Qdrant
                    vs = VectorService(collection_name=collection_name)
                    vs.client.delete_collection(collection_name=collection_name)

                    # 🗑️ Synchronisation Totale de la Purge (PBI-073)
                    try:
                        from src.ingestion.theses_client import ThesesClient

                        client = ThesesClient()
                        if client.fs and client.bucket:
                            # Suppression du dossier thématique sur MinIO (via le slug canonique)
                            theme_path = f"{client.bucket}/themes/{slug}"
                            if client.fs.exists(theme_path):
                                client.fs.rm(theme_path, recursive=True)
                                logger.info(
                                    f"S3 folder {theme_path} deleted for theme {slug}"
                                )

                            # Fallback : suppression de l'ancien dossier (ex: sans prefixe themes/)
                            legacy_path = f"{client.bucket}/{slug}"
                            if client.fs.exists(legacy_path):
                                client.fs.rm(legacy_path, recursive=True)

                            # Fallback 2 : au cas où le dossier S3 utilisait le nom brut du thème
                            raw_slug = selected_theme.replace("theses-", "")
                            if raw_slug != slug:
                                raw_path = f"{client.bucket}/themes/{raw_slug}"
                                if client.fs.exists(raw_path):
                                    client.fs.rm(raw_path, recursive=True)

                        # Nettoyage local aussi (PBI-073 Bonus)
                        local_paths = [
                            os.path.join("data", "themes", slug),
                            os.path.join("storage", "cache", slug),
                            os.path.join(
                                "data", "themes", selected_theme.replace("theses-", "")
                            ),
                            os.path.join(
                                "storage",
                                "cache",
                                selected_theme.replace("theses-", ""),
                            ),
                        ]
                        import shutil

                        for p in local_paths:
                            if os.path.exists(p):
                                shutil.rmtree(p)
                                logger.info(f"Local path {p} deleted")

                    except Exception as purge_err:
                        logger.error(f"Erreur lors de la purge physique : {purge_err}")
                        st.warning(
                            f"Collection supprimée mais échec de la purge physique : {purge_err}"
                        )

                    st.success(
                        f"Collection `{collection_name}` et ressources associées (slug: {slug}) supprimées."
                    )
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
            theme_stats.append(
                {
                    "Thème": theme,
                    "Extraits": stats.get("points_count", 0),
                    "Statut": "Indexé",
                }
            )
        except Exception:
            theme_stats.append({"Thème": theme, "Extraits": 0, "Statut": "Erreur"})

    if theme_stats:
        df = pd.DataFrame(theme_stats)
        st.table(df)

        # Chart
        fig = go.Figure(
            data=[go.Pie(labels=df["Thème"], values=df["Extraits"], hole=0.3)]
        )
        fig.update_layout(title_text="Répartition des extraits par thème")
        st.plotly_chart(fig)
    else:
        st.info("Aucune donnée statistique disponible.")

elif menu == "🏗️ Architecture":
    st.header("Schéma Technique du Pipeline Exhaustif")

    st.markdown("### 🔄 Flux de Données Bout-en-Bout")
    st.write(
        "Visualisation détaillée des trois phases du pipeline : Ingestion, Indexation et Moteur RAG."
    )

    mermaid_code = """
graph TD
    subgraph "1. Ingestion"
        RAW["📄 PDF"] -->|Docling GPU| MD["📝 Markdown"]
        MD -->|SLM| META["🏷️ Métadonnées Enrichies"]
        MD & META -->|Archivage| S3["🪣 MinIO S3"]
    end

    S3 -.-> EMB
    META -.-> EMB
    META -.-> BM25

    subgraph "2. Indexation"
        EMB["🔢 text-embedding-3"] -->|Vecteurs Int8| QDR["🔍 Qdrant"]
        BM25["🗂️ BM25s"]
    end

    QDR -.-> V_RET
    BM25 -.-> T_RET

    subgraph "3. Moteur RAG"
        User["👤 Utilisateur"] -->|Query Expansion| MQ["🔄 Multi-Query"]
        MQ --> V_RET["🔍 Vector Search"] & T_RET["🔍 BM25"]
        V_RET & T_RET -->|RRF Fusion| FUSION["⚖️ Fusion"]
        FUSION --> W_SUB["🪟 Window Substitution"] --> RERANK["💎 Cohere Rerank v3"]
        RERANK --> DIV["🎭 Diversity Filter"] --> LLM["🤖 GPT-4o-mini"]
        LLM --> Final["✅ Réponse Sourcée"]
    end

    %% Styles pour contraste élevé (Texte foncé sur fond clair)
    classDef ingestion fill:#fee2e2,stroke:#ef4444,stroke-width:2px,color:#991b1b;
    classDef indexation fill:#dbeafe,stroke:#3b82f6,stroke-width:2px,color:#1e40af;
    classDef rag fill:#dcfce7,stroke:#22c55e,stroke-width:2px,color:#166534;
    classDef tool fill:#2563eb,stroke:#1e40af,stroke-width:1px,color:#ffffff;

    class RAW,MD,META,S3 ingestion;
    class EMB,QDR,BM25 indexation;
    class MQ,V_RET,T_RET,FUSION,W_SUB,RERANK,DIV,LLM,Final rag;
    class User tool;
"""
    st_mermaid(mermaid_code, height=1600)

    st.info(
        "💡 Ce schéma représente la configuration 'Gold Standard' du pipeline DeepInsight."
    )

    st.divider()
    st.subheader("🛠️ Détails des Composants & Expertise Technique")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 📥 1. Phase d'Ingestion")
        st.info(
            "**Objectif** : Transformer le chaos des PDF en données structurées et enrichies."
        )
        st.markdown("""
        - **IBM Docling (GPU)** : Contrairement aux parseurs classiques, Docling utilise des modèles de vision pour comprendre la mise en page (tableaux complexes, multi-colonnes) et exporte un Markdown fidèle.
        - **Enrichissement SLM (Local)** : Un modèle de langage léger (ex: Phi-3) analyse le texte en local pour extraire :
            - *Entités* : Universités, disciplines, dates clés.
            - *Résumés* : Synthèse sémantique pour booster la recherche.
        - **Archivage MinIO S3** : Sanctuarisation des originaux et des versions Markdown pour une traçabilité totale.
        """)

    with col2:
        st.markdown("### 🗂️ 2. Phase d'Indexation")
        st.info(
            "**Objectif** : Créer des index multi-modaux pour une recherche hybride ultra-rapide."
        )
        st.markdown("""
        - **Embeddings text-embedding-3** : Conversion du texte en vecteurs de 1536 dimensions capturant le sens sémantique profond.
        - **Qdrant (Vecteurs Int8)** : Base vectorielle optimisée par *quantification scalaire*. On réduit la précision des vecteurs de Float32 à Int8, divisant par 4 l'empreinte mémoire sans perte significative de précision.
        - **Index BM25s** : Algorithme de recherche lexicale (mots-clés) implémenté en Python pur pour sa rapidité, idéal pour retrouver des noms propres ou termes techniques exacts.
        """)

    with col3:
        st.markdown("### 🤖 3. Moteur RAG")
        st.info(
            "**Objectif** : Générer une réponse véridique et sourcée à partir du contexte récupéré."
        )
        st.markdown("""
        - **Multi-Query Expansion** : La question est reformulée en 3 variantes pour capturer différents angles d'attaque sémantiques.
        - **Fusion RRF (Reciprocal Rank Fusion)** : Combine les scores du Vector Search et du BM25 pour faire remonter les documents validés par les deux approches.
        - **Post-Processing Avancé** :
            - **Window Substitution** : Remplace les extraits par leur contexte élargi (fenêtre glissante) pour que le LLM comprenne l'environnement de l'information.
            - **Cohere Rerank v3** : Un modèle de cross-encoder ré-évalue la pertinence réelle du Top-K.
            - **Filtre de Diversité** : Élimine les redondances pour maximiser l'information utile.
        - **GPT-4o-mini** : Synthèse finale avec un prompt "Grounding" strict pour interdire l'hallucination.
        """)

    st.divider()

    st.subheader("💸 Estimation des Coûts (OpenAI)")
    cols = st.columns(2)
    with cols[0]:
        st.metric(
            "Consommation Totale",
            "$0.42",
            help="Simulation basée sur l'usage des tokens",
        )
    with cols[1]:
        st.metric("Tokens (24h)", "12,450")

# Footer
st.divider()
st.caption(
    f"DeepInsight Control Plane v1.11.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)
