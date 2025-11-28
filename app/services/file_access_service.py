"""
File Access Service for tenant-based file access control.
Ensures files can only be accessed by their owning tenant.
"""
import os
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class FileAccessService:
    """
    Service for managing tenant file access control and storage quotas.
    """
    
    def __init__(self, base_upload_dir: str = "uploads"):
        """
        Initialize file access service.
        
        Args:
            base_upload_dir: Base directory for file uploads
        """
        self.base_upload_dir = base_upload_dir
        logger.info(f"File access service initialized with base dir: {base_upload_dir}")
    
    def get_tenant_directory(self, tenant_id: str) -> str:
        """
        Get the directory path for a tenant's files.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Absolute path to tenant directory
        """
        return os.path.abspath(os.path.join(self.base_upload_dir, tenant_id))
    
    def verify_tenant_owns_file(self, tenant_id: str, file_path: str) -> bool:
        """
        Verify that a file belongs to the specified tenant.
        
        Args:
            tenant_id: Tenant identifier
            file_path: Path to file to verify
            
        Returns:
            True if tenant owns file, False otherwise
        """
        try:
            # Get absolute paths
            tenant_dir = self.get_tenant_directory(tenant_id)
            abs_file_path = os.path.abspath(file_path)
            
            # Check if file is within tenant directory
            is_owned = abs_file_path.startswith(tenant_dir)
            
            if not is_owned:
                logger.warning(
                    f"Access denied: Tenant {tenant_id} attempted to access "
                    f"file outside their directory: {file_path}"
                )
            
            return is_owned
            
        except Exception as e:
            logger.error(f"Error verifying file ownership: {e}")
            return False
    
    def get_safe_file_path(self, tenant_id: str, filename: str) -> str:
        """
        Get a safe file path within tenant directory.
        Prevents directory traversal attacks.
        
        Args:
            tenant_id: Tenant identifier
            filename: Requested filename
            
        Returns:
            Safe absolute file path
            
        Raises:
            ValueError: If filename contains path traversal attempts
        """
        # Remove any path components from filename
        safe_filename = os.path.basename(filename)
        
        # Check for suspicious patterns
        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            raise ValueError(f"Invalid filename: {filename}")
        
        tenant_dir = self.get_tenant_directory(tenant_id)
        file_path = os.path.join(tenant_dir, safe_filename)
        
        # Verify the resulting path is still within tenant directory
        if not os.path.abspath(file_path).startswith(tenant_dir):
            raise ValueError(f"Path traversal attempt detected: {filename}")
        
        return file_path
    
    def list_tenant_files(self, tenant_id: str) -> List[Dict[str, Any]]:
        """
        List all files for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            List of file information dictionaries
        """
        tenant_dir = self.get_tenant_directory(tenant_id)
        
        if not os.path.exists(tenant_dir):
            return []
        
        files = []
        
        try:
            for filename in os.listdir(tenant_dir):
                file_path = os.path.join(tenant_dir, filename)
                
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    files.append({
                        'filename': filename,
                        'size_bytes': stat.st_size,
                        'size_mb': round(stat.st_size / (1024 * 1024), 2),
                        'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'path': file_path
                    })
            
            logger.info(f"Listed {len(files)} files for tenant {tenant_id}")
            return files
            
        except Exception as e:
            logger.error(f"Error listing files for tenant {tenant_id}: {e}")
            return []
    
    def get_tenant_storage_usage(self, tenant_id: str) -> Dict[str, Any]:
        """
        Calculate storage usage for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dictionary with storage statistics
        """
        tenant_dir = self.get_tenant_directory(tenant_id)
        
        if not os.path.exists(tenant_dir):
            return {
                'tenant_id': tenant_id,
                'total_files': 0,
                'total_bytes': 0,
                'total_mb': 0,
                'total_gb': 0
            }
        
        total_bytes = 0
        file_count = 0
        
        try:
            for filename in os.listdir(tenant_dir):
                file_path = os.path.join(tenant_dir, filename)
                if os.path.isfile(file_path):
                    total_bytes += os.path.getsize(file_path)
                    file_count += 1
            
            return {
                'tenant_id': tenant_id,
                'total_files': file_count,
                'total_bytes': total_bytes,
                'total_mb': round(total_bytes / (1024 * 1024), 2),
                'total_gb': round(total_bytes / (1024 * 1024 * 1024), 3)
            }
            
        except Exception as e:
            logger.error(f"Error calculating storage for tenant {tenant_id}: {e}")
            return {
                'tenant_id': tenant_id,
                'total_files': 0,
                'total_bytes': 0,
                'total_mb': 0,
                'total_gb': 0,
                'error': str(e)
            }
    
    def delete_tenant_file(self, tenant_id: str, filename: str) -> bool:
        """
        Delete a file for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            filename: Name of file to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            file_path = self.get_safe_file_path(tenant_id, filename)
            
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                return False
            
            # Verify ownership
            if not self.verify_tenant_owns_file(tenant_id, file_path):
                logger.error(f"Tenant {tenant_id} does not own file: {filename}")
                return False
            
            os.remove(file_path)
            logger.info(f"Deleted file for tenant {tenant_id}: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file for tenant {tenant_id}: {e}")
            return False
    
    def delete_all_tenant_files(self, tenant_id: str) -> int:
        """
        Delete all files for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Number of files deleted
        """
        tenant_dir = self.get_tenant_directory(tenant_id)
        
        if not os.path.exists(tenant_dir):
            return 0
        
        deleted_count = 0
        
        try:
            for filename in os.listdir(tenant_dir):
                file_path = os.path.join(tenant_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    deleted_count += 1
            
            # Remove directory if empty
            if not os.listdir(tenant_dir):
                os.rmdir(tenant_dir)
            
            logger.info(f"Deleted {deleted_count} files for tenant {tenant_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting files for tenant {tenant_id}: {e}")
            return deleted_count
    
    def check_storage_quota(
        self,
        tenant_id: str,
        quota_mb: float,
        file_size_bytes: int = 0
    ) -> Dict[str, Any]:
        """
        Check if tenant is within storage quota.
        
        Args:
            tenant_id: Tenant identifier
            quota_mb: Storage quota in megabytes
            file_size_bytes: Size of file to be uploaded (optional)
            
        Returns:
            Dictionary with quota check results
        """
        usage = self.get_tenant_storage_usage(tenant_id)
        quota_bytes = quota_mb * 1024 * 1024
        
        current_usage_bytes = usage['total_bytes']
        projected_usage_bytes = current_usage_bytes + file_size_bytes
        
        within_quota = projected_usage_bytes <= quota_bytes
        
        return {
            'tenant_id': tenant_id,
            'quota_mb': quota_mb,
            'quota_bytes': quota_bytes,
            'current_usage_mb': usage['total_mb'],
            'current_usage_bytes': current_usage_bytes,
            'projected_usage_mb': round(projected_usage_bytes / (1024 * 1024), 2),
            'projected_usage_bytes': projected_usage_bytes,
            'within_quota': within_quota,
            'available_mb': round((quota_bytes - current_usage_bytes) / (1024 * 1024), 2),
            'usage_percent': round((current_usage_bytes / quota_bytes) * 100, 2) if quota_bytes > 0 else 0
        }
    
    def ensure_tenant_directory(self, tenant_id: str) -> str:
        """
        Ensure tenant directory exists.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Path to tenant directory
        """
        tenant_dir = self.get_tenant_directory(tenant_id)
        os.makedirs(tenant_dir, exist_ok=True)
        return tenant_dir


# Global instance
_file_access_service: Optional[FileAccessService] = None


def get_file_access_service() -> FileAccessService:
    """
    Get or create global file access service instance.
    
    Returns:
        FileAccessService instance
    """
    global _file_access_service
    
    if _file_access_service is None:
        _file_access_service = FileAccessService()
    
    return _file_access_service
