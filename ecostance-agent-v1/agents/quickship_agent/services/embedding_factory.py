"""
Embedding Service Factory
Creates appropriate embedding service based on configuration
"""

import logging
from typing import Optional, Union, List
from abc import ABC, abstractmethod
from langchain_core.embeddings import Embeddings
import httpx

from app.config.multilingual_app_config import (
    EMBEDDING_MODEL_TYPE,
    BGE_M3_MODEL_NAME,
    BGE_M3_EMBEDDING_DIMENSION,
    BGE_M3_MAX_SEQUENCE_LENGTH,
    BGE_M3_BATCH_SIZE,
    BGE_M3_NORMALIZE,
    BGE_M3_DEVICE,
    FALLBACK_TO_LEGACY
)
from app.config import USE_REMOTE_EMBEDDING, EMBEDDING_SERVER_URL

logger = logging.getLogger(__name__)


class BaseEmbeddingService(Embeddings, ABC):
    """Abstract base class for embedding services that extends LangChain Embeddings."""
    
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed search docs."""
        pass
    
    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Embed query text."""
        pass
    
    @abstractmethod
    def encode(self, texts: Union[str, list], **kwargs):
        """Encode text(s) into embeddings."""
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Get embedding dimension."""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get model name."""
        pass


class LegacyEmbeddingService(BaseEmbeddingService):
    """Legacy HuggingFace embedding service (unchanged)."""
    
    def __init__(self):
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from ..config import EMBEDDING_MODEL_NAME, EMBEDDING_VECTOR_SIZE
        
        self.model_name = EMBEDDING_MODEL_NAME
        self.dimension = EMBEDDING_VECTOR_SIZE
        self.embeddings = HuggingFaceEmbeddings(model_name=self.model_name)
        
        logger.info(f"Initialized legacy embedding service: {self.model_name}")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed search docs using legacy HuggingFace embeddings."""
        return self.embeddings.embed_documents(texts)
    
    def embed_query(self, text: str) -> List[float]:
        """Embed query text using legacy HuggingFace embeddings."""
        return self.embeddings.embed_query(text)
    
    def encode(self, texts: Union[str, list], **kwargs):
        """Encode using legacy HuggingFace embeddings."""
        if isinstance(texts, str):
            return self.embed_query(texts)
        else:
            return self.embed_documents(texts)
    
    def get_dimension(self) -> int:
        return self.dimension
    
    def get_model_name(self) -> str:
        return self.model_name


class BGE_M3EmbeddingService(BaseEmbeddingService):
    """BGE-M3 multilingual embedding service."""
    
    def __init__(self):
        self.model_name = BGE_M3_MODEL_NAME
        self.dimension = BGE_M3_EMBEDDING_DIMENSION
        self.max_length = BGE_M3_MAX_SEQUENCE_LENGTH
        self.batch_size = BGE_M3_BATCH_SIZE
        self.normalize = BGE_M3_NORMALIZE
        self.model = None

        if USE_REMOTE_EMBEDDING:
            logger.info(f"BGE-M3 using remote embedding server: {EMBEDDING_SERVER_URL}")
            return

        try:
            from FlagEmbedding import BGEM3FlagModel
            import torch

            if BGE_M3_DEVICE == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                device = BGE_M3_DEVICE

            logger.info(f"Initializing BGE-M3 model on device: {device}")
            self.model = BGEM3FlagModel(
                BGE_M3_MODEL_NAME,
                use_fp16=device == "cuda",
                device=device
            )
            logger.info(f"Successfully initialized BGE-M3 embedding service")
        except ImportError as e:
            logger.error(f"Failed to import BGE-M3 dependencies: {e}")
            raise ImportError("BGE-M3 dependencies not installed. Install with: pip install FlagEmbedding")
        except Exception as e:
            logger.error(f"Failed to initialize BGE-M3 model: {e}")
            raise
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed search docs using BGE-M3."""
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents using BGE-M3."""
        if self.model is None:
            response = httpx.post(f"{EMBEDDING_SERVER_URL}/embed", json={"text": texts}, timeout=120.0)
            response.raise_for_status()
            return response.json()["embeddings"]
        embeddings = self.encode(texts)
        if hasattr(embeddings[0], 'tolist'):
            return [emb.tolist() for emb in embeddings]
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed query text using BGE-M3."""
        if self.model is None:
            response = httpx.post(f"{EMBEDDING_SERVER_URL}/embed", json={"text": text}, timeout=60.0)
            response.raise_for_status()
            return response.json()["embedding"]
        embedding = self.encode(text)
        if hasattr(embedding, 'tolist'):
            return embedding.tolist()
        return embedding
    
    def encode(self, texts: Union[str, list], **kwargs):
        """Encode text(s) using BGE-M3 local model or remote server."""
        if self.model is None:
            # Delegate to embed methods which handle remote
            if isinstance(texts, str):
                return self.embed_query(texts)
            return self.embed_documents(texts)

        try:
            # Handle single text
            if isinstance(texts, str):
                texts = [texts]
                single_text = True
            else:
                single_text = False
            
            # Truncate texts if needed
            max_length = kwargs.get('max_length', self.max_length)
            if max_length:
                texts = [text[:max_length] for text in texts]
            
            # Get batch size
            batch_size = kwargs.get('batch_size', self.batch_size)
            
            # Encode in batches
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                # Use dense embeddings from BGE-M3
                batch_embeddings = self.model.encode(
                    batch_texts,
                    batch_size=len(batch_texts),
                    max_length=max_length
                )['dense_vecs']
                
                # Normalize if requested
                if self.normalize:
                    import numpy as np
                    norms = np.linalg.norm(batch_embeddings, axis=1, keepdims=True)
                    batch_embeddings = batch_embeddings / norms
                
                all_embeddings.extend(batch_embeddings)
            
            # Return single embedding or list
            if single_text:
                return all_embeddings[0]
            else:
                return all_embeddings
                
        except Exception as e:
            logger.error(f"Error encoding with BGE-M3: {e}")
            raise
    
    def encode_queries(self, queries: Union[str, list], **kwargs):
        """
        Encode queries (optimized for search).
        
        Args:
            queries: Query text(s)
            **kwargs: Additional arguments
            
        Returns:
            Query embeddings
        """
        # For BGE-M3, we can use the same encoding for queries and documents
        return self.encode(queries, **kwargs)
    
    def encode_documents(self, documents: Union[str, list], **kwargs):
        """
        Encode documents (optimized for indexing).
        
        Args:
            documents: Document text(s)
            **kwargs: Additional arguments
            
        Returns:
            Document embeddings
        """
        return self.encode(documents, **kwargs)
    
    def get_dimension(self) -> int:
        return self.dimension
    
    def get_model_name(self) -> str:
        return self.model_name
    
    def get_max_length(self) -> int:
        return self.max_length


