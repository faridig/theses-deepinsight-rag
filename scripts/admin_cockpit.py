import os
import sys
import logging
import re
import ast

# Configuration des logs - Silence Technique (PBI-050)
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger("AdminCockpit")
logger.setLevel(logging.INFO)

# Silence technique pour les dépendances bruyantes
logging.getLogger("llama_index").setLevel(logging.ERROR)
logging.getLogger("phoenix").setLevel(logging.ERROR)
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("numba").setLevel(logging.ERROR)
logging.getLogger("src").setLevel(logging.CRITICAL) # Silence presque tout le code source interne

# Ajout du chemin racine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.generation.rag_engine import RAGEngine  # noqa: E402

def get_latest_audit_metrics() -> dict:
    """Récupère les dernières metrics d'audit de qualité (hiérarchie YYYY-MM-DD uniquement)."""
    audit_root = "docs/AUDITS"
    if not os.path.exists(audit_root):
        return {}
        
    all_audits = []
    # On cherche uniquement dans les sous-répertoires de type YYYY-MM-DD (Decision PBI-050)
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    
    for entry in os.scandir(audit_root):
        if entry.is_dir() and date_pattern.match(entry.name):
            for f_entry in os.scandir(entry.path):
                if f_entry.is_file() and f_entry.name.startswith("audit_") and f_entry.name.endswith(".md"):
                    all_audits.append(f_entry.path)
    
    if not all_audits:
        return {}
        
    # Le tri alphabétique reverse garantit que la date la plus récente vient en premier
    latest_audit_path = sorted(all_audits, reverse=True)[0]
    
    try:
        with open(latest_audit_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Recherche flexible supportant "| Global |" et "| Score Global |"
        global_match = re.search(r"\| (?:Score )?Global \| (\{.*?\}) \|", content)
        if global_match:
            scores_dict = ast.literal_eval(global_match.group(1))
            return {
                "file": os.path.basename(latest_audit_path),
                "path": latest_audit_path,
                "scores": scores_dict
            }
        else:
            logger.debug(f"Format de scores non trouvé dans {latest_audit_path}")
    except Exception as e:
        logger.warning(f"Erreur lors de la lecture de l'audit {latest_audit_path}: {e}")
    
    return {}

def print_header(title: str):
    print("\n" + "="*50)
    print(f" {title.upper()} ".center(50, "="))
    print("="*50 + "\n")

def run_cockpit():
    print_header("DeepInsight Admin Cockpit")
    
    # 1. État de la Qualité (Ragas)
    audit_data = get_latest_audit_metrics()
    print("🛡️  QUALITÉ DU SYSTÈME (RAGAS)")
    if audit_data:
        scores = audit_data["scores"]
        faithfulness = scores.get('faithfulness', 0.0)
        relevancy = scores.get('answer_relevancy', 0.0)
        
        status_emoji = "✅" if faithfulness >= 0.85 else "⚠️" if faithfulness >= 0.80 else "🚨"
        
        print(f"Dernier Audit : {audit_data['file']}")
        print(f"Fidélité (Faithfulness)    : {faithfulness:.2f} {status_emoji}")
        print(f"Pertinence (Relevancy)     : {relevancy:.2f}")
        
        if faithfulness < 0.80:
            print("\n" + "!"*50)
            print(" ALERTE CRITIQUE : FIDÉLITÉ INFÉRIEURE À 0.80 ".center(50, "!"))
            print("!"*50 + "\n")
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
                points = stats.get('points_count', 0)
                print(f"- {theme:.<25}: {points:>6} extraits")
                
    except Exception as e:
        print(f"🚨 Erreur Infrastructure : {e}")

    print("-" * 30)
    
    # 3. Liens Utiles
    print("🔗 LIENS D'OBSERVABILITÉ")
    print("- Arize Phoenix : http://localhost:6006")
    print("- MinIO Console : http://localhost:9001")
    print("- Qdrant UI     : http://localhost:6333/dashboard")
    
    print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    run_cockpit()
