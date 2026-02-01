import unittest
from unittest.mock import patch, MagicMock
import os
import shutil
from src.ingestion.theses_client import ThesesClient

class TestThesesClient(unittest.TestCase):
    def setUp(self):
        self.client = ThesesClient()
        self.test_data_dir = "data/test_outputs"
        os.makedirs(self.test_data_dir, exist_ok=True)
        self.client.data_dir = self.test_data_dir

    def tearDown(self):
        if os.path.exists(self.test_data_dir):
            shutil.rmtree(self.test_data_dir)

    @patch("httpx.Client.get")
    def test_search_success(self, mock_get):
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "docs": [
                    {
                        "id": "2023PA010001",
                        "titrePrincipal": ["Une thèse magnifique"],
                        "auteurs": ["Jean Dupont"],
                        "dateSoutenance": "2023-01-01",
                        "discipline": ["Informatique"],
                        "resumes": ["Ceci est un résumé."],
                        "urlDocument": "https://www.theses.fr/2023PA010001/document"
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        results = self.client.search("AI")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "2023PA010001")
        self.assertEqual(results[0]["titre"], "Une thèse magnifique")

    @patch("httpx.Client.get")
    def test_download_pdf_success(self, mock_get):
        # Mock PDF download
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"%PDF-1.4 mock content"
        mock_get.return_value = mock_response

        path = self.client.download_pdf("2023PA010001", "https://www.theses.fr/2023PA010001/document")
        
        self.assertIsNotNone(path)
        if path:
            self.assertTrue(os.path.exists(path))
            with open(path, "rb") as f:
                self.assertEqual(f.read(), b"%PDF-1.4 mock content")

    @patch("httpx.Client.get")
    def test_download_pdf_not_found(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        path = self.client.download_pdf("missing", "https://www.theses.fr/missing/document")
        self.assertIsNone(path)

if __name__ == "__main__":
    unittest.main()
