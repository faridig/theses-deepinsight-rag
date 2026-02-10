import os
import sys
from src.generation.rag_engine import RAGEngine

def main():
    os.environ["DISABLE_PHOENIX"] = "1"
    try:
        engine = RAGEngine()
        # Question qui devrait générer des sources
        response = engine.ask("Qu'est-ce que l'IA ?")
        print("\n=== REPONSE RAG ===")
        print(response)
        print("=== FIN REPONSE ===")
        
        source_nodes = getattr(response, 'source_nodes', None)

        if source_nodes and len(source_nodes) > 0:
            print(f"\n✅ Bloc Sources détecté ({len(source_nodes)} sources).")
            first_node_metadata = source_nodes[0].metadata
            
            # Vérification des métadonnées (PBI-012)
            if 'titre' in first_node_metadata and first_node_metadata['titre'] != 'Inconnu':
                print(f"✅ Métadonnée 'titre' trouvée : {first_node_metadata['titre']}")
            else:
                print("❌ Métadonnée 'titre' manquante ou 'Inconnu'.")
                sys.exit(1)
            
            if 'auteur' in first_node_metadata and first_node_metadata['auteur'] != 'Inconnu':
                print(f"✅ Métadonnée 'auteur' trouvée : {first_node_metadata['auteur']}")
            else:
                print("❌ Métadonnée 'auteur' manquante ou 'Inconnu'.")
                sys.exit(1)
        else:
            print("\n❌ Bloc Sources manquant ou vide.")
            sys.exit(1)

        
        print("✅ Smoke test réussi.")

    except Exception as e:
        print(f"Erreur: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
