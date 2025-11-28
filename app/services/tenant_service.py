"""
Tenant Service for managing tenant-specific Qdrant collections.
Provides collection isolation and naming conventions for multitenancy.
"""
import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

from app.config import EMBEDDING_VECTOR_SIZE, DISTANCE_METRIC

logger = logging.getLogger(__name__)


class TenantService:
    """
    Service for managing tenant-specific Qdrant collections.
    Implements collection naming conventions and isolation.
    """
    
    COLLECTION_PREFIX = "tenant"
    SEPARATOR = "_"
    
    def __init__(self, qdrant_client: QdrantClient):
        """
        Initialize tenant service with Qdrant client.
        
        Args:
            qdrant_client: Initialized Qdrant client
        """
        self.client = qdrant_client
    
    def get_collection_name(self, tenant_id: str, kb_name: str) -> str:
        """
        Generate tenant-specific collection name.
        
        Format: tenant_{tenant_id}_{kb_name}
        
        Args:
            tenant_id: Tenant identifier
            kb_name: Knowledge base name
            
        Returns:
            Formatted collection name
            
        Example:
            >>> get_collection_name("acme-corp", "docs")
            "tenant_acme-corp_docs"
        """
        # Sanitize names to ensure valid collection names
        safe_tenant_id = self._sanitize_name(tenant_id)
        safe_kb_name = self._sanitize_name(kb_name)
        
        collection_name = f"{self.COLLECTION_PREFIX}{self.SEPARATOR}{safe_tenant_id}{self.SEPARATOR}{safe_kb_name}"
        
        logger.debug(f"Generated collection name: {collection_name}")
        return collection_name
    
    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize name for use in collection names.
        Replaces invalid characters with underscores.
        
        Args:
            name: Name to sanitize
            
        Returns:
            Sanitized name
        """
        # Replace spaces and special characters with underscores
        import re
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        # Remove consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        return sanitized.lower()
    
    def parse_collection_name(self, collection_name: str) -> Optional[Dict[str, str]]:
        """
        Parse collection name to extract tenant_id and kb_name.
        
        Args:
            collection_name: Collection name to parse
            
        Returns:
            Dictionary with tenant_id and kb_name, or None if invalid format
            
        Example:
            >>> parse_collection_name("tenant_acme-corp_docs")
            {"tenant_id": "acme-corp", "kb_name": "docs"}
        """
        parts = collection_name.split(self.SEPARATOR)
        
        if len(parts) >= 3 and parts[0] == self.COLLECTION_PREFIX:
            return {
                "tenant_id": parts[1],
                "kb_name": self.SEPARATOR.join(parts[2:])
            }
        
        return None
    
    def create_tenant_collection(
        self,
        tenant_id: str,
        kb_name: str,
        vector_size: Optional[int] = None,
        distance: Optional[str] = None
    ) -> str:
        """
        Create a new tenant-specific collection in Qdrant.
        
        Args:
            tenant_id: Tenant identifier
            kb_name: Knowledge base name
            vector_size: Vector dimension (default from config)
            distance: Distance metric (default from config)
            
        Returns:
            Created collection name
            
        Raises:
            Exception: If collection creation fails
        """
        collection_name = self.get_collection_name(tenant_id, kb_name)
        
        # Check if collection already exists
        if self.collection_exists(collection_name):
            logger.info(f"Collection '{collection_name}' already exists")
            return collection_name
        
        # Use defaults from config if not provided
        vector_size = vector_size or EMBEDDING_VECTOR_SIZE
        distance = distance or DISTANCE_METRIC
        
        try:
            logger.info(f"Creating collection '{collection_name}' for tenant {tenant_id}")
            
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=distance
                ),
            )
            
            # Create payload indexes for common fields
            self._create_payload_indexes(collection_name)
            
            logger.info(f"Collection '{collection_name}' created successfully")
            return collection_name
            
        except Exception as e:
            logger.error(f"Failed to create collection '{collection_name}': {e}")
            raise
    
    def _create_payload_indexes(self, collection_name: str) -> None:
        """
        Create payload indexes for common query fields.
        
        Args:
            collection_name: Collection to create indexes for
        """
        indexes = [
            ("source_filename", models.PayloadSchemaType.KEYWORD),
            ("tenant_id", models.PayloadSchemaType.KEYWORD),
            ("chunk_index", models.PayloadSchemaType.INTEGER),
        ]
        
        for field_name, field_type in indexes:
            try:
                self.client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=field_type,
                    wait=True
                )
                logger.debug(f"Created index for '{field_name}' in '{collection_name}'")
            except Exception as e:
                logger.warning(f"Could not create index for '{field_name}': {e}")
    
    def delete_tenant_collection(self, tenant_id: str, kb_name: str) -> bool:
        """
        Delete a tenant-specific collection.
        
        Args:
            tenant_id: Tenant identifier
            kb_name: Knowledge base name
            
        Returns:
            True if deleted successfully, False otherwise
        """
        collection_name = self.get_collection_name(tenant_id, kb_name)
        
        try:
            logger.info(f"Deleting collection '{collection_name}' for tenant {tenant_id}")
            
            result = self.client.delete_collection(collection_name=collection_name)
            
            if result:
                logger.info(f"Collection '{collection_name}' deleted successfully")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete collection '{collection_name}': {e}")
            return False
    
    def list_tenant_collections(self, tenant_id: str) -> List[Dict[str, Any]]:
        """
        List all collections for a specific tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            List of collection information dictionaries
        """
        try:
            all_collections = self.client.get_collections()
            tenant_prefix = f"{self.COLLECTION_PREFIX}{self.SEPARATOR}{self._sanitize_name(tenant_id)}{self.SEPARATOR}"
            
            tenant_collections = []
            
            for collection in all_collections.collections:
                if collection.name.startswith(tenant_prefix):
                    parsed = self.parse_collection_name(collection.name)
                    
                    if parsed and parsed["tenant_id"] == self._sanitize_name(tenant_id):
                        # Get collection details
                        try:
                            info = self.client.get_collection(collection_name=collection.name)
                            tenant_collections.append({
                                "collection_name": collection.name,
                                "kb_name": parsed["kb_name"],
                                "vector_count": info.vectors_count,
                                "points_count": info.points_count,
                            })
                        except Exception as e:
                            logger.warning(f"Could not get info for collection '{collection.name}': {e}")
            
            logger.info(f"Found {len(tenant_collections)} collections for tenant {tenant_id}")
            return tenant_collections
            
        except Exception as e:
            logger.error(f"Failed to list collections for tenant {tenant_id}: {e}")
            return []
    
    def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists in Qdrant.
        
        Args:
            collection_name: Collection name to check
            
        Returns:
            True if collection exists, False otherwise
        """
        try:
            self.client.get_collection(collection_name=collection_name)
            return True
        except UnexpectedResponse:
            return False
        except Exception as e:
            logger.error(f"Error checking collection existence: {e}")
            return False
    
    def get_collection_info(self, tenant_id: str, kb_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a tenant collection.
        
        Args:
            tenant_id: Tenant identifier
            kb_name: Knowledge base name
            
        Returns:
            Collection information dictionary or None if not found
        """
        collection_name = self.get_collection_name(tenant_id, kb_name)
        
        try:
            info = self.client.get_collection(collection_name=collection_name)
            
            return {
                "collection_name": collection_name,
                "tenant_id": tenant_id,
                "kb_name": kb_name,
                "vector_count": info.vectors_count,
                "points_count": info.points_count,
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance,
                "indexed_fields": list(info.payload_schema.keys()) if info.payload_schema else [],
            }
            
        except UnexpectedResponse:
            logger.warning(f"Collection '{collection_name}' not found")
            return None
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return None
    
    def verify_tenant_access(self, tenant_id: str, collection_name: str) -> bool:
        """
        Verify that a collection belongs to the specified tenant.
        
        Args:
            tenant_id: Tenant identifier
            collection_name: Collection name to verify
            
        Returns:
            True if collection belongs to tenant, False otherwise
        """
        parsed = self.parse_collection_name(collection_name)
        
        if not parsed:
            return False
        
        return parsed["tenant_id"] == self._sanitize_name(tenant_id)


# Global instance (will be initialized with client)
_tenant_service: Optional[TenantService] = None


def get_tenant_service(qdrant_client: QdrantClient) -> TenantService:
    """
    Get or create tenant service instance.
    
    Args:
        qdrant_client: Qdrant client instance
        
    Returns:
        TenantService instance
    """
    global _tenant_service
    
    if _tenant_service is None:
        _tenant_service = TenantService(qdrant_client)
    
    return _tenant_service
