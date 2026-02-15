import phoenix as px
import pandas as pd
from phoenix.trace.dsl import SpanQuery

client = px.Client(endpoint="http://localhost:6006")

def test_fetch():
    print("Fetching traces from Phoenix...")
    # Requête pour obtenir les sessions RAG (souvent des CHAIN au top level)
    query = SpanQuery(client).filter('kind == "CHAIN"')
    df = query.all()
    print(f"Found {len(df)} traces")
    if len(df) > 0:
        print(df.columns)
        print(df.head())

if __name__ == "__main__":
    test_fetch()
