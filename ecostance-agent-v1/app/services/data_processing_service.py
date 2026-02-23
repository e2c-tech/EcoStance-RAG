from typing import List, Dict, Any
import os
import anyio

from .extraction_service import extract_data_from_file
from .cleaning_service import clean_and_enrich_blocks
from .chunking_service import chunk_blocks
from .embedding_service import load_embedding_model, create_embeddings
from .qdrant_service import get_qdrant_client, create_collection_if_not_exists, upload_to_qdrant
from .kb_service import add_kb

# --- Global Service Initialization ---
# Load the embedding model and Qdrant client once when the service starts.
# This is crucial for performance, avoiding reconnection on every API call.
embedding_model = load_embedding_model()
qdrant_client = get_qdrant_client()

async def process_and_upload_file(
    file_path: str, 
    collection_name: str = "default_collection", 
    job_id: str = None,
    tenant_id: str = None
):
    """
    Orchestrates the full data pipeline: Extract -> Clean -> Chunk -> Embed -> Upload.

    Args:
        file_path (str): The path to the raw file.
        collection_name (str): The name of the Qdrant collection to upload to.
        job_id (str, optional): Job ID for progress tracking.
        tenant_id (str, optional): Tenant ID for multitenancy isolation.
    """
    from .job_service import job_tracker
    
    def update_progress(message: str):
        """Helper to update job progress if job_id is provided."""
        print(message)
        if job_id:
            job_tracker.update_progress(job_id, message)
    
    update_progress(f"--- Starting full processing pipeline for file: {os.path.basename(file_path)} ---")
    
    try:
        # 1. Extraction Stage
        update_progress("Step 1/5: Starting document extraction...")
        raw_blocks, _ = await extract_data_from_file(file_path)
        update_progress(f"Step 1/5: Extraction complete. Found {len(raw_blocks)} blocks.")

        # 2. Cleaning Stage
        update_progress("Step 2/5: Starting data cleaning and enrichment...")
        enriched_blocks = await anyio.to_thread.run_sync(clean_and_enrich_blocks, raw_blocks)
        update_progress(f"Step 2/5: Cleaning complete. {len(enriched_blocks)} blocks remain after cleaning.")

        # 3. Chunking Stage
        update_progress("Step 3/5: Starting text chunking...")
        final_chunks = await anyio.to_thread.run_sync(chunk_blocks, enriched_blocks)
        update_progress(f"Step 3/5: Chunking complete. Generated {len(final_chunks)} chunks.")

        # 4. Embedding Stage
        update_progress("Step 4/5: Starting embedding generation...")
        chunks_with_embeddings = await anyio.to_thread.run_sync(create_embeddings, final_chunks, embedding_model)
        update_progress(f"Step 4/5: Embedding complete. All {len(chunks_with_embeddings)} chunks have been embedded.")

        # 5. Qdrant Upload Stage
        update_progress("Step 5/5: Starting upload to vector database...")
        # Ensure the target collection exists before uploading.
        await anyio.to_thread.run_sync(create_collection_if_not_exists, qdrant_client, collection_name)
        add_kb(collection_name)
        # Upload the final, processed data to Qdrant with tenant context.
        await anyio.to_thread.run_sync(upload_to_qdrant, qdrant_client, collection_name, chunks_with_embeddings, tenant_id)
        update_progress(f"Step 5/5: Upload to Qdrant complete.")
        update_progress(f"--- Pipeline finished successfully for file: {os.path.basename(file_path)} ---")

        if job_id:
            job_tracker.complete_job(job_id)
            
    except Exception as e:
        error_msg = f"Processing failed: {str(e)}"
        update_progress(error_msg)
        if job_id:
            job_tracker.fail_job(job_id, error_msg)
        raise
