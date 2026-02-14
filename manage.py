import click
import logging
import os
from src.ingestion.theses_client import ThesesClient
from tabulate import tabulate
from qdrant_client import QdrantClient

# Silence technique
logging.getLogger("httpx").setLevel(logging.WARNING)

@click.group()
def cli():
    """Outil de gestion Theses-DeepInsight."""
    pass

@cli.command()
@click.option('--storage-path', default='./storage/qdrant', help='Path to Qdrant storage.')
def health(storage_path):
    """Affiche l'état de santé du système (PBI-028)."""
    click.echo("🔍 Analyse de l'état du système...")
    
    # 1. Analyse Qdrant
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    client = QdrantClient(url=qdrant_url)
    
    collections_data = []
    universities = {}
    
    try:
        collections = client.get_collections().collections
        for coll in collections:
            name = coll.name
            if not name.startswith("theses-"):
                continue
                
            info = client.get_collection(name)
            count = info.points_count
            
            # Récupération du volume (taille approximative) - Qdrant ne donne pas facilement la taille Mo via API simple
            # On va se contenter du nombre de docs pour l'instant
            
            collections_data.append([name, count])
            
            # Top Universités (via scan des points - attention si gros volume)
            # Pour la démo, on scanne les 100 premiers points de chaque collection
            points, _ = client.scroll(name, limit=100, with_payload=True)
            for p in points:
                if not isinstance(p.payload, dict):
                    continue
                univ = p.payload.get("university")
                if univ:
                    universities[univ] = universities.get(univ, 0) + 1
                    
    except Exception as e:
        click.echo(f"❌ Erreur lors de l'accès à Qdrant : {e}")

    # 2. Analyse Quarantaine & Storage
    theses_client = ThesesClient()
    quarantine_count = 0
    if theses_client.fs:
        try:
            if theses_client.fs.exists("quarantine"):
                quarantine_count = len(theses_client.fs.ls("quarantine"))
        except Exception:
            pass
    else:
        q_dir = os.path.join(theses_client.data_dir, "quarantine")
        if os.path.exists(q_dir):
            quarantine_count = len(os.listdir(q_dir))

    # Affichage des résultats
    click.echo("\n📊 Volume par Collection :")
    click.echo(tabulate(collections_data, headers=["Collection", "Nb Points"], tablefmt="grid"))
    
    click.echo(f"\n🛡️ État de la Quarantaine : {quarantine_count} fichiers suspects.")
    
    click.echo("\n🎓 Top 5 des Universités :")
    top_univs = sorted(universities.items(), key=lambda x: x[1], reverse=True)[:5]
    click.echo(tabulate(top_univs, headers=["Université", "Nb Docs"], tablefmt="simple"))

if __name__ == "__main__":
    cli()
