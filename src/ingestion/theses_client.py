import httpx
import os
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ThesesClient:
    """Client for interacting with theses.fr API and downloading documents.

    Attributes:
        base_url (str): The base URL for the theses.fr search API.
        user_agent (str): The User-Agent header used for requests.
        data_dir (str): Directory where downloaded PDFs will be stored.
    """

    def __init__(self, data_dir: str = "data", fs: Optional[Any] = None, bucket: Optional[str] = None) -> None:
        """Initializes the ThesesClient.

        Args:
            data_dir (str): Directory to save downloaded PDFs. Defaults to "data".
            fs (Optional[Any]): fsspec-compatible filesystem (e.g. S3FileSystem).
            bucket (Optional[str]): Bucket name if using a remote filesystem.
        """
        self.base_url = "https://theses.fr/api/v1/theses/recherche/"
        self.user_agent = "ThesesInsightBot/1.0"
        self.data_dir = data_dir
        self.fs = fs
        self.bucket = bucket
        if not self.fs:
            os.makedirs(self.data_dir, exist_ok=True)
        self.headers = {"User-Agent": self.user_agent}

    def search(self, query: str, rows: int = 10) -> List[Dict[str, Any]]:
        """Searches for theses on theses.fr.

        Args:
            query (str): The search keywords.
            rows (int): Number of results to return. Defaults to 10.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing thesis metadata.
        """
        params = {
            "q": query,
            "format": "json",
            "rows": rows
        }
        
        try:
            # Added follow_redirects=True as per mission correction
            with httpx.Client(headers=self.headers, timeout=10.0, follow_redirects=True) as client:
                response = client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Corrected root key: 'theses' instead of 'response/docs'
                theses_list = data.get("theses", [])
                results = []
                for doc in theses_list:
                    thesis_id = doc.get("id")
                    # Deduce PDF URL as it's missing from search JSON
                    url_document = f"https://theses.fr/{thesis_id}/document" if thesis_id else None
                    
                    results.append({
                        "id": thesis_id,
                        "titre": doc.get("titrePrincipal"),
                        "auteurs": [f"{a.get('prenom', '')} {a.get('nom', '')}".strip() for a in doc.get("auteurs", [])],
                        "dateSoutenance": doc.get("dateSoutenance"),
                        "discipline": doc.get("discipline"),
                        "resume": None,  # Absent from search API, will be handled in later PBI or detailed fetch
                        "urlDocument": url_document
                    })
                return results
        except httpx.HTTPError as e:
            logger.error(f"Error during search for query '{query}': {e}")
            return []

    def download_pdf(self, thesis_id: str, download_url: str) -> Optional[str]:
        """Downloads a PDF document for a given thesis ID.

        Args:
            thesis_id (str): The unique ID of the thesis.
            download_url (str): The URL where the PDF is located.

        Returns:
            Optional[str]: The path (local or S3) to the downloaded file if successful, None otherwise.
        """
        if not download_url:
            logger.warning(f"No download URL provided for thesis {thesis_id}")
            return None

        if self.fs and self.bucket:
            file_path = f"{self.bucket}/{thesis_id}.pdf"
        else:
            file_path = str(Path(self.data_dir) / f"{thesis_id}.pdf")
        
        try:
            with httpx.Client(headers=self.headers, timeout=30.0, follow_redirects=True) as client:
                response = client.get(download_url)
                if response.status_code == 404:
                    logger.warning(f"PDF not found for thesis {thesis_id} at {download_url}")
                    return None
                response.raise_for_status()
                
                if self.fs:
                    with self.fs.open(file_path, "wb") as f:
                        f.write(response.content)
                else:
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                
                logger.info(f"Successfully downloaded PDF for {thesis_id} to {file_path}")
                return file_path
        except httpx.HTTPError as e:
            logger.error(f"Error downloading PDF for {thesis_id} from {download_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error saving PDF for {thesis_id} to {file_path}: {e}")
            return None

    def _extract_first(self, value: Any) -> Optional[str]:
        """Helper to extract the first element if the value is a list.

        Args:
            value (Any): The value to extract from.

        Returns:
            Optional[str]: The extracted string or None.
        """
        if isinstance(value, list) and len(value) > 0:
            return str(value[0])
        return str(value) if value is not None else None
