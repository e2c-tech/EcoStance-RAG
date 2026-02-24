from sqlalchemy import Column, String, Float, DateTime, JSON
from sqlalchemy.orm import declarative_base
from datetime import datetime
from app.db.database import Base

class EmbeddingCache(Base):
    """
    Model for caching vector embeddings to prevent re-calculating the same
    text chunk multiple times (e.g., repeating headers, footers).
    """
    __tablename__ = "embedding_cache"

    text_hash = Column(String(64), primary_key=True, index=True)
    tenant_id = Column(String(50), index=True, nullable=True)
    model_name = Column(String(100), nullable=False)
    vector = Column(JSON, nullable=False)  # We store the List[float] as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
