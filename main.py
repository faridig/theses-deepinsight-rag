import os
import sys
import socket
import logging
import phoenix as px
from llama_index.core import set_global_handler

# 1. Stratégie Radicale : Silence total des logs OpenTelemetry pour éviter le spam
logging.getLogger("opentelemetry.sdk.trace.export").setLevel(logging.CRITICAL)

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

# 2. Vérification de Santé (Health Check)
def is_phoenix_healthy(port: int = 6006) -> bool:
    import urllib.request
    try:
        # Vérifie que l'UI de Phoenix répond
        with urllib.request.urlopen(f"http://localhost:{port}/", timeout=1) as response:
            return response.status == 200
    except Exception:
        return False

# Configuration de l'instrumentation Phoenix
def setup_observability():
    # 3. Option de désactivation totale via .env
    if os.getenv("DISABLE_PHOENIX") == "1":
        print("ℹ️ Observabilité désactivée par DISABLE_PHOENIX=1")
        return

    try:
        UI_PORT = 6006
        GRPC_PORT = 4317
        
        # Mode Headless : Vérification de santé avant connexion
        if is_port_in_use(GRPC_PORT) and is_phoenix_healthy(UI_PORT):
            print(f"ℹ️ Phoenix sain détecté sur le port {GRPC_PORT}. Connexion à l'instance existante.")
            set_global_handler("arize_phoenix")
            return

        # Si ports occupés mais service non sain, on abandonne pour éviter les erreurs
        if is_port_in_use(GRPC_PORT) or is_port_in_use(UI_PORT):
            print("⚠️ Ports Phoenix occupés mais service non répondant. Instrumentation ignorée.")
            return

        # Tentative de lancement
        px.launch_app()
        set_global_handler("arize_phoenix")
        print("✅ Observabilité Phoenix activée (http://localhost:6006)")
        
    except Exception as e:
        # Silence Radio sur Erreur : Un seul message clair
        print(f"❌ Observabilité ignorée : {e if 'bind' not in str(e) else 'Conflit de port gRPC'}")

setup_observability()

from src.generation.rag_engine import RAGEngine

def main():
    print("=== Theses-DeepInsight RAG Engine Demo ===")
    
    try:
        # Initialisation du moteur
        engine = RAGEngine()
        print("Moteur RAG initialisé avec succès.\n")
    except Exception as e:
        print(f"Erreur d'initialisation : {e}")
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
