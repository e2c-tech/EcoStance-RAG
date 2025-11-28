"""
Connection Manager Service for per-tenant database connection pooling.
Manages connection lifecycle, health checks, and resource limits.
"""
import logging
import time
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from threading import Lock
from collections import defaultdict

from ..db.database_connector import DatabaseConnector

logger = logging.getLogger(__name__)


class ConnectionInfo:
    """Information about a database connection."""
    
    def __init__(self, tenant_id: str, db_id: str, connector: DatabaseConnector):
        self.tenant_id = tenant_id
        self.db_id = db_id
        self.connector = connector
        self.created_at = datetime.utcnow()
        self.last_used_at = datetime.utcnow()
        self.use_count = 0
        self.is_healthy = True
    
    def mark_used(self):
        """Mark connection as recently used."""
        self.last_used_at = datetime.utcnow()
        self.use_count += 1
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if connection has expired due to inactivity."""
        timeout = timedelta(minutes=timeout_minutes)
        return datetime.utcnow() - self.last_used_at > timeout
    
    def get_age_seconds(self) -> float:
        """Get connection age in seconds."""
        return (datetime.utcnow() - self.created_at).total_seconds()


class ConnectionManagerService:
    """
    Service for managing per-tenant database connections.
    Implements connection pooling, lifecycle management, and resource limits.
    """
    
    def __init__(
        self,
        max_connections_per_tenant: int = 5,
        connection_timeout_minutes: int = 30,
        cleanup_interval_seconds: int = 300
    ):
        """
        Initialize connection manager.
        
        Args:
            max_connections_per_tenant: Maximum connections per tenant
            connection_timeout_minutes: Idle timeout for connections
            cleanup_interval_seconds: Interval for cleanup task
        """
        self.max_connections_per_tenant = max_connections_per_tenant
        self.connection_timeout_minutes = connection_timeout_minutes
        self.cleanup_interval_seconds = cleanup_interval_seconds
        
        # Connection storage: {connection_key: ConnectionInfo}
        self._connections: Dict[str, ConnectionInfo] = {}
        
        # Tenant connection counts: {tenant_id: count}
        self._tenant_connection_counts: Dict[str, int] = defaultdict(int)
        
        # Thread safety
        self._lock = Lock()
        
        # Last cleanup time
        self._last_cleanup = time.time()
        
        logger.info(
            f"Connection manager initialized: "
            f"max_per_tenant={max_connections_per_tenant}, "
            f"timeout={connection_timeout_minutes}min"
        )
    
    def _get_connection_key(self, tenant_id: str, db_id: str) -> str:
        """
        Generate connection key from tenant_id and db_id.
        
        Args:
            tenant_id: Tenant identifier
            db_id: Database identifier
            
        Returns:
            Connection key string
        """
        return f"{tenant_id}:{db_id}"
    
    def _parse_connection_key(self, key: str) -> Tuple[str, str]:
        """
        Parse connection key into tenant_id and db_id.
        
        Args:
            key: Connection key
            
        Returns:
            Tuple of (tenant_id, db_id)
        """
        parts = key.split(':', 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return parts[0], ""
    
    def get_connection(
        self,
        tenant_id: str,
        db_id: str,
        connection_config: Optional[Dict[str, Any]] = None
    ) -> Optional[DatabaseConnector]:
        """
        Get or create a database connection for tenant.
        
        Args:
            tenant_id: Tenant identifier
            db_id: Database identifier
            connection_config: Connection configuration (required for new connections)
            
        Returns:
            DatabaseConnector instance or None if limit reached
            
        Raises:
            ValueError: If connection limit reached
            Exception: If connection creation fails
        """
        connection_key = self._get_connection_key(tenant_id, db_id)
        
        with self._lock:
            # Check if connection exists and is healthy
            if connection_key in self._connections:
                conn_info = self._connections[connection_key]
                
                # Test connection health
                if conn_info.connector.test_connection():
                    conn_info.mark_used()
                    logger.debug(f"Reusing connection: {connection_key}")
                    return conn_info.connector
                else:
                    # Connection is unhealthy, remove it
                    logger.warning(f"Connection unhealthy, removing: {connection_key}")
                    self._remove_connection(connection_key)
            
            # Check tenant connection limit
            if self._tenant_connection_counts[tenant_id] >= self.max_connections_per_tenant:
                logger.error(
                    f"Connection limit reached for tenant {tenant_id}: "
                    f"{self._tenant_connection_counts[tenant_id]}/{self.max_connections_per_tenant}"
                )
                raise ValueError(
                    f"Maximum connections ({self.max_connections_per_tenant}) "
                    f"reached for tenant {tenant_id}"
                )
            
            # Create new connection
            if connection_config is None:
                raise ValueError("connection_config required for new connections")
            
            logger.info(f"Creating new connection: {connection_key}")
            
            try:
                connector = DatabaseConnector()
                connector.connect(connection_config)
                
                # Store connection info
                conn_info = ConnectionInfo(tenant_id, db_id, connector)
                self._connections[connection_key] = conn_info
                self._tenant_connection_counts[tenant_id] += 1
                
                logger.info(
                    f"Connection created: {connection_key} "
                    f"(tenant total: {self._tenant_connection_counts[tenant_id]})"
                )
                
                return connector
                
            except Exception as e:
                logger.error(f"Failed to create connection {connection_key}: {e}")
                raise
    
    def _remove_connection(self, connection_key: str) -> bool:
        """
        Remove a connection (internal method, assumes lock is held).
        
        Args:
            connection_key: Connection key to remove
            
        Returns:
            True if removed, False if not found
        """
        if connection_key in self._connections:
            conn_info = self._connections[connection_key]
            
            # Close the connection
            try:
                conn_info.connector.close_connection()
            except Exception as e:
                logger.warning(f"Error closing connection {connection_key}: {e}")
            
            # Remove from tracking
            del self._connections[connection_key]
            self._tenant_connection_counts[conn_info.tenant_id] -= 1
            
            logger.info(
                f"Connection removed: {connection_key} "
                f"(tenant total: {self._tenant_connection_counts[conn_info.tenant_id]})"
            )
            return True
        
        return False
    
    def close_connection(self, tenant_id: str, db_id: str) -> bool:
        """
        Close a specific connection.
        
        Args:
            tenant_id: Tenant identifier
            db_id: Database identifier
            
        Returns:
            True if closed, False if not found
        """
        connection_key = self._get_connection_key(tenant_id, db_id)
        
        with self._lock:
            return self._remove_connection(connection_key)
    
    def close_tenant_connections(self, tenant_id: str) -> int:
        """
        Close all connections for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Number of connections closed
        """
        with self._lock:
            keys_to_remove = [
                key for key in self._connections.keys()
                if self._connections[key].tenant_id == tenant_id
            ]
            
            for key in keys_to_remove:
                self._remove_connection(key)
            
            logger.info(f"Closed {len(keys_to_remove)} connections for tenant {tenant_id}")
            return len(keys_to_remove)
    
    def cleanup_expired_connections(self) -> int:
        """
        Clean up expired connections based on timeout.
        
        Returns:
            Number of connections cleaned up
        """
        with self._lock:
            expired_keys = [
                key for key, conn_info in self._connections.items()
                if conn_info.is_expired(self.connection_timeout_minutes)
            ]
            
            for key in expired_keys:
                logger.info(f"Cleaning up expired connection: {key}")
                self._remove_connection(key)
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired connections")
            
            self._last_cleanup = time.time()
            return len(expired_keys)
    
    def check_and_cleanup(self):
        """
        Check if cleanup is needed and run if necessary.
        Called periodically or on connection requests.
        """
        if time.time() - self._last_cleanup > self.cleanup_interval_seconds:
            self.cleanup_expired_connections()
    
    def get_connection_stats(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get connection statistics.
        
        Args:
            tenant_id: Optional tenant ID to filter stats
            
        Returns:
            Dictionary with connection statistics
        """
        with self._lock:
            if tenant_id:
                # Stats for specific tenant
                tenant_connections = [
                    conn_info for conn_info in self._connections.values()
                    if conn_info.tenant_id == tenant_id
                ]
                
                return {
                    "tenant_id": tenant_id,
                    "active_connections": len(tenant_connections),
                    "max_connections": self.max_connections_per_tenant,
                    "connections": [
                        {
                            "db_id": conn.db_id,
                            "age_seconds": conn.get_age_seconds(),
                            "use_count": conn.use_count,
                            "last_used": conn.last_used_at.isoformat()
                        }
                        for conn in tenant_connections
                    ]
                }
            else:
                # System-wide stats
                return {
                    "total_connections": len(self._connections),
                    "total_tenants": len(self._tenant_connection_counts),
                    "connections_by_tenant": dict(self._tenant_connection_counts),
                    "max_per_tenant": self.max_connections_per_tenant,
                    "timeout_minutes": self.connection_timeout_minutes
                }
    
    def health_check(self, tenant_id: str, db_id: str) -> bool:
        """
        Check health of a specific connection.
        
        Args:
            tenant_id: Tenant identifier
            db_id: Database identifier
            
        Returns:
            True if healthy, False otherwise
        """
        connection_key = self._get_connection_key(tenant_id, db_id)
        
        with self._lock:
            if connection_key in self._connections:
                conn_info = self._connections[connection_key]
                is_healthy = conn_info.connector.test_connection()
                conn_info.is_healthy = is_healthy
                return is_healthy
        
        return False
    
    def close_all_connections(self) -> int:
        """
        Close all connections (for shutdown).
        
        Returns:
            Number of connections closed
        """
        with self._lock:
            count = len(self._connections)
            
            for key in list(self._connections.keys()):
                self._remove_connection(key)
            
            logger.info(f"Closed all {count} connections")
            return count


# Global instance
_connection_manager: Optional[ConnectionManagerService] = None


def get_connection_manager_service() -> ConnectionManagerService:
    """
    Get or create global connection manager instance.
    
    Returns:
        ConnectionManagerService instance
    """
    global _connection_manager
    
    if _connection_manager is None:
        _connection_manager = ConnectionManagerService()
    
    return _connection_manager
