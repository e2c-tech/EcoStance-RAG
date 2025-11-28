"""
Qdrant Service for Vector Database Operations
"""

from qdrant_client import QdrantClient
from ..config import QDRANT_URL, QDRANT_API_KEY


def get_qdrant_client():
    """
    Initializes and returns the Qdrant client using credentials from the config.
    """
    if not QDRANT_URL or not QDRANT_API_KEY:
        raise ValueError("QDRANT_URL and QDRANT_API_KEY must be set in environment variables.")
    
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return client
