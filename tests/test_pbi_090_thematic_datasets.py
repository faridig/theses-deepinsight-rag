import os
import json
import pytest
from scripts.audit_quality import run_audit
from unittest.mock import patch, MagicMock


@pytest.fixture
def setup_test_datasets():
    # Setup data/benchmarks directory if not exists (done by dev but for test independence)
    os.makedirs("data/benchmarks", exist_ok=True)

    # Create a thematic dataset
    theme_data = [{"question": "Q Test", "ground_truth": "GT Test"}]
    theme_path = "data/benchmarks/ground_truth_test_pbi_090.json"
    with open(theme_path, "w") as f:
        json.dump(theme_data, f)

    # Create a global fallback in benchmarks
    global_bench_data = [
        {"question": "Q Global Bench", "ground_truth": "GT Global Bench"}
    ]
    global_bench_path = "data/benchmarks/ground_truth.json"
    with open(global_bench_path, "w") as f:
        json.dump(global_bench_data, f)

    yield {"theme_path": theme_path, "global_bench_path": global_bench_path}

    # Cleanup (Optional, but let's be clean)
    if os.path.exists(theme_path):
        os.remove(theme_path)
    # Note: we might not want to remove the global_bench_path if it's used elsewhere,
    # but for this specific test suite we should.


def test_load_thematic_dataset(setup_test_datasets):
    theme = "test_pbi_090"

    with (
        patch("scripts.audit_quality.setup_settings"),
        patch("scripts.audit_quality.RAGEngine") as mock_engine_class,
        patch("scripts.audit_quality.Dataset"),
        patch("scripts.audit_quality.evaluate") as mock_evaluate,
    ):
        # Mocking the engine and its response
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_response = MagicMock()
        mock_response.__str__.return_value = "Test response"
        mock_response.source_nodes = []
        mock_engine.ask.return_value = mock_response

        # Mock evaluate to avoid actual heavy computation
        mock_evaluate.return_value = {"faithfulness": 0.9}

        # Run audit with theme
        run_audit(collection=theme)

        # Verify the engine was asked with the right theme
        mock_engine.ask.assert_called_with("Q Test", theme=theme)


def test_fallback_to_global_benchmark(setup_test_datasets):
    # Non-existent theme
    theme = "unknown_theme_pbi_090"

    with (
        patch("scripts.audit_quality.setup_settings"),
        patch("scripts.audit_quality.RAGEngine") as mock_engine_class,
        patch("scripts.audit_quality.Dataset"),
        patch("scripts.audit_quality.evaluate") as mock_evaluate,
    ):
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_response = MagicMock()
        mock_response.__str__.return_value = "Test response"
        mock_engine.ask.return_value = mock_response

        mock_evaluate.return_value = {"faithfulness": 0.9}

        # Run audit
        run_audit(collection=theme)

        # Verify it used the global bench dataset (Q Global Bench)
        mock_engine.ask.assert_called_with("Q Global Bench", theme=theme)


def test_legacy_fallback():
    # Ensure benchmarks/ground_truth.json doesn't exist
    if os.path.exists("data/benchmarks/ground_truth.json"):
        os.rename(
            "data/benchmarks/ground_truth.json", "data/benchmarks/ground_truth.json.bak"
        )

    try:
        # Create legacy dataset
        legacy_data = [{"question": "Q Legacy", "ground_truth": "GT Legacy"}]
        legacy_path = "data/ground_truth.json"
        with open(legacy_path, "w") as f:
            json.dump(legacy_data, f)

        with (
            patch("scripts.audit_quality.setup_settings"),
            patch("scripts.audit_quality.RAGEngine") as mock_engine_class,
            patch("scripts.audit_quality.Dataset") as mock_dataset_class,
            patch("scripts.audit_quality.evaluate") as mock_evaluate,
        ):
            mock_engine = MagicMock()
            mock_engine_class.return_value = mock_engine
            mock_response = MagicMock()
            mock_response.__str__.return_value = "Test response"
            mock_engine.ask.return_value = mock_response

            mock_evaluate.return_value = {"faithfulness": 0.9}

            # Run audit
            run_audit(collection="any_theme")

            # Verify it used the legacy dataset
            mock_engine.ask.assert_called_with("Q Legacy", theme="any_theme")

    finally:
        # Restore benchmarks/ground_truth.json if it was backed up
        if os.path.exists("data/benchmarks/ground_truth.json.bak"):
            os.rename(
                "data/benchmarks/ground_truth.json.bak",
                "data/benchmarks/ground_truth.json",
            )
