import unittest
from src.ingestion.theses_client import ThesesClient
import s3fs

class TestThesesClientS3(unittest.TestCase):
    def setUp(self):
        self.endpoint_url = "http://localhost:9000"
        self.key = "minioadmin"
        self.secret = "minioadmin"
        self.bucket = "test-bucket"
        
        # Skip if MinIO is not reachable (e.g. in CI)
        try:
            self.fs = s3fs.S3FileSystem(
                endpoint_url=self.endpoint_url,
                key=self.key,
                secret=self.secret,
                use_ssl=False
            )
            # Short timeout check
            self.fs.ls("/", detail=False)
            if not self.fs.exists(self.bucket):
                self.fs.mkdir(self.bucket)
        except Exception:
            self.skipTest("MinIO not reachable at http://localhost:9000")
        
        self.client = ThesesClient(fs=self.fs, bucket=self.bucket)

    def test_download_pdf_to_s3(self):
        # Use a real but small PDF or a mock response
        # For the sake of this test, we'll use a known working URL from theses.fr
        thesis_id = "2023STRAB011"
        url = f"https://theses.fr/{thesis_id}/document"
        
        result = self.client.download_pdf(thesis_id, url)
        
        self.assertIsNotNone(result)
        s3_path = result["path"]
        self.assertTrue(s3_path.startswith(self.bucket))
        self.assertTrue(self.fs.exists(s3_path))
        
        # Clean up files
        self.fs.rm(s3_path)
        # Clean up the reference file if it exists
        ref_path = f"{self.bucket}/unsorted/{thesis_id}.ref"
        if self.fs.exists(ref_path):
            self.fs.rm(ref_path)

    def tearDown(self):
        """Nettoyage du bucket après les tests (PBI-Review: Hygiène S3)."""
        if hasattr(self, "fs") and hasattr(self, "bucket"):
            try:
                if self.fs.exists(self.bucket):
                    self.fs.rm(self.bucket, recursive=True)
                    print(f"\n[CLEANUP] Bucket {self.bucket} supprimé.")
            except Exception as e:
                print(f"\n[WARNING] Échec du nettoyage du bucket {self.bucket}: {e}")

if __name__ == "__main__":
    unittest.main()
