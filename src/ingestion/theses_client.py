import httpx
import os
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
from s3fs import S3FileSystem

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ThesesClient:
    """Client for interacting with theses.fr API and downloading documents.

    Attributes:
        base_url (str): The base URL for the theses.fr search API.
        user_agent (str): The User-Agent header used for requests.
        data_dir (str): Directory where downloaded PDFs will be stored (if local).
        fs (Optional[S3FileSystem]): S3 filesystem for remote storage.
        bucket (Optional[str]): Bucket name for remote storage.
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
        
        # Load from ENV if not provided (PBI-026)
        self.bucket = bucket or os.getenv("MINIO_BUCKET")
        self.fs = fs
        
        if not self.fs and os.getenv("MINIO_ENDPOINT_URL"):
            try:
                # Review Fix: No hardcoded secrets in defaults
                access_key = os.getenv("MINIO_ACCESS_KEY")
                secret_key = os.getenv("MINIO_SECRET_KEY")
                endpoint_url = os.getenv("MINIO_ENDPOINT_URL")
                
                if access_key and secret_key and endpoint_url:
                    self.fs = S3FileSystem(
                        key=access_key,
                        secret=secret_key,
                        endpoint_url=endpoint_url,
                        use_ssl=os.getenv("MINIO_USE_SSL", "False").lower() == "true"
                    )
                    logger.info(f"Initialized S3FileSystem with endpoint {endpoint_url}")
                    
                    # Ensure bucket exists
                    if self.bucket and not self.fs.exists(self.bucket):
                        self.fs.makedirs(self.bucket)
                        logger.info(f"Created bucket: {self.bucket}")
                else:
                    logger.warning("MinIO environment variables missing (ACCESS_KEY, SECRET_KEY or ENDPOINT_URL). Falling back to local.")
            except Exception as e:
                logger.error(f"Failed to initialize S3FileSystem: {e}")
                self.fs = None

        if not self.fs:
            os.makedirs(self.data_dir, exist_ok=True)
            logger.info(f"Using local storage at {self.data_dir}")
            
        self.headers = {"User-Agent": self.user_agent}

    def search(self, query: str, rows: int = 10, start: int = 0, filters: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Searches for theses on theses.fr with pagination and filters (PBI-025).

        Args:
            query (str): The search keywords.
            rows (int): Number of results to return. Defaults to 10.
            start (int): Starting index for pagination. Defaults to 0.
            filters (Optional[Dict[str, str]]): Additional filters (e.g., {"discipline": "informatique"}).

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing thesis metadata.
        """
        # Construction de la requête avec filtres
        full_query = query
        if filters:
            for key, value in filters.items():
                full_query += f' AND {key}:"{value}"'

        params = {
            "q": full_query,
            "format": "json",
            "rows": rows,
            "start": start
        }
        
        try:
            with httpx.Client(headers=self.headers, timeout=10.0, follow_redirects=True) as client:
                response = client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                theses_list = data.get("theses", [])
                results = []
                for doc in theses_list:
                    thesis_id = doc.get("id")
                    url_document = f"https://theses.fr/{thesis_id}/document" if thesis_id else None
                    
                    results.append({
                        "id": thesis_id,
                        "titre": doc.get("titrePrincipal"),
                        "auteurs": [f"{a.get('prenom', '')} {a.get('nom', '')}".strip() for a in doc.get("auteurs", [])],
                        "dateSoutenance": doc.get("dateSoutenance"),
                        "discipline": doc.get("discipline"),
                        "resume": None,
                        "urlDocument": url_document
                    })
                return results
        except httpx.HTTPError as e:
            logger.error(f"Error during search for query '{full_query}': {e}")
            return []

    def search_all(self, query: str, limit: int = 100, filters: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Searches for all theses up to a limit using pagination (PBI-025)."""
        all_results = []
        rows_per_page = 100
        start = 0
        
        while len(all_results) < limit:
            rows_to_fetch = min(rows_per_page, limit - len(all_results))
            page_results = self.search(query, rows=rows_to_fetch, start=start, filters=filters)
            
            if not page_results:
                break
                
            all_results.extend(page_results)
            start += rows_to_fetch
            
            if len(page_results) < rows_to_fetch:
                break # No more results
                
        return all_results

    def download_pdf(self, thesis_id: str, download_url: str, theme: Optional[str] = None) -> Optional[str]:
        """Downloads a PDF document for a given thesis ID.

        Args:
            thesis_id (str): The unique ID of the thesis.
            download_url (str): The URL where the PDF is located.
            theme (Optional[str]): Optional theme for organization (PBI-026).

        Returns:
            Optional[str]: The path (local or S3) to the downloaded file if successful, None otherwise.
        """
        if not download_url:
            logger.warning(f"No download URL provided for thesis {thesis_id}")
            return None

        if self.fs and self.bucket:
            if theme:
                file_path = f"{self.bucket}/{theme}/{thesis_id}.pdf"
            else:
                file_path = f"{self.bucket}/{thesis_id}.pdf"
        else:
            if theme:
                target_dir = Path(self.data_dir) / theme
                os.makedirs(target_dir, exist_ok=True)
                file_path = str(target_dir / f"{thesis_id}.pdf")
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
                    # Open with 'wb' as requested in PBI-026
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
