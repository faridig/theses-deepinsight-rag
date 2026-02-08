import os
import sys
import socket
import logging
import phoenix as px
from llama_index.core import set_global_handler
from src.generation.rag_engine import RAGEngine

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("DeepInsight")

# 1. Stratégie Radicale : Silence total des logs OpenTelemetry
logging.getLogger("opentelemetry.sdk.trace.export").setLevel(logging.CRITICAL)
logging.getLogger("phoenix").setLevel(logging.ERROR)

def check_port_occupancy(port: int):
    """
    Vérifie l'occupation d'un port sur IPv4 et IPv6 et tente un bind check.
    Retourne un rapport détaillé.
    """
    results = {"ipv4": False, "ipv6": False, "bindable": False, "error": None}
    
    # Test IPv4
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            results["ipv4"] = (s.connect_ex(('127.0.0.1', port)) == 0)
    except Exception:
        pass

    # Test IPv6
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            results["ipv6"] = (s.connect_ex(('::1', port)) == 0)
    except Exception:
        pass

    # Bind Check (Vérification de liaison)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))
            results["bindable"] = True
    except Exception as e:
        results["bindable"] = False
        results["error"] = str(e)
        
    return results

def is_phoenix_healthy(port: int = 6006) -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1) as response:
            return response.status == 200
    except Exception:
        return False

# Configuration de l'instrumentation Phoenix
def setup_observability():
    if os.getenv("DISABLE_PHOENIX") == "1":
        return

    try:
        UI_PORT = 6006
        GRPC_PORT = 4317
        
        # Rapport d'Incident gRPC
        report = check_port_occupancy(GRPC_PORT)
        is_occupied = report["ipv4"] or report["ipv6"] or not report["bindable"]
        
        if is_occupied:
            if is_phoenix_healthy(UI_PORT):
                logger.info("ℹ️ Phoenix opérationnel détecté.")
                try:
                    set_global_handler("arize_phoenix")
                except Exception:
                    logger.info("ℹ️ Instrumentation Phoenix ignorée (déjà configurée ou port occupé).")
                return
            else:
                logger.info("ℹ️ Phoenix non disponible - Continuation sans monitoring.")
                return

        # Tentative de lancement
        try:
            # On redirige stdout/stderr vers devnull pour phoenix.launch_app() 
            # car certains logs internes ne respectent pas le logging standard
            with open(os.devnull, 'w') as f:
                original_stdout = sys.stdout
                original_stderr = sys.stderr
                try:
                    sys.stdout = f
                    sys.stderr = f
                    px.launch_app()
                finally:
                    sys.stdout = original_stdout
                    sys.stderr = original_stderr
            
            # On attend un tout petit peu que le serveur démarre
            import time
            time.sleep(1)
        except Exception:
            logger.info("ℹ️ Phoenix non disponible - Continuation sans monitoring.")
            return

        # Vérification finale avant instrumentation
        if is_phoenix_healthy(UI_PORT):
            try:
                set_global_handler("arize_phoenix")
                logger.info("✅ Observabilité Phoenix activée.")
            except Exception:
                logger.info("ℹ️ Phoenix non disponible - Continuation sans monitoring.")
        else:
            logger.info("ℹ️ Phoenix non disponible - Continuation sans monitoring.")
        
    except Exception:
        # Silence total absolu (Directive Alpha)
        pass

setup_observability()


def main():
    logger.info("=== Theses-DeepInsight RAG Engine Demo ===")
    
    try:
        # Initialisation du moteur
        engine = RAGEngine()
        logger.info("Moteur RAG prêt.\n")
    except Exception as e:
        logger.error(f"Erreur d'initialisation : {e}")
        sys.exit(1)

    print("Tapez 'exit' ou 'quit' pour quitter.")
    
    while True:
        question = input("\nVotre question : ")
        
        if question.lower() in ['exit', 'quit']:
            print("Au revoir !")
            break
            
        if not question.strip():
            continue
            
        print("Recherche en cours...")
        response = engine.ask(question)
        
        print("\n--- RÉPONSE ---")
        # str(response) fonctionne pour Response et les chaînes d'erreur
        print(str(response))
        print("----------------\n")
        
        # Affichage des sources si disponibles
        source_nodes = getattr(response, 'source_nodes', None)
        if source_nodes:
            print("Sources utilisées :")
            for i, node in enumerate(source_nodes):
                title = node.metadata.get('titre', 'Inconnu')
                author = node.metadata.get('auteur', 'Inconnu')
                score = getattr(node, 'score', "N/A")
                if isinstance(score, float):
                    print(f"[{i+1}] {title} - {author} (Score: {score:.2f})")
                else:
                    print(f"[{i+1}] {title} - {author} (Score: {score})")

if __name__ == "__main__":
    main()
