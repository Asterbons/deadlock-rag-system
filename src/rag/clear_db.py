import sys
import os

# Add project root to sys.path
PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from qdrant_client import QdrantClient
from src.rag.indexer import COLLECTIONS, QDRANT_URL

def clear_database():
    client = QdrantClient(url=QDRANT_URL)
    print(f"Connecting to Qdrant at {QDRANT_URL}...")
    
    for key, collection_name in COLLECTIONS.items():
        if client.collection_exists(collection_name):
            print(f"Deleting collection: {collection_name}")
            client.delete_collection(collection_name)
        else:
            print(f"Collection {collection_name} does not exist, skipping.")
            
    print("\nDatabase cleared! Now you can run the indexer again.")

if __name__ == "__main__":
    clear_database()
