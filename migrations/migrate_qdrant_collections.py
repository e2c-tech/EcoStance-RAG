"""
Qdrant Collection Migration Tool
Migrates existing collections to tenant-specific naming convention.
"""
import os
import sys
from typing import List, Dict, Any
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

# Load environment variables
load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
DEFAULT_TENANT_ID = "default-tenant"


def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client."""
    if not QDRANT_URL or not QDRANT_API_KEY:
        print("ERROR: QDRANT_URL and QDRANT_API_KEY must be set")
        sys.exit(1)
    
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


def list_collections(client: QdrantClient) -> List[str]:
    """List all collections."""
    collections = client.get_collections()
    return [c.name for c in collections.collections]


def is_tenant_collection(collection_name: str) -> bool:
    """Check if collection already follows tenant naming convention."""
    return collection_name.startswith("tenant_")


def generate_tenant_collection_name(kb_name: str, tenant_id: str = DEFAULT_TENANT_ID) -> str:
    """Generate tenant-specific collection name."""
    return f"tenant_{tenant_id}_{kb_name}"


def migrate_collection(
    client: QdrantClient,
    old_name: str,
    new_name: str,
    batch_size: int = 100
) -> bool:
    """
    Migrate a collection to new name by copying all points.
    
    Args:
        client: Qdrant client
        old_name: Original collection name
        new_name: New tenant-specific collection name
        batch_size: Number of points to copy per batch
        
    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"\n→ Migrating '{old_name}' to '{new_name}'...")
        
        # Get old collection info
        old_collection = client.get_collection(collection_name=old_name)
        print(f"  Source collection has {old_collection.points_count} points")
        
        # Create new collection with same configuration
        print(f"  Creating new collection '{new_name}'...")
        client.create_collection(
            collection_name=new_name,
            vectors_config=old_collection.config.params.vectors
        )
        
        # Copy all points in batches
        offset = None
        total_copied = 0
        
        while True:
            # Scroll through points
            points, next_offset = client.scroll(
                collection_name=old_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=True
            )
            
            if not points:
                break
            
            # Add tenant_id to payload
            updated_points = []
            for point in points:
                payload = point.payload or {}
                payload["tenant_id"] = DEFAULT_TENANT_ID
                
                updated_points.append(
                    PointStruct(
                        id=point.id,
                        vector=point.vector,
                        payload=payload
                    )
                )
            
            # Upload to new collection
            client.upsert(
                collection_name=new_name,
                points=updated_points,
                wait=True
            )
            
            total_copied += len(points)
            print(f"  Copied {total_copied}/{old_collection.points_count} points...")
            
            if next_offset is None:
                break
            
            offset = next_offset
        
        # Verify migration
        new_collection = client.get_collection(collection_name=new_name)
        if new_collection.points_count == old_collection.points_count:
            print(f"✓ Migration successful: {total_copied} points copied")
            return True
        else:
            print(f"✗ Migration incomplete: {new_collection.points_count}/{old_collection.points_count} points")
            return False
            
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False


def migrate_all_collections(client: QdrantClient, delete_old: bool = False):
    """
    Migrate all non-tenant collections to tenant naming convention.
    
    Args:
        client: Qdrant client
        delete_old: Whether to delete old collections after migration
    """
    collections = list_collections(client)
    
    print(f"\nFound {len(collections)} collection(s)")
    print("=" * 60)
    
    # Filter collections that need migration
    to_migrate = [c for c in collections if not is_tenant_collection(c)]
    
    if not to_migrate:
        print("No collections need migration")
        return
    
    print(f"\nCollections to migrate: {len(to_migrate)}")
    for collection in to_migrate:
        print(f"  - {collection}")
    
    print("\n" + "=" * 60)
    
    # Migrate each collection
    migrated = []
    failed = []
    
    for old_name in to_migrate:
        new_name = generate_tenant_collection_name(old_name)
        
        # Check if target already exists
        if new_name in collections:
            print(f"⊘ Skipping '{old_name}' - target '{new_name}' already exists")
            continue
        
        success = migrate_collection(client, old_name, new_name)
        
        if success:
            migrated.append((old_name, new_name))
        else:
            failed.append(old_name)
    
    # Summary
    print("\n" + "=" * 60)
    print(f"\nMigration Summary:")
    print(f"  Successful: {len(migrated)}")
    print(f"  Failed: {len(failed)}")
    
    if migrated:
        print(f"\nMigrated collections:")
        for old, new in migrated:
            print(f"  {old} → {new}")
    
    if failed:
        print(f"\nFailed migrations:")
        for name in failed:
            print(f"  {name}")
    
    # Optionally delete old collections
    if delete_old and migrated:
        print("\n" + "=" * 60)
        response = input("\nDelete old collections? (type 'DELETE' to confirm): ")
        
        if response == "DELETE":
            print("\nDeleting old collections...")
            for old_name, _ in migrated:
                try:
                    client.delete_collection(collection_name=old_name)
                    print(f"✓ Deleted '{old_name}'")
                except Exception as e:
                    print(f"✗ Failed to delete '{old_name}': {e}")
        else:
            print("Deletion cancelled")


def verify_migration(client: QdrantClient):
    """Verify migration by listing all collections."""
    collections = list_collections(client)
    
    print("\nCurrent Collections:")
    print("=" * 60)
    
    tenant_collections = [c for c in collections if is_tenant_collection(c)]
    other_collections = [c for c in collections if not is_tenant_collection(c)]
    
    if tenant_collections:
        print(f"\nTenant Collections ({len(tenant_collections)}):")
        for name in tenant_collections:
            info = client.get_collection(collection_name=name)
            print(f"  ✓ {name} ({info.points_count} points)")
    
    if other_collections:
        print(f"\nNon-Tenant Collections ({len(other_collections)}):")
        for name in other_collections:
            info = client.get_collection(collection_name=name)
            print(f"  ⚠ {name} ({info.points_count} points)")
    
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Qdrant Collection Migration Tool")
    parser.add_argument(
        "command",
        choices=["migrate", "verify", "list"],
        help="Command to run"
    )
    parser.add_argument(
        "--delete-old",
        action="store_true",
        help="Delete old collections after successful migration"
    )
    
    args = parser.parse_args()
    
    client = get_qdrant_client()
    
    if args.command == "migrate":
        migrate_all_collections(client, delete_old=args.delete_old)
    elif args.command == "verify":
        verify_migration(client)
    elif args.command == "list":
        collections = list_collections(client)
        print(f"\nAll Collections ({len(collections)}):")
        for name in collections:
            info = client.get_collection(collection_name=name)
            tenant = "✓ Tenant" if is_tenant_collection(name) else "⚠ Legacy"
            print(f"  [{tenant}] {name} ({info.points_count} points)")
