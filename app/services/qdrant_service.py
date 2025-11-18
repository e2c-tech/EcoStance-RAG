from qdrant_client import QdrantClient, models
from typing import List, Dict, Any
import uuid

from app.config import QDRANT_URL, QDRANT_API_KEY, EMBEDDING_VECTOR_SIZE, DISTANCE_METRIC

def get_qdrant_client():
    """
    Initializes and returns the Qdrant client using credentials from the config.
    """
    if not QDRANT_URL or not QDRANT_API_KEY:
        raise ValueError("QDRANT_URL and QDRANT_API_KEY must be set in environment variables.")
    
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return client

def create_collection_if_not_exists(client: QdrantClient, collection_name: str):
    """
    Checks if a collection exists in Qdrant and creates it if it doesn't.
    Also ensures the required payload index is created on the flat 'source_filename' field.
    """
    try:
        client.get_collection(collection_name=collection_name)
        print(f"Collection '{collection_name}' already exists.")
    except Exception:
        print(f"Collection '{collection_name}' not found. Creating it now...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=EMBEDDING_VECTOR_SIZE,
                distance=DISTANCE_METRIC
            ),
        )
        print(f"Collection '{collection_name}' created successfully.")

    # Ensure the payload index for the top-level 'source_filename' field exists.
    try:
        print(f"Ensuring payload index exists for 'source_filename' in '{collection_name}'...")
        client.create_payload_index(
            collection_name=collection_name,
            field_name="source_filename",  # Indexing the top-level field
            field_schema=models.PayloadSchemaType.KEYWORD,
            wait=True
        )
        print("Payload index for 'source_filename' created or already exists.")
    except Exception as e:
        print(f"Warning: Could not create payload index for 'source_filename'. This may affect delete performance. Error: {e}")


def upload_to_qdrant(client: QdrantClient, collection_name: str, chunks: List[Dict[str, Any]]):
    """
    Uploads a list of processed chunks (with embeddings and metadata) to Qdrant.
    The payload is stored in a flat structure.
    """
    points_to_upload = []
    for chunk in chunks:
        point_id = str(uuid.uuid4())
        # Create a flat payload by unpacking the metadata dictionary
        payload = {
            "text": chunk["text"],
            **chunk["metadata"]
        }
        vector = chunk["embedding"]
        points_to_upload.append(models.PointStruct(id=point_id, vector=vector, payload=payload))

    client.upsert(
        collection_name=collection_name,
        points=points_to_upload,
        wait=True
    )
    print(f"Successfully uploaded {len(points_to_upload)} points to Qdrant collection '{collection_name}'.")

# --- Knowledge Base Management Functions ---

def list_collections(client: QdrantClient) -> List[str]:
    """
    Retrieves a list of all collection names from Qdrant.
    """
    collections_response = client.get_collections()
    return [collection.name for collection in collections_response.collections]

def get_collection_info(client: QdrantClient, collection_name: str) -> Dict[str, Any]:
    """
    Retrieves detailed information about a specific collection.
    """
    try:
        collection_info = client.get_collection(collection_name=collection_name)
        # Convert the response to a more friendly dictionary format
        return {
            "name": collection_name,
            "vector_count": collection_info.vectors_count,
            "indexed_fields": list(collection_info.payload_schema.keys()),
        }
    except Exception as e:
        # Handle cases where the collection doesn't exist
        return {"error": f"Collection '{collection_name}' not found or error fetching info: {e}"}

def delete_collection(client: QdrantClient, collection_name: str) -> bool:
    """
    Deletes a collection and all its associated data from Qdrant.
    """
    try:
        result = client.delete_collection(collection_name=collection_name)
        if result:
            print(f"Collection '{collection_name}' deleted successfully.")
            return True
        return False
    except Exception as e:
        print(f"Error deleting collection '{collection_name}': {e}")
        return False
