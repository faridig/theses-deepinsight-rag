
import os
import pytest
import torch
from src.processing.parser import ThesisParser
from llama_index.core.schema import BaseNode

def test_cuda_available():
    # This is more of an info than a test, but it validates the requirement
    cuda_available = torch.cuda.is_available()
    print(f"CUDA available: {cuda_available}")

def test_docling_parsing_initialization():
    parser = ThesisParser(mode="docling")
    assert parser.mode == "docling"

def test_docling_parsing_real_file():
    # Use a small part of a PDF or skip if no files
    pdf_path = "data/2023STRAB011.pdf"
    if not os.path.exists(pdf_path):
        pytest.skip(f"PDF file {pdf_path} not found")
        
    parser = ThesisParser(mode="docling")
    # We use a mocked or limited version if we want it to be fast, 
    # but here we just check if it can run.
    # To keep CI fast, we might want to skip this in CI.
    if os.getenv("GITHUB_ACTIONS"):
        pytest.skip("Skipping heavy Docling test in CI")

    try:
        # Just parse 1 page would be enough for a smoke test if we could, 
        # but our parse_pdf doesn't expose max_num_pages yet (only via is_dev)
        nodes = parser.parse_pdf(pdf_path, is_dev=True)
        assert len(nodes) > 0
        assert isinstance(nodes[0], BaseNode)
        assert "page_label" in nodes[0].metadata
    except Exception as e:
        pytest.fail(f"Docling parsing failed: {e}")
