from .qdrant_service import get_qdrant_client, delete_collection as delete_qdrant_collection
from .data_processing_service import process_and_upload_file
from .kb_service import get_all_kbs, remove_kb
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def get_all_knowledge_bases():
    """
    Retrieves a list of all knowledge bases from the persistent store.
    """
    return get_all_kbs()

def delete_knowledge_base(collection_name: str):
    """
    Deletes a knowledge base (collection) from Qdrant and the persistent store.
    """
    client = get_qdrant_client()
    if delete_qdrant_collection(client, collection_name):
        remove_kb(collection_name)
        return True
    return False

def delete_points_by_filename(client, collection_name: str, filename: str):
    """
    Deletes all points from a collection that are associated with a specific filename.
    """
    filter_ = Filter(
        must=[
            FieldCondition(
                key="source_filename",  # Corrected key to be top-level
                match=MatchValue(value=filename)
            )
        ]
    )
    client.delete(collection_name=collection_name, points_selector=filter_, wait=True)

def get_knowledge_base_files(collection_name: str) -> List[Dict[str, Any]]:
    """
    Retrieves all files indexed in a specific knowledge base with their metadata.
    """
    client = get_qdrant_client()
    
    try:
        # Get all points from the collection with their payloads
        scroll_result = client.scroll(
            collection_name=collection_name,
            limit=10000,  # Adjust based on your needs
            with_payload=True,
            with_vectors=False  # We don't need vectors for this
        )
        
        points = scroll_result[0]  # First element contains the points
        
        # Group by source filename and collect metadata
        files_info = {}
        
        for point in points:
            payload = point.payload
            # Access source_filename from the top-level payload
            source_filename = payload.get('source_filename', 'Unknown')
            
            if source_filename not in files_info:
                files_info[source_filename] = {
                    'filename': source_filename,
                    'chunk_count': 0,
                    'file_type': payload.get('doc_type', 'Unknown'), # Corrected from file_type
                    'upload_date': payload.get('ingest_timestamp', 'Unknown'),
                    'file_size': payload.get('file_size', 'Unknown'),
                    'total_characters': 0
                }
            
            files_info[source_filename]['chunk_count'] += 1
            files_info[source_filename]['total_characters'] += len(payload.get('text', ''))
        
        return list(files_info.values())
        
    except Exception as e:
        logger.error(f"Error retrieving files for collection {collection_name}: {e}")
        return []

def get_knowledge_base_details(collection_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a knowledge base including files and stats.
    """
    client = get_qdrant_client()
    
    try:
        # Get collection info
        collection_info = client.get_collection(collection_name=collection_name)
        
        # Get files information
        files = get_knowledge_base_files(collection_name)
        
        return {
            'name': collection_name,
            'vectors_count': collection_info.points_count,
            'vector_size': collection_info.config.params.vectors.size,
            'files_count': len(files),
            'files': files
        }
        
    except Exception as e:
        logger.error(f"Error getting details for collection {collection_name}: {e}")
        return {
            'name': collection_name,
            'error': str(e),
            'vectors_count': 0,
            'files_count': 0,
            'files': []
        }

def delete_file_from_knowledge_base(collection_name: str, filename: str) -> bool:
    """
    Deletes all points associated with a specific file from the knowledge base.
    """
    client = get_qdrant_client()
    
    try:
        delete_points_by_filename(client, collection_name, filename)
        logger.info(f"Successfully deleted file '{filename}' from collection '{collection_name}'")
        return True
    except Exception as e:
        logger.error(f"Error deleting file '{filename}' from collection '{collection_name}': {e}")
        return False

def reindex_document(file_path: str, collection_name: str):
    """
    Re-indexes a document by first deleting all its existing points from the
    collection and then running the full processing and upload pipeline again.
    """
    client = get_qdrant_client()
    
    # First, delete all existing points for this filename.
    delete_points_by_filename(client, collection_name, file_path)
    
    # Now, re-process and upload the file.
    process_and_upload_file(file_path, collection_name)
