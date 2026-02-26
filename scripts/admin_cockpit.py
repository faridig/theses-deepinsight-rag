import os
import sys
import logging
import re
import ast

# Configuration des logs - Silence Technique (PBI-050)
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger("AdminCockpit")
logger.setLevel(logging.INFO)

# Silence technique pour les dépendances bruyantes
logging.getLogger("llama_index").setLevel(logging.ERROR)
logging.getLogger("phoenix").setLevel(logging.ERROR)
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("numba").setLevel(logging.ERROR)
logging.getLogger("src").setLevel(
    logging.CRITICAL
)  # Silence presque tout le code source interne

# Ajout du chemin racine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.generation.rag_engine import RAGEngine  # noqa: E402


def get_all_themes_latest_metrics() -> list:
    """Récupère les dernières metrics pour chaque thème trouvé dans les audits."""
    audit_root = "docs/AUDITS"
    if not os.path.exists(audit_root):
        return []

    all_audits = []
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    for entry in os.scandir(audit_root):
        if entry.is_dir() and date_pattern.match(entry.name):
            for f_entry in os.scandir(entry.path):
                if (
                    f_entry.is_file()
                    and f_entry.name.startswith("audit_")
                    and f_entry.name.endswith(".md")
                ):
                    all_audits.append(f_entry.path)

    if not all_audits:
        return []

    # On trie par date descendante pour traiter les plus récents en premier
    all_audits.sort(reverse=True)

    latest_per_theme = {}

    for audit_path in all_audits:
        try:
            with open(audit_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extraction du thème (Accent-insensitive et robuste - Correction Bloquant PBI-091)
            theme_match = re.search(r"\*\*Th[éèe]me\*\* : `(.*?)`", content)
            theme = theme_match.group(1) if theme_match else "default"

            if theme not in latest_per_theme:
                # Regex plus permissive pour Score Global (support des listes et np types)
                global_match = re.search(r"\| (?:Score )?Global \| (.*?) \|", content)
                if global_match:
                    raw_val = global_match.group(1).strip()

                    # Nettoyage pour literal_eval (cas np.float64 et listes)
                    # Remplacement des types numpy par des nombres purs
                    clean_val = re.sub(
                        r"np\.(?:float64|float32|int64|int32)\((.*?)\)", r"\1", raw_val
                    )

                    try:
                        scores_dict = ast.literal_eval(clean_val)
                        # Si c'est une liste de un élément '[{...}]', on prend l'intérieur
                        if isinstance(scores_dict, list) and len(scores_dict) > 0:
                            scores_dict = scores_dict[0]

                        if isinstance(scores_dict, dict):
                            latest_per_theme[theme] = {
                                "theme": theme,
                                "file": os.path.basename(audit_path),
                                "path": audit_path,
                                "scores": scores_dict,
                            }
                    except Exception:
                        continue
        except Exception:
            continue

    return list(latest_per_theme.values())


def get_latest_audit_metrics() -> dict:
    """Compatibilité : Récupère le tout dernier audit global."""
    all_metrics = get_all_themes_latest_metrics()
    if not all_metrics:
        return {}
    return all_metrics[0]


def print_header(title: str):
    print("\n" + "=" * 50)
    print(f" {title.upper()} ".center(50, "="))
    print("=" * 50 + "\n")


def run_cockpit():
    print_header("DeepInsight Admin Cockpit")

    # 1. État de la Qualité (Ragas)
    audit_data = get_latest_audit_metrics()
    print("🛡️  QUALITÉ DU SYSTÈME (RAGAS)")
    if audit_data:
        scores = audit_data["scores"]
        faithfulness = scores.get("faithfulness", 0.0)
        relevancy = scores.get("answer_relevancy", 0.0)
        precision = scores.get("context_precision", 0.0)  # PBI-076

        status_emoji = (
            "✅" if faithfulness >= 0.85 else "⚠️" if faithfulness >= 0.80 else "🚨"
        )

        print(f"Dernier Audit : {audit_data['file']}")
        print(f"Fidélité (Faithfulness)    : {faithfulness:.2f} {status_emoji}")
        print(f"Pertinence (Relevancy)     : {relevancy:.2f}")
        print(
            f"Précision (Context Prec.)  : {precision:.2f} (Gold Standard)"
        )  # PBI-076

        if faithfulness < 0.80:
            print("\n" + "!" * 50)
            print(" ALERTE CRITIQUE : FIDÉLITÉ INFÉRIEURE À 0.80 ".center(50, "!"))
            print("!" * 50 + "\n")
    else:
        print("❌ Aucun audit trouvé dans docs/AUDITS/")

    print("-" * 30)

    # 2. État de l'Infrastructure (Qdrant)
    print("🏗️  INFRASTRUCTURE (QDRANT)")
    try:
        engine = RAGEngine()
        themes = engine.get_available_themes()

        if not themes:
            print("⚠️ Aucune collection trouvée dans Qdrant.")
        else:
            for theme in themes:
                stats = engine.get_theme_stats(theme)
                points = stats.get("points_count", 0)
                print(f"- {theme:.<25}: {points:>6} extraits")

    except Exception as e:
        print(f"🚨 Erreur Infrastructure : {e}")

    print("-" * 30)

    # 3. Liens Utiles
    print("🔗 LIENS D'OBSERVABILITÉ")
    print("- Arize Phoenix : http://localhost:6006")
    print("- MinIO Console : http://localhost:9001")
    print("- Qdrant UI     : http://localhost:6333/dashboard")

    print("\n" + "=" * 50 + "\n")


if __name__ == "__main__":
    run_cockpit()
