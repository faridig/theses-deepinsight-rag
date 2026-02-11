import unittest
from src.ingestion.theses_client import ThesesClient
import s3fs

class TestThesesClientS3(unittest.TestCase):
    def setUp(self):
        self.endpoint_url = "http://localhost:9000"
        self.key = "minioadmin"
        self.secret = "minioadmin"
        self.bucket = "test-bucket"
        self.fs = s3fs.S3FileSystem(
            endpoint_url=self.endpoint_url,
            key=self.key,
            secret=self.secret,
            use_ssl=False
        )
        if not self.fs.exists(self.bucket):
            self.fs.mkdir(self.bucket)
        
        self.client = ThesesClient(fs=self.fs, bucket=self.bucket)

    def test_download_pdf_to_s3(self):
        # Use a real but small PDF or a mock response
        # For the sake of this test, we'll use a known working URL from theses.fr
        thesis_id = "2023STRAB011"
        url = f"https://theses.fr/{thesis_id}/document"
        
        s3_path = self.client.download_pdf(thesis_id, url)
        
        self.assertIsNotNone(s3_path)
        self.assertTrue(s3_path.startswith(self.bucket))
        self.assertTrue(self.fs.exists(s3_path))
        
        # Clean up
        self.fs.rm(s3_path)

if __name__ == "__main__":
    unittest.main()
