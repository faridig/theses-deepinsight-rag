
import os
import shutil
from src.indexing.vector_service import VectorService
from llama_index.core import Settings
from llama_index.core.embeddings import MockEmbedding
from llama_index.core.schema import TextNode

# Use Mock embedding to avoid API calls and costs
Settings.embed_model = MockEmbedding(embed_dim=1536)

def audit_manual():
    storage_path = "./storage/chroma_audit"
    if os.path.exists(storage_path):
        shutil.rmtree(storage_path)
    
    print(f"--- Étape 1: Création de l'index dans {storage_path} ---")
    service = VectorService(storage_path=storage_path, collection_name="audit_collection")
    
    node = TextNode(
        text="La physique quantique est fascinante.",
        metadata={"window": "Contexte physique.", "title": "Physique"}
    )
    service.index_nodes([node])
    print("Index créé et sauvegardé.")
    
    # Vérification physique
    print("\n--- Étape 2: Vérification physique des fichiers ---")
    if os.path.exists(storage_path):
        print(f"Le dossier {storage_path} existe.")
        files = os.listdir(storage_path)
        print(f"Fichiers trouvés: {files}")
        if any("chroma.sqlite3" in f for f in files) or any("chroma-embeddings.parquet" in f for f in files) or os.path.exists(os.path.join(storage_path, "chroma.sqlite3")):
             print("✅ Fichiers ChromaDB détectés.")
        else:
             print("❌ Fichiers ChromaDB non trouvés dans le dossier.")
    else:
        print(f"❌ Le dossier {storage_path} n'a pas été créé.")

    # Test de survie
    print("\n--- Étape 3: Test de survie (rechargement) ---")
    # On crée une nouvelle instance
    service_reload = VectorService(storage_path=storage_path, collection_name="audit_collection")
    results = service_reload.query("physique", similarity_top_k=1)
    
    if len(results) > 0:
        top_node = results[0].node
        print(f"Résultat trouvé: '{top_node.get_content()}'")
        print(f"Métadonnées: {top_node.metadata}")
        if "window" in top_node.metadata:
            print("✅ Métadonnée 'window' préservée.")
        else:
            print("❌ Métadonnée 'window' manquante.")
        
        if top_node.metadata.get("title") == "Physique":
            print("✅ Métadonnée 'title' préservée.")
    else:
        print("❌ Aucun résultat après rechargement.")

    # Cleanup optional
    # shutil.rmtree(storage_path)

if __name__ == "__main__":
    audit_manual()
