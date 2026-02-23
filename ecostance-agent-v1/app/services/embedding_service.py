import os
from sentence_transformers import SentenceTransformer
import torch
from typing import List, Dict, Any, Optional
from threading import Lock
import logging

from .langsmith_service import trace_embedding

# Limit GPU memory usage to 1/3
if torch.cuda.is_available():
    torch.cuda.set_per_process_memory_fraction(0.33)

logger = logging.getLogger(__name__)

# Global embedding model instance (singleton pattern)
_embedding_model: Optional[SentenceTransformer] = None
_langchain_embeddings: Optional[Any] = None
_embedding_model_lock = Lock()


@trace_embedding
def load_embedding_model() -> SentenceTransformer:
    """
    Returns a singleton embedding model instance.
    
    This ensures the model is loaded only once and reused across all requests,
    significantly improving performance and reducing memory usage.
    
    The model loading is expensive (~500MB RAM, ~2-3 seconds), so we cache it.
    
    Returns:
        SentenceTransformer: Singleton embedding model instance
    """
    global _embedding_model
    
    # Double-checked locking pattern for thread-safe singleton
    if _embedding_model is None:
        with _embedding_model_lock:
            if _embedding_model is None:
                # Check if a CUDA-enabled GPU is available, otherwise use CPU
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
                logger.info(f"Loading embedding model singleton on device: {device}")
                
                # Load a pre-trained model.
                from app.config import EMBEDDING_MODEL_NAME as CONFIG_MODEL_NAME
                model_name = os.getenv('EMBEDDING_MODEL_NAME', CONFIG_MODEL_NAME or 'BAAI/bge-m3')
                logger.info(f"Using embedding model: {model_name}")
                _embedding_model = SentenceTransformer(model_name, device=device)
                
                logger.info("✓ Embedding model singleton loaded successfully")
    
    return _embedding_model

def get_langchain_embeddings():
    """
    Returns a singleton LangChain-compatible embeddings object.
    
    This avoids re-initializing the heavy model when using LangChain components like VectorStores.
    """
    global _langchain_embeddings
    
    if _langchain_embeddings is None:
        with _embedding_model_lock:
            if _langchain_embeddings is None:
                from langchain_community.embeddings import HuggingFaceEmbeddings
                from app.config import EMBEDDING_MODEL_NAME as CONFIG_MODEL_NAME
                
                # Ensure the base model is loaded
                base_model = load_embedding_model()
                
                logger.info("Creating LangChain embeddings wrapper for singleton model")
                _langchain_embeddings = HuggingFaceEmbeddings(
                    model_name=os.getenv('EMBEDDING_MODEL_NAME', CONFIG_MODEL_NAME or 'BAAI/bge-m3'),
                    client=base_model
                )
    
    return _langchain_embeddings


def unload_embedding_model():
    """
    Unload the embedding model from memory.
    Should be called on application shutdown.
    """
    global _embedding_model, _langchain_embeddings
    
    if _embedding_model is not None or _langchain_embeddings is not None:
        with _embedding_model_lock:
            try:
                if _langchain_embeddings is not None:
                    del _langchain_embeddings
                    _langchain_embeddings = None
                
                if _embedding_model is not None:
                    del _embedding_model
                    _embedding_model = None
                
                # Clear CUDA cache if using GPU
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                logger.info("✓ Embedding model and wrapper unloaded successfully")
            except Exception as e:
                logger.error(f"Error unloading embedding model: {e}")

# --- Embedding Creation ---
@trace_embedding
def create_embeddings(chunks: List[Dict[str, Any]], model: SentenceTransformer) -> List[Dict[str, Any]]:
    """
    Generates vector embeddings for a list of text chunks and attaches them.

    Args:
        chunks (List[Dict[str, Any]]): The list of processed data chunks.
        model (SentenceTransformer): The loaded sentence-transformer model.

    Returns:
        The list of chunks, now with an 'embedding' key in each one.
    """
    # Extract the text content from each chunk to be embedded.
    texts_to_embed = [chunk['text'] for chunk in chunks]

    # Generate embeddings for all texts in a single batch.
    # The `encode` method returns a list of numpy arrays.
    embeddings = model.encode(texts_to_embed, show_progress_bar=False)

    # Attach the generated embedding to its corresponding chunk.
    # We convert the numpy array to a list to ensure it's easily serializable (e.g., for JSON).
    for chunk, embedding in zip(chunks, embeddings):
        chunk['embedding'] = embedding.tolist()

    return chunks
