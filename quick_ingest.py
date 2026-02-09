import os
from src.processing.parser import ThesisParser
from src.indexing.vector_service import VectorService

def main():
    parser = ThesisParser()
    service = VectorService()
    
    pdf_path = "data/2024PA131029.pdf" # Un fichier existant
    if not os.path.exists(pdf_path):
        print(f"Fichier {pdf_path} non trouvé.")
        return

    print(f"Parsing {pdf_path}...")
    documents = parser.parse_pdf(pdf_path)

    # Ajout des métadonnées requises par main.py pour l'affichage de la traçabilité
    base_name = os.path.basename(pdf_path).replace(".pdf", "")
    title = f"Thèse Technique {base_name}"
    author = "Équipe Technique DeepInsight"

    for doc in documents:
        doc.metadata["titre"] = title
        doc.metadata["auteur"] = author
    print(f"Indexing {len(documents)} docs...")
    service.index_nodes(documents)
    print("Ingestion terminée.")

if __name__ == "__main__":
    main()