class EmbeddingServiceFactory:
    """Factory for creating embedding services."""
    
    @staticmethod
    def create_service(model_type: Optional[str] = None) -> BaseEmbeddingService:
        """
        Create embedding service based on configuration.
        
        Args:
            model_type: Override model type ('huggingface' or 'bge-m3')
            
        Returns:
            Embedding service instance
        """
        if model_type is None:
            model_type = EMBEDDING_MODEL_TYPE
        
        try:
            if model_type == "bge-m3":
                logger.info("Creating BGE-M3 embedding service")
                return BGE_M3EmbeddingService()
            else:
                logger.info("Creating legacy HuggingFace embedding service")
                return LegacyEmbeddingService()
                
        except Exception as e:
            logger.error(f"Failed to create {model_type} embedding service: {e}")
            
            if FALLBACK_TO_LEGACY and model_type != "huggingface":
                logger.warning("Falling back to legacy embedding service")
                return LegacyEmbeddingService()
            else:
                raise
    
    @staticmethod
    def get_available_models() -> list:
        """Get list of available embedding models."""
        models = ["huggingface"]
        
        try:
            import FlagEmbedding
            models.append("bge-m3")
        except ImportError:
            pass
        
        return models
    
    @staticmethod
    def validate_model_type(model_type: str) -> bool:
        """Validate if model type is available."""
        return model_type in EmbeddingServiceFactory.get_available_models()


# Global embedding service instance
_embedding_service = None

def get_embedding_service(model_type: Optional[str] = None, force_recreate: bool = False) -> BaseEmbeddingService:
    """
    Get or create the global embedding service instance.
    
    Args:
        model_type: Override model type
        force_recreate: Force recreation of service
        
    Returns:
        Embedding service instance
    """
    global _embedding_service
    
    if _embedding_service is None or force_recreate:
        _embedding_service = EmbeddingServiceFactory.create_service(model_type)
    
    return _embedding_service
