"""
Multilingual Embedding Service for Document Processing
Parallel implementation using BGE-M3 for multilingual document embedding
"""

import torch
import logging
from typing import List, Dict, Any, Optional
from threading import Lock
import numpy as np
import httpx
import hashlib

from .langsmith_service import trace_embedding
from app.config import USE_REMOTE_EMBEDDING, EMBEDDING_SERVER_URL

logger = logging.getLogger(__name__)

# Global multilingual embedding model instance (singleton pattern)
_multilingual_embedding_model: Optional[Any] = None
_multilingual_embedding_model_lock = Lock()

# Configuration
MULTILINGUAL_ENABLED = False  # Will be set from config
BGE_M3_MODEL_NAME = "BAAI/bge-m3"
BGE_M3_BATCH_SIZE = 128
BGE_M3_MAX_LENGTH = 8192
BGE_M3_NORMALIZE = True

def set_multilingual_config(enabled: bool, model_name: str = None, batch_size: int = None):
    """Set multilingual configuration from app config."""
    global MULTILINGUAL_ENABLED, BGE_M3_MODEL_NAME, BGE_M3_BATCH_SIZE
    MULTILINGUAL_ENABLED = enabled
    if model_name:
        BGE_M3_MODEL_NAME = model_name
    if batch_size:
        BGE_M3_BATCH_SIZE = batch_size

@trace_embedding
def load_multilingual_embedding_model():
    """
    Load BGE-M3 multilingual embedding model. 
    If USE_REMOTE_EMBEDDING is enabled, returns None to save memory.
    """
    if USE_REMOTE_EMBEDDING:
        return None
    
    if not MULTILINGUAL_ENABLED:
        logger.info("Multilingual embedding disabled")
        return None
    
    # Double-checked locking pattern for thread-safe singleton
    if _multilingual_embedding_model is None:
        with _multilingual_embedding_model_lock:
            if _multilingual_embedding_model is None:
                try:
                    # Check if model names match to reuse the main singleton
                    from .embedding_service import load_embedding_model
                    from app.config import EMBEDDING_MODEL_NAME as MAIN_MODEL
                    
                    if BGE_M3_MODEL_NAME == MAIN_MODEL or BGE_M3_MODEL_NAME == "BAAI/bge-m3":
                        logger.info("Reusing main embedding singleton for multilingual tasks to save memory")
                        _multilingual_embedding_model = load_embedding_model()
                    else:
                        from FlagEmbedding import BGEM3FlagModel
                        # Determine device
                        device = 'cuda' if torch.cuda.is_available() else 'cpu'
                        logger.info(f"Loading separate BGE-M3 model on {device}")
                        _multilingual_embedding_model = BGEM3FlagModel(
                            BGE_M3_MODEL_NAME,
                            use_fp16=device == "cuda",
                            device=device
                        )
                    
                    logger.info("✓ Multilingual embedding model provider ready")
                    
                except Exception as e:
                    logger.error(f"Failed to load multilingual model: {e}")
                    return None
    
    return _multilingual_embedding_model

def unload_multilingual_embedding_model():
    """Unload the multilingual embedding model from memory."""
    global _multilingual_embedding_model
    
    if _multilingual_embedding_model is not None:
        with _multilingual_embedding_model_lock:
            if _multilingual_embedding_model is not None:
                try:
                    del _multilingual_embedding_model
                    _multilingual_embedding_model = None
                    
                    # Clear CUDA cache if using GPU
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    
                    logger.info("✓ Multilingual embedding model unloaded successfully")
                except Exception as e:
                    logger.error(f"Error unloading multilingual embedding model: {e}")

