from qdrant_client import QdrantClient, models
from typing import List, Dict, Any, Optional
import uuid
import logging
from threading import Lock

from app.config import QDRANT_URL, QDRANT_API_KEY, EMBEDDING_VECTOR_SIZE, DISTANCE_METRIC
# Database tracing removed - limiting to embedding, RAG, and agent only

logger = logging.getLogger(__name__)

# Global Qdrant client instance (singleton pattern)
_qdrant_client: Optional[QdrantClient] = None
_qdrant_client_lock = Lock()


def get_qdrant_client() -> QdrantClient:
    """
    Returns a singleton Qdrant client instance with connection pooling.
    
    This ensures only one client is created and reused across all requests,
    improving performance and reducing connection overhead.
    
    Returns:
        QdrantClient: Singleton Qdrant client instance
        
    Raises:
        ValueError: If QDRANT_URL or QDRANT_API_KEY are not set
    """
    global _qdrant_client
    
    # Double-checked locking pattern for thread-safe singleton
    if _qdrant_client is None:
        with _qdrant_client_lock:
            if _qdrant_client is None:
                if not QDRANT_URL or not QDRANT_API_KEY:
                    raise ValueError("QDRANT_URL and QDRANT_API_KEY must be set in environment variables.")
                
                logger.info(f"Initializing Qdrant client singleton: {QDRANT_URL}")
                
                # Create client with connection pooling settings
                _qdrant_client = QdrantClient(
                    url=QDRANT_URL,
                    api_key=QDRANT_API_KEY,
                    timeout=30,  # Request timeout in seconds
                    # Connection pooling is handled internally by httpx (used by qdrant-client)
                    # The client maintains persistent connections automatically
                )
                
                logger.info("✓ Qdrant client singleton initialized successfully")
    
    return _qdrant_client


def close_qdrant_client():
    """
    Close the Qdrant client connection.
    Should be called on application shutdown.
    """
    global _qdrant_client
    
    if _qdrant_client is not None:
        with _qdrant_client_lock:
            if _qdrant_client is not None:
                try:
                    _qdrant_client.close()
                    logger.info("✓ Qdrant client closed successfully")
                except Exception as e:
                    logger.error(f"Error closing Qdrant client: {e}")
                finally:
                    _qdrant_client = None

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

    # Ensure the payload index for 'email_id' exists (for Gmail integration).
    try:
        print(f"Ensuring payload index exists for 'email_id' in '{collection_name}'...")
        client.create_payload_index(
            collection_name=collection_name,
            field_name="email_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
            wait=True
        )
        print("Payload index for 'email_id' created or already exists.")
    except Exception as e:
        print(f"Warning: Could not create payload index for 'email_id'. Error: {e}")


def upload_to_qdrant(
    client: QdrantClient, 
    collection_name: str, 
    chunks: List[Dict[str, Any]],
    tenant_id: Optional[str] = None
):
    """
    Uploads a list of processed chunks (with embeddings and metadata) to Qdrant.
    The payload is stored in a flat structure with tenant_id for isolation.
    
    Args:
        client: Qdrant client
        collection_name: Target collection name
        chunks: List of chunks with embeddings and metadata
        tenant_id: Tenant identifier (added to metadata for filtering)
    """
    points_to_upload = []
    for chunk in chunks:
        point_id = str(uuid.uuid4())
        # Create a flat payload by unpacking the metadata dictionary
        payload = {
            "text": chunk["text"],
            **chunk["metadata"]
        }
        
        # Add tenant_id to payload if provided
        if tenant_id:
            payload["tenant_id"] = tenant_id
        
        vector = chunk["embedding"]
        points_to_upload.append(models.PointStruct(id=point_id, vector=vector, payload=payload))

    if not points_to_upload:
        logger.warning(f"No points to upload for collection '{collection_name}'")
        return

    # Chunk the points into larger batches to speed up the network transfer,
    # keeping each payload comfortably under Qdrant's 32MB limit.
    batch_size = 500
    try:
        for i in range(0, len(points_to_upload), batch_size):
            batch = points_to_upload[i:i + batch_size]
            client.upsert(
                collection_name=collection_name,
                points=batch,
                wait=True # Wait until Qdrant confirms the chunks are indexed and searchable
            )
        logger.info(f"Successfully uploaded {len(points_to_upload)} points in batches of {batch_size} to '{collection_name}'")
    except Exception as e:
        logger.error(f"Failed to upload points to Qdrant: {e}")
        raise


def delete_points_by_metadata(client: QdrantClient, collection_name: str, key: str, value: str):
    """
    Deletes points from a collection where the payload metadata matches the given key-value pair.
    Useful for deleting vectors associated with a specific file or email.
    """
    try:
        client.delete(
            collection_name=collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value),
                        ),
                    ],
                )
            ),
        )
        logger.info(f"Deleted points from '{collection_name}' where {key}={value}")
        return True
    except Exception as e:
        logger.error(f"Error deleting points: {e}")
        raise

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
