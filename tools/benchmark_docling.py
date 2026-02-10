
import logging
import os
from src.processing.parser import ThesisParser
from src.indexing.vector_service import VectorService
from src.generation.rag_engine import RAGEngine
from src.evaluation.evaluator import RagasEvaluator, RagasTestItem
from dotenv import load_dotenv

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def benchmark_docling_vs_llamaparse():
    """
    Benchmark Docling vs LlamaParse.
    """
    pdf_files = ["data/2023STRAB011.pdf", "data/2024STRAB004.pdf"]
    
    # 1. Parsing & Indexation with Docling
    logger.info("=== STEP 1: INDEXING WITH DOCLING ===")
    parser_docling = ThesisParser(mode="docling")
    vector_service_docling = VectorService(storage_path="./storage/chroma", collection_name="theses_docling")
    
    # We clear the collection to ensure a clean benchmark
    try:
        vector_service_docling.db.delete_collection("theses_docling")
        vector_service_docling = VectorService(storage_path="./storage/chroma", collection_name="theses_docling")
    except Exception:
        pass

    all_nodes = []
    for file_path in pdf_files:
        if not os.path.exists(file_path):
            logger.warning(f"File {file_path} not found, skipping.")
            continue
        logger.info(f"Parsing {file_path} with Docling...")
        # NOT using is_dev=True here to have the full content
        nodes = parser_docling.parse_pdf(file_path, is_dev=False)
        # Add some dummy business metadata for RAGEngine expectations
        for node in nodes:
            node.metadata.update({
                "titre": os.path.basename(file_path),
                "auteur": "Unknown"
            })
        all_nodes.extend(nodes)
    
    if all_nodes:
        logger.info(f"Indexing {len(all_nodes)} nodes in theses_docling...")
        vector_service_docling.index_nodes(all_nodes)

    # 2. Evaluation
    logger.info("=== STEP 2: EVALUATION ===")
    
    # Golden Dataset
    test_items = [
        RagasTestItem(
            query_str="Quels sont les impacts de l'intelligence artificielle sur le système scientifique ?",
            expected_response="L'IA affecte la production de connaissances, son originalité et l'impact scientifique associé.",
            expected_context=["impact of artificial intelligence (AI) on the scientific system"]
        ),
        RagasTestItem(
            query_str="Qui a popularisé le terme Knowledge Graph en 2012 ?",
            expected_response="Google a popularisé le terme Knowledge Graph en 2012.",
            expected_context=["popularisé qu’en 2012 lorsque Google a présenté son propre KG"]
        ),
        RagasTestItem(
            query_str="Qu'est-ce que Novelpy ?",
            expected_response="Novelpy est un outil open-source basé sur Python qui calcule divers indicateurs de nouveauté et de disruption.",
            expected_context=["Novelpy, un outil open-source basé sur Python"]
        )
    ]

    # Evaluate Docling
    logger.info("Evaluating Docling...")
    engine_docling = RAGEngine(collection_name="theses_docling")
    evaluator_docling = RagasEvaluator(engine_docling)
    results_docling = evaluator_docling.run_evaluation(test_items)
    
    # Evaluate LlamaParse (default collection)
    logger.info("Evaluating LlamaParse (Baseline)...")
    try:
        engine_llama = RAGEngine(collection_name="theses_collection")
        evaluator_llama = RagasEvaluator(engine_llama)
        results_llama = evaluator_llama.run_evaluation(test_items)
    except Exception as e:
        logger.error(f"Could not evaluate LlamaParse baseline: {e}")
        results_llama = None

    # 3. Report
    print("\n" + "="*50)
    print("BENCHMARK RESULTS: DOCLING VS LLAMAPARSE")
    print("="*50)
    
    print("\nDOCLING SCORES:")
    print(results_docling)
    
    if results_llama:
        print("\nLLAMAPARSE (BASELINE) SCORES:")
        print(results_llama)
    
    print("="*50 + "\n")

if __name__ == "__main__":
    benchmark_docling_vs_llamaparse()
