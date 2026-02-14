
import os
import logging
from src.ingestion.theses_client import ThesesClient

logging.basicConfig(level=logging.INFO)

def reality_test():
    os.environ["MINIO_ACCESS_KEY"] = "minioadmin"
    os.environ["MINIO_SECRET_KEY"] = "minioadmin"
    os.environ["MINIO_ENDPOINT_URL"] = "http://localhost:9000"
    os.environ["MINIO_BUCKET"] = "reality-test-bucket"
    
    print("Testing connection to MinIO...")
    client = ThesesClient()
    if client.fs and client.fs.exists("reality-test-bucket"):
        print("Success: Bucket exists or was created.")
        # Try to write a file
        with client.fs.open("reality-test-bucket/hello.txt", "wb") as f:
            f.write(b"Hello MinIO")
        print("Success: Wrote file to MinIO.")
        
        # Cleanup
        client.fs.rm("reality-test-bucket/hello.txt")
        print("Success: Deleted file from MinIO.")
    else:
        print("Failure: Could not verify bucket.")

if __name__ == "__main__":
    reality_test()