@trace_embedding
def create_multilingual_embeddings(chunks: List[Dict[str, Any]], model=None, tenant_id: str = None) -> List[Dict[str, Any]]:
    """
    Generate multilingual embeddings using BGE-M3 with Cache Deduplication.
    
    Args:
        chunks: List of processed data chunks with language metadata
        model: BGE-M3 model instance (optional, will load if None)
        tenant_id: Optional string for the tenant cache
        
    Returns:
        Chunks with multilingual embeddings attached
    """
    if not MULTILINGUAL_ENABLED:
        logger.warning("Multilingual embedding called but not enabled")
        return chunks
    
    if model is None and not USE_REMOTE_EMBEDDING:
        model = load_multilingual_embedding_model()
        
    if model is None and not USE_REMOTE_EMBEDDING:
        logger.error("Could not load multilingual embedding model")
        return chunks
    
    try:
        from app.db.database import SessionLocal
        from app.models.embedding_cache import EmbeddingCache
        from sqlalchemy.exc import IntegrityError
        
        db = SessionLocal()
        
        # 1. Identify all chunks and their hashes
        all_chunk_data = [] # List of tuples: (text_hash, text, chunk_ref)
        hash_list = []
        
        for chunk in chunks:
            text = chunk.get('text', '')
            if len(text) > BGE_M3_MAX_LENGTH:
                text = text[:BGE_M3_MAX_LENGTH]
            
            chunk['metadata'] = chunk.get('metadata', {})
            text_hash = chunk['metadata'].get('normalized_text_hash')
            if not text_hash:
                text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
                chunk['metadata']['normalized_text_hash'] = text_hash
                
            all_chunk_data.append((text_hash, text, chunk))
            hash_list.append(text_hash)
            
        # 2. Bulk query the cache
        db_cache = {}
        try:
            cached_records = db.query(EmbeddingCache).filter(
                EmbeddingCache.text_hash.in_(hash_list),
                EmbeddingCache.model_name == BGE_M3_MODEL_NAME,
                EmbeddingCache.tenant_id == tenant_id
            ).all()
            db_cache = {record.text_hash: record.vector for record in cached_records}
            logger.info(f"Cache hit: Found {len(db_cache)} vectors in cache out of {len(chunks)} chunks.")
        except Exception as e:
            logger.warning(f"Failed to query embedding cache: {e}")

        # 3. Separate chunks into "Cached" vs "Needs Embedding"
        texts_to_embed = []
        chunks_to_embed = []
        
        for text_hash, text, chunk in all_chunk_data:
            if text_hash in db_cache:
                # Cache HIT
                chunk['embedding'] = db_cache[text_hash]
            else:
                # Cache MISS
                texts_to_embed.append(text)
                chunks_to_embed.append(chunk)

        all_new_embeddings = []

        if texts_to_embed:
            logger.info(f"Calculating embeddings for {len(texts_to_embed)} new chunks")
            if USE_REMOTE_EMBEDDING:
                logger.info(f"Using remote embedding server: {EMBEDDING_SERVER_URL}")
                try:
                    for i in range(0, len(texts_to_embed), BGE_M3_BATCH_SIZE * 2):
                        batch_texts = texts_to_embed[i:i + BGE_M3_BATCH_SIZE * 2]
                        response = httpx.post(
                            f"{EMBEDDING_SERVER_URL}/embed", 
                            json={"text": batch_texts},
                            timeout=120.0
                        )
                        response.raise_for_status()
                        all_new_embeddings.extend(response.json()["embeddings"])
                except Exception as e:
                    logger.error(f"Remote embedding failed: {e}")
                    raise ValueError(f"Remote embedding server error: {str(e)}")
            else:
                for i in range(0, len(texts_to_embed), BGE_M3_BATCH_SIZE):
                    batch_texts = texts_to_embed[i:i + BGE_M3_BATCH_SIZE]
                    encode_kwargs = {"batch_size": len(batch_texts)}
                    
                    from sentence_transformers import SentenceTransformer
                    if not isinstance(model, SentenceTransformer):
                        encode_kwargs["max_length"] = BGE_M3_MAX_LENGTH
                    
                    raw_output = model.encode(batch_texts, **encode_kwargs)
                    if isinstance(raw_output, dict):
                        batch_embeddings = raw_output['dense_vecs']
                    else:
                        batch_embeddings = raw_output
                    
                    if BGE_M3_NORMALIZE:
                        norms = np.linalg.norm(batch_embeddings, axis=1, keepdims=True)
                        batch_embeddings = batch_embeddings / norms
                    
                    all_new_embeddings.extend(batch_embeddings)
            
            # 4. Attach new embeddings and save to cache
            new_cache_records = []
            for chunk, embedding in zip(chunks_to_embed, all_new_embeddings):
                chunk['embedding'] = embedding.tolist() if hasattr(embedding, 'tolist') else embedding
                
                # Save to DB cache list
                text_hash = chunk['metadata']['normalized_text_hash']
                new_cache_records.append(EmbeddingCache(
                    text_hash=text_hash,
                    tenant_id=tenant_id,
                    model_name=BGE_M3_MODEL_NAME,
                    vector=chunk['embedding']
                ))
            
            if new_cache_records:
                try:
                    db.add_all(new_cache_records)
                    db.commit()
                except IntegrityError:
                    # Occurs if multiple workers insert the same exact hash at the same fraction of a second
                    db.rollback()
                    logger.warning("Integrity error updating embedding cache (likely race condition), ignoring.")
                except Exception as e:
                    db.rollback()
                    logger.warning(f"Failed to update embedding cache: {e}")

        # 5. Populate metadata for all chunks
        for chunk in chunks:
            chunk['metadata']['embedding_model'] = BGE_M3_MODEL_NAME
            chunk['metadata']['embedding_type'] = 'multilingual'
            chunk['metadata']['embedding_dimension'] = len(chunk['embedding'])
        
        db.close()
        logger.info(f"✓ Successfully processed multilingual embeddings for {len(chunks)} chunks")
        return chunks
        
    except Exception as e:
        logger.error(f"Error creating multilingual embeddings: {e}")
        # Raise exception instead of returning chunks without embeddings 
        # to prevent KeyError: 'embedding' in subsequent steps
        raise ValueError(f"Failed to generate embeddings for {len(chunks)} chunks: {str(e)}")

