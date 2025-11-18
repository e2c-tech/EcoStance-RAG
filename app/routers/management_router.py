from fastapi import APIRouter, Form, HTTPException, Body
from typing import List

from app.services.management_service import (
    get_all_knowledge_bases, 
    delete_knowledge_base, 
    reindex_document,
    get_knowledge_base_details,
    get_knowledge_base_files,
    delete_file_from_knowledge_base
)

router = APIRouter()

@router.get("/knowledge-bases/", response_model=List[str])
async def list_knowledge_bases():
    """
    Lists all available knowledge bases (Qdrant collections).
    """
    try:
        return get_all_knowledge_bases()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve knowledge bases: {e}")

@router.delete("/knowledge-bases/{collection_name}")
async def delete_knowledge_base_endpoint(collection_name: str):
    """
    Deletes a specific knowledge base (Qdrant collection).
    """
    try:
        success = delete_knowledge_base(collection_name)
        if success:
            return {"message": f"Knowledge base '{collection_name}' deleted successfully."}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to delete knowledge base '{collection_name}'.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/knowledge-bases/{collection_name}/details")
async def get_knowledge_base_details_endpoint(collection_name: str):
    """
    Get detailed information about a knowledge base including all indexed files.
    """
    try:
        details = get_knowledge_base_details(collection_name)
        return details
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get knowledge base details: {e}")

@router.get("/knowledge-bases/{collection_name}/files")
async def get_knowledge_base_files_endpoint(collection_name: str):
    """
    Get all files indexed in a specific knowledge base.
    """
    try:
        files = get_knowledge_base_files(collection_name)
        return {"collection_name": collection_name, "files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get knowledge base files: {e}")

@router.delete("/knowledge-bases/{collection_name}/files/{filename}")
async def delete_file_endpoint(collection_name: str, filename: str):
    """
    Delete a specific file from a knowledge base.
    """
    try:
        success = delete_file_from_knowledge_base(collection_name, filename)
        if success:
            return {"message": f"File '{filename}' deleted successfully from '{collection_name}'."}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to delete file '{filename}'.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/knowledge-bases/{collection_name}/files/{filename}/reindex")
async def reindex_file_endpoint(collection_name: str, filename: str):
    """
    Re-index a specific file in a knowledge base.
    """
    try:
        reindex_document(filename, collection_name)
        return {"message": f"Successfully initiated re-indexing for '{filename}' in collection '{collection_name}'."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to re-index file: {e}")

@router.post("/reindex/")
async def reindex_document_endpoint(
    file_path: str = Form(...),
    collection_name: str = Form(...)
):
    """
    Re-indexes a document. This process first deletes all existing data associated
    with the file from the specified collection and then re-runs the full
    ingestion pipeline on the file.
    """
    try:
        reindex_document(file_path, collection_name)
        return {"message": f"Successfully initiated re-indexing for '{file_path}' in collection '{collection_name}'."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to re-index document: {e}")
