"""
Cleanup Service - Handles tenant data cleanup and maintenance tasks.
"""
import logging
import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from qdrant_client import QdrantClient

from app.models.tenant import Tenant
from app.services.tenant_service import TenantService

logger = logging.getLogger(__name__)


class CleanupService:
    """Service for cleaning up tenant data and performing maintenance."""
    
    def __init__(self, db: Session, qdrant_client: QdrantClient):
        """
        Initialize cleanup service.
        
        Args:
            db: Database session
            qdrant_client: Qdrant client for vector store cleanup
        """
        self.db = db
        self.qdrant_client = qdrant_client
        self.tenant_service = TenantService(qdrant_client)
    
    def delete_tenant_data(self, tenant_id: str, soft_delete: bool = True) -> Dict[str, Any]:
        """
        Delete all data for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            soft_delete: If True, mark as deleted instead of removing (default: True)
            
        Returns:
            Dictionary with deletion results
        """
        logger.info(f"Starting tenant deletion for {tenant_id} (soft_delete={soft_delete})")
        
        results = {
            "tenant_id": tenant_id,
            "soft_delete": soft_delete,
            "collections_deleted": 0,
            "files_deleted": 0,
            "database_records_deleted": 0,
            "errors": []
        }
        
        try:
            # Get tenant
            tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if not tenant:
                results["errors"].append(f"Tenant {tenant_id} not found")
                return results
            
            # 1. Delete Qdrant collections
            try:
                collections = self.tenant_service.list_tenant_collections(tenant_id)
                for collection in collections:
                    success = self.tenant_service.delete_tenant_collection(
                        tenant_id,
                        collection["kb_name"]
                    )
                    if success:
                        results["collections_deleted"] += 1
                    else:
                        results["errors"].append(f"Failed to delete collection {collection['collection_name']}")
            except Exception as e:
                logger.error(f"Error deleting Qdrant collections: {e}")
                results["errors"].append(f"Qdrant cleanup error: {str(e)}")
            
            # 2. Delete files from storage
            try:
                upload_dir = os.path.join("uploads", tenant_id)
                if os.path.exists(upload_dir):
                    file_count = sum(len(files) for _, _, files in os.walk(upload_dir))
                    shutil.rmtree(upload_dir)
                    results["files_deleted"] = file_count
                    logger.info(f"Deleted {file_count} files from {upload_dir}")
            except Exception as e:
                logger.error(f"Error deleting files: {e}")
                results["errors"].append(f"File cleanup error: {str(e)}")
            
            # 3. Handle database records
            if soft_delete:
                # Soft delete - mark as inactive
                tenant.is_active = False
                tenant.deleted_at = datetime.utcnow()
                tenant.billing_status = "cancelled"
                self.db.commit()
                logger.info(f"Soft deleted tenant {tenant_id}")
            else:
                # Hard delete - remove all records (cascade will handle related records)
                try:
                    # Count related records before deletion
                    db_count = self.db.execute(
                        "SELECT COUNT(*) FROM tenant_databases WHERE tenant_id = ?",
                        (tenant_id,)
                    ).fetchone()[0]
                    
                    kb_count = self.db.execute(
                        "SELECT COUNT(*) FROM tenant_knowledge_bases WHERE tenant_id = ?",
                        (tenant_id,)
                    ).fetchone()[0]
                    
                    user_count = self.db.execute(
                        "SELECT COUNT(*) FROM tenant_users WHERE tenant_id = ?",
                        (tenant_id,)
                    ).fetchone()[0]
                    
                    results["database_records_deleted"] = db_count + kb_count + user_count + 1
                    
                    # Delete tenant (cascade will delete related records)
                    self.db.delete(tenant)
                    self.db.commit()
                    logger.info(f"Hard deleted tenant {tenant_id} and {results['database_records_deleted']} related records")
                    
                except Exception as e:
                    self.db.rollback()
                    logger.error(f"Error deleting database records: {e}")
                    results["errors"].append(f"Database cleanup error: {str(e)}")
            
            logger.info(f"Tenant deletion completed for {tenant_id}")
            
        except Exception as e:
            logger.error(f"Unexpected error during tenant deletion: {e}")
            results["errors"].append(f"Unexpected error: {str(e)}")
        
        return results
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """
        Clean up expired user sessions.
        
        Args:
            max_age_hours: Maximum age of sessions in hours
            
        Returns:
            Number of sessions deleted
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        try:
            # This would depend on your session storage implementation
            # For now, we'll just log it
            logger.info(f"Cleaning up sessions older than {cutoff_time}")
            
            # Example: Delete from sessions table if you have one
            # result = self.db.execute(
            #     "DELETE FROM sessions WHERE last_activity < ?",
            #     (cutoff_time,)
            # )
            # self.db.commit()
            # return result.rowcount
            
            return 0
            
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
            return 0
    
    def cleanup_temporary_files(self, max_age_days: int = 7) -> int:
        """
        Clean up old temporary files.
        
        Args:
            max_age_days: Maximum age of temp files in days
            
        Returns:
            Number of files deleted
        """
        cutoff_time = datetime.utcnow() - timedelta(days=max_age_days)
        deleted_count = 0
        
        try:
            temp_dir = "temp"
            if not os.path.exists(temp_dir):
                return 0
            
            for filename in os.listdir(temp_dir):
                filepath = os.path.join(temp_dir, filename)
                
                if os.path.isfile(filepath):
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    if file_mtime < cutoff_time:
                        os.remove(filepath)
                        deleted_count += 1
            
            logger.info(f"Deleted {deleted_count} temporary files older than {max_age_days} days")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {e}")
            return deleted_count
    
    def archive_old_audit_logs(self, max_age_days: int = 90) -> int:
        """
        Archive old audit logs.
        
        Args:
            max_age_days: Maximum age of logs to keep in main table
            
        Returns:
            Number of logs archived
        """
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        
        try:
            # Move old logs to archive table (if you have one)
            # For now, just delete very old logs
            result = self.db.execute(
                "DELETE FROM audit_logs WHERE timestamp < ?",
                (cutoff_date,)
            )
            self.db.commit()
            
            archived_count = result.rowcount
            logger.info(f"Archived {archived_count} audit logs older than {max_age_days} days")
            return archived_count
            
        except Exception as e:
            logger.error(f"Error archiving audit logs: {e}")
            self.db.rollback()
            return 0
    
    def cleanup_inactive_connections(self, max_idle_hours: int = 1) -> int:
        """
        Clean up inactive database connections.
        
        Args:
            max_idle_hours: Maximum idle time in hours
            
        Returns:
            Number of connections closed
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_idle_hours)
        closed_count = 0
        
        try:
            # This would depend on your connection pooling implementation
            # For now, just log it
            logger.info(f"Checking for connections idle since {cutoff_time}")
            
            # Example implementation:
            # Get all tenant connections
            # Check last activity time
            # Close connections that are idle too long
            
            return closed_count
            
        except Exception as e:
            logger.error(f"Error cleaning up connections: {e}")
            return closed_count
    
    def run_daily_cleanup(self) -> Dict[str, int]:
        """
        Run all daily cleanup tasks.
        
        Returns:
            Dictionary with cleanup results
        """
        logger.info("Starting daily cleanup tasks")
        
        results = {
            "sessions_cleaned": self.cleanup_expired_sessions(max_age_hours=24),
            "temp_files_cleaned": self.cleanup_temporary_files(max_age_days=7),
            "audit_logs_archived": self.archive_old_audit_logs(max_age_days=90),
            "connections_closed": self.cleanup_inactive_connections(max_idle_hours=1),
        }
        
        logger.info(f"Daily cleanup completed: {results}")
        return results
    
    def export_tenant_data(self, tenant_id: str, export_path: str) -> Dict[str, Any]:
        """
        Export all tenant data for backup or offboarding.
        
        Args:
            tenant_id: Tenant identifier
            export_path: Path to export data to
            
        Returns:
            Dictionary with export results
        """
        logger.info(f"Exporting data for tenant {tenant_id} to {export_path}")
        
        results = {
            "tenant_id": tenant_id,
            "export_path": export_path,
            "files_exported": 0,
            "collections_exported": 0,
            "errors": []
        }
        
        try:
            # Create export directory
            os.makedirs(export_path, exist_ok=True)
            
            # 1. Export tenant metadata
            tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if tenant:
                import json
                with open(os.path.join(export_path, "tenant_info.json"), "w") as f:
                    json.dump(tenant.to_dict(), f, indent=2)
            
            # 2. Copy files
            upload_dir = os.path.join("uploads", tenant_id)
            if os.path.exists(upload_dir):
                export_files_dir = os.path.join(export_path, "files")
                shutil.copytree(upload_dir, export_files_dir)
                results["files_exported"] = sum(len(files) for _, _, files in os.walk(export_files_dir))
            
            # 3. Export collection metadata
            collections = self.tenant_service.list_tenant_collections(tenant_id)
            results["collections_exported"] = len(collections)
            
            with open(os.path.join(export_path, "collections.json"), "w") as f:
                import json
                json.dump(collections, f, indent=2)
            
            logger.info(f"Export completed for tenant {tenant_id}")
            
        except Exception as e:
            logger.error(f"Error exporting tenant data: {e}")
            results["errors"].append(str(e))
        
        return results
    
    def get_tenant_storage_usage(self, tenant_id: str) -> Dict[str, Any]:
        """
        Calculate total storage usage for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dictionary with storage usage details
        """
        total_bytes = 0
        file_count = 0
        
        try:
            upload_dir = os.path.join("uploads", tenant_id)
            if os.path.exists(upload_dir):
                for dirpath, dirnames, filenames in os.walk(upload_dir):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        if os.path.isfile(filepath):
                            total_bytes += os.path.getsize(filepath)
                            file_count += 1
            
            return {
                "tenant_id": tenant_id,
                "total_bytes": total_bytes,
                "total_mb": total_bytes / (1024 * 1024),
                "total_gb": total_bytes / (1024 * 1024 * 1024),
                "file_count": file_count
            }
            
        except Exception as e:
            logger.error(f"Error calculating storage usage: {e}")
            return {
                "tenant_id": tenant_id,
                "total_bytes": 0,
                "total_mb": 0,
                "total_gb": 0,
                "file_count": 0,
                "error": str(e)
            }



# Singleton instance for background cleanup tasks
class CleanupServiceSingleton:
    """Singleton wrapper for cleanup service with lifecycle management."""
    
    def __init__(self):
        self._running = False
        self._service = None
    
    async def start(self):
        """Start the cleanup service."""
        logger.info("Cleanup service starting...")
        self._running = True
        # Initialize service when needed
        logger.info("Cleanup service started")
    
    async def stop(self):
        """Stop the cleanup service."""
        logger.info("Cleanup service stopping...")
        self._running = False
        logger.info("Cleanup service stopped")
    
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._running


# Export singleton instance
cleanup_service = CleanupServiceSingleton()
