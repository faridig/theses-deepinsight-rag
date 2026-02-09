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
    print(f"Indexing {len(documents)} docs...")
    service.index_documents(documents)
    print("Ingestion terminée.")

if __name__ == "__main__":
    main()