def get_embedding_dimension() -> int:
    """Get the embedding dimension for BGE-M3."""
    return 1024  # BGE-M3 output dimension

def is_multilingual_enabled() -> bool:
    """Check if multilingual embedding is enabled."""
    return MULTILINGUAL_ENABLED

def get_multilingual_model_info() -> Dict[str, Any]:
    """Get information about the multilingual model."""
    return {
        "enabled": MULTILINGUAL_ENABLED,
        "model_name": BGE_M3_MODEL_NAME,
        "dimension": get_embedding_dimension(),
        "max_length": BGE_M3_MAX_LENGTH,
        "batch_size": BGE_M3_BATCH_SIZE,
        "normalize": BGE_M3_NORMALIZE,
        "device": "cuda" if torch.cuda.is_available() else "cpu"
    }

# Compatibility functions for existing code
def should_use_multilingual_embedding(tenant_id: str = None) -> bool:
    """
    Determine if multilingual embedding should be used.
    Always use multilingual when enabled - BGE-M3 handles all languages including single-language content.
    
    Args:
        tenant_id: Tenant identifier (not used - always multilingual when enabled)
        
    Returns:
        True if multilingual embedding should be used
    """
    return MULTILINGUAL_ENABLED

def create_embeddings_no_fallback(chunks: List[Dict[str, Any]], tenant_id: str = None) -> List[Dict[str, Any]]:
    """
    Create multilingual embeddings using BGE-M3 - no fallback to legacy.
    
    Args:
        chunks: List of data chunks
        tenant_id: Tenant identifier (for logging only)
        
    Returns:
        Chunks with BGE-M3 multilingual embeddings
    """
    logger.info(f"Using multilingual embeddings (BGE-M3) - handles all languages optimally")
    return create_multilingual_embeddings(chunks, tenant_id=tenant_id)

def create_embeddings_with_fallback(chunks: List[Dict[str, Any]], tenant_id: str = None) -> List[Dict[str, Any]]:
    """
    Create embeddings using BGE-M3 multilingual model only - no fallback.
    
    Args:
        chunks: List of data chunks
        tenant_id: Tenant identifier (for logging only)
        
    Returns:
        Chunks with BGE-M3 multilingual embeddings
    """
    logger.info(f"Using BGE-M3 multilingual embeddings only - no fallback")
    return create_multilingual_embeddings(chunks, tenant_id=tenant_id)
