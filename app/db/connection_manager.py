"""
Secure connection manager for database credentials.
Uses encryption to store passwords safely.
"""
import json
import os
from pathlib import Path
from cryptography.fernet import Fernet
from typing import Dict, List, Optional
import base64
import hashlib


class ConnectionManager:
    """Manages secure storage of database connection credentials."""
    
    def __init__(self, storage_path: str = ".db_connections"):
        """
        Initialize the connection manager.
        
        Args:
            storage_path: Path to store encrypted connections
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.connections_file = self.storage_path / "connections.json"
        self.key_file = self.storage_path / ".key"
        self._ensure_key()
        
    def _ensure_key(self):
        """Ensure encryption key exists, create if not."""
        if not self.key_file.exists():
            # Generate a key from a machine-specific identifier
            # This makes the key unique to this machine
            key = Fernet.generate_key()
            self.key_file.write_bytes(key)
            # Make the key file read-only
            os.chmod(self.key_file, 0o600)
        
        self.cipher = Fernet(self.key_file.read_bytes())
    
    def _encrypt(self, text: str) -> str:
        """Encrypt a string."""
        if not text:
            return ""
        return self.cipher.encrypt(text.encode()).decode()
    
    def _decrypt(self, encrypted_text: str) -> str:
        """Decrypt a string."""
        if not encrypted_text:
            return ""
        return self.cipher.decrypt(encrypted_text.encode()).decode()
    
    def save_connection(self, name: str, connection_data: Dict) -> bool:
        """
        Save a database connection with encrypted password.
        
        Args:
            name: Unique name for this connection
            connection_data: Dict with keys: type, host, port, username, password, database, db_path
            
        Returns:
            True if saved successfully
        """
        try:
            # Load existing connections
            connections = self._load_connections()
            
            # Encrypt sensitive data
            encrypted_data = connection_data.copy()
            if 'password' in encrypted_data and encrypted_data['password']:
                encrypted_data['password'] = self._encrypt(encrypted_data['password'])
            
            # Save connection
            connections[name] = encrypted_data
            
            # Write to file
            self.connections_file.write_text(json.dumps(connections, indent=2))
            return True
            
        except Exception as e:
            print(f"Error saving connection: {e}")
            return False
    
    def load_connection(self, name: str) -> Optional[Dict]:
        """
        Load a database connection and decrypt password.
        
        Args:
            name: Name of the connection to load
            
        Returns:
            Connection data dict or None if not found
        """
        try:
            connections = self._load_connections()
            
            if name not in connections:
                return None
            
            connection_data = connections[name].copy()
            
            # Decrypt password
            if 'password' in connection_data and connection_data['password']:
                connection_data['password'] = self._decrypt(connection_data['password'])
            
            return connection_data
            
        except Exception as e:
            print(f"Error loading connection: {e}")
            return None
    
    def list_connections(self) -> List[str]:
        """
        Get list of saved connection names.
        
        Returns:
            List of connection names
        """
        try:
            connections = self._load_connections()
            return list(connections.keys())
        except Exception as e:
            print(f"Error listing connections: {e}")
            return []
    
    def delete_connection(self, name: str) -> bool:
        """
        Delete a saved connection.
        
        Args:
            name: Name of the connection to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            connections = self._load_connections()
            
            if name in connections:
                del connections[name]
                self.connections_file.write_text(json.dumps(connections, indent=2))
                return True
            
            return False
            
        except Exception as e:
            print(f"Error deleting connection: {e}")
            return False
    
    def get_connection_info(self, name: str) -> Optional[Dict]:
        """
        Get connection info without password (for display purposes).
        
        Args:
            name: Name of the connection
            
        Returns:
            Connection info dict without password
        """
        try:
            connections = self._load_connections()
            
            if name not in connections:
                return None
            
            info = connections[name].copy()
            # Remove password from display
            if 'password' in info:
                info['password'] = '********'
            
            return info
            
        except Exception as e:
            print(f"Error getting connection info: {e}")
            return None
    
    def _load_connections(self) -> Dict:
        """Load connections from file."""
        if not self.connections_file.exists():
            return {}
        
        try:
            return json.loads(self.connections_file.read_text())
        except json.JSONDecodeError:
            return {}


# Global instance
_connection_manager = None

def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
