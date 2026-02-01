import os
import sys
import phoenix as px
from llama_index.core import set_global_handler

# Configuration de l'instrumentation Phoenix AVANT tout autre composant LlamaIndex
px.launch_app()
set_global_handler("arize_phoenix")

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
        print(response)
        print("----------------\n")
        
        # Affichage des sources si disponibles
        if hasattr(response, 'source_nodes') and response.source_nodes:
            print("Sources utilisées :")
            for i, node in enumerate(response.source_nodes):
                title = node.metadata.get('titre', 'Inconnu')
                author = node.metadata.get('auteur', 'Inconnu')
                score = node.score if hasattr(node, 'score') else "N/A"
                print(f"[{i+1}] {title} - {author} (Score: {score:.2f})")

if __name__ == "__main__":
    main()
