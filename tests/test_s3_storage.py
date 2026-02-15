import os
import pytest
from src.ingestion.theses_client import ThesesClient
from s3fs import S3FileSystem
from dotenv import load_dotenv

load_dotenv()

@pytest.fixture
def s3_config():
    return {
        "key": os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        "secret": os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        "endpoint_url": os.getenv("MINIO_ENDPOINT_URL", "http://localhost:9000"),
        "bucket": "test-storage-bucket"
    }

@pytest.mark.asyncio
async def test_theses_client_s3_init(s3_config):
    """Vérifie que le client s'initialise correctement avec S3."""
    os.environ["MINIO_ACCESS_KEY"] = s3_config["key"]
    os.environ["MINIO_SECRET_KEY"] = s3_config["secret"]
    os.environ["MINIO_ENDPOINT_URL"] = s3_config["endpoint_url"]
    os.environ["MINIO_BUCKET"] = s3_config["bucket"]

    client = ThesesClient()
    
    if client.fs is None:
        pytest.skip(f"S3FileSystem could not be initialized at {s3_config['endpoint_url']}")
        
    assert client.fs is not None
    assert isinstance(client.fs, S3FileSystem)
    assert client.bucket == s3_config["bucket"]

@pytest.mark.asyncio
async def test_s3_download_mock(s3_config):
    """Test de téléchargement simulé vers MinIO."""
    # Ensure environment variables are set for ThesesClient initialization
    os.environ["MINIO_ACCESS_KEY"] = s3_config["key"]
    os.environ["MINIO_SECRET_KEY"] = s3_config["secret"]
    os.environ["MINIO_ENDPOINT_URL"] = s3_config["endpoint_url"]
    os.environ["MINIO_BUCKET"] = s3_config["bucket"]

    client = ThesesClient(bucket=s3_config["bucket"])
    
    # If S3 init failed due to connection error, skip the rest of the test
    # (ThesesClient logs the error and sets self.fs to None)
    if client.fs is None:
        pytest.skip(f"S3FileSystem could not be initialized at {s3_config['endpoint_url']}")
    
    test_id = "test_thesis_123"
    test_content = b"Fake PDF content"
    test_url = "http://example.com/test.pdf"
    
    # On simule un téléchargement réussi sans appeler l'URL réelle
    from unittest.mock import MagicMock, patch

    with patch("httpx.Client.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = test_content
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        import hashlib
        expected_hash = hashlib.sha256(test_content).hexdigest()

        result = client.download_pdf(test_id, test_url, theme="test-theme")
        path = result["path"]
        
        assert path == f"{s3_config['bucket']}/pdfs/{expected_hash}.pdf"
        assert client.fs.exists(path)
        
        # Vérification du fichier de référence (PBI-028)
        ref_path = f"{s3_config['bucket']}/themes/test-theme/{test_id}.ref"
        assert client.fs.exists(ref_path)
        
        with client.fs.open(path, "rb") as f:
            assert f.read() == test_content
        
        # Cleanup
        client.fs.rm(path)
        client.fs.rm(ref_path)
