"""
Services for QuickShip AI Agent
"""

from .qdrant_service import get_qdrant_client
from .rag_service import execute_query

__all__ = ["get_qdrant_client", "execute_query"]
