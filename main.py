import os
import sys
import socket
import phoenix as px
from llama_index.core import set_global_handler

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

# Configuration robuste de l'instrumentation Phoenix
def setup_observability():
    try:
        # Ports par défaut de Phoenix
        UI_PORT = 6006
        GRPC_PORT = 4317
        
        # Mode Headless : Si le port gRPC est déjà utilisé, on suppose Phoenix actif
        if is_port_in_use(GRPC_PORT):
            print(f"ℹ️ Phoenix détecté sur le port {GRPC_PORT}. Connexion à l'instance existante.")
            set_global_handler("arize_phoenix")
            return

        # Si le port UI est utilisé mais pas gRPC, conflit probable
        if is_port_in_use(UI_PORT):
            print(f"⚠️ Port {UI_PORT} occupé mais Phoenix gRPC (4317) non détecté. Désactivation de l'instrumentation.")
            return

        # Tentative de lancement
        px.launch_app()
        set_global_handler("arize_phoenix")
        print("✅ Observabilité Phoenix activée (http://localhost:6006)")
        
    except Exception as e:
        # Silence Radio sur Erreur : Un seul message clair, pas de boucle d'erreurs
        print(f"❌ Observabilité désactivée : {e if 'bind' not in str(e) else 'Conflit de port gRPC'}")

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
