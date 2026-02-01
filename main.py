import os
import sys
import phoenix as px
from llama_index.core import set_global_handler

# Configuration robuste de l'instrumentation Phoenix
try:
    # Lancement du serveur Phoenix (gère les appels multiples en interne ou via exception)
    px.launch_app()
    set_global_handler("arize_phoenix")
    print("✅ Observabilité Phoenix activée (http://localhost:6006)")
except Exception as e:
    # Si Phoenix est déjà lancé ou une erreur survient, on continue gracieusement
    if "Failed to bind to address" in str(e):
        print("ℹ️ Phoenix est déjà actif sur le port 4317.")
    else:
        print(f"⚠️ Note: Erreur lors de l'initialisation de Phoenix : {e}")

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
