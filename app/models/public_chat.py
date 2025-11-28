"""
Public Chat models - represents public chat configuration, sessions, messages, and feedback.
"""
from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import json

from ..db.database import Base


class PublicChatConfig(Base):
    """Configuration for public chat feature per tenant."""
    __tablename__ = "public_chat_configs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    enabled = Column(Boolean, default=True, nullable=False)
    allowed_kbs = Column(Text, default="[]", nullable=False)  # JSON array
    welcome_message = Column(Text, nullable=False, default="Hi! How can I help you today?")
    suggested_questions = Column(Text, default="[]", nullable=False)  # JSON array
    branding = Column(Text, nullable=False, default="{}")  # JSON object
    rate_limit = Column(Text, nullable=False, default='{"queries_per_minute": 10, "max_messages_per_session": 50}')  # JSON object
    features = Column(Text, nullable=False, default='{"show_sources": true, "allow_feedback": true, "show_suggested_questions": true}')  # JSON object
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(255))

    def to_dict(self, include_sensitive=False):
        """Convert to dictionary."""
        data = {
            "enabled": self.enabled,
            "welcome_message": self.welcome_message,
            "suggested_questions": json.loads(self.suggested_questions) if isinstance(self.suggested_questions, str) else self.suggested_questions,
            "branding": json.loads(self.branding) if isinstance(self.branding, str) else self.branding,
            "rate_limit": json.loads(self.rate_limit) if isinstance(self.rate_limit, str) else self.rate_limit,
            "features": json.loads(self.features) if isinstance(self.features, str) else self.features,
        }
        
        if include_sensitive:
            data.update({
                "id": self.id,
                "tenant_id": self.tenant_id,
                "allowed_kbs": json.loads(self.allowed_kbs) if isinstance(self.allowed_kbs, str) else self.allowed_kbs,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "updated_by": self.updated_by,
            })
        
        return data


class PublicChatSession(Base):
    """Individual chat session."""
    __tablename__ = "public_chat_sessions"

    session_id = Column(String(100), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime)
    message_count = Column(Integer, default=0, nullable=False)
    query_count = Column(Integer, default=0, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    session_metadata = Column("metadata", Text, default="{}")  # JSON object

    # Relationships
    messages = relationship("PublicChatMessage", back_populates="session", cascade="all, delete-orphan")

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "message_count": self.message_count,
            "query_count": self.query_count,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "metadata": json.loads(self.session_metadata) if isinstance(self.session_metadata, str) else self.session_metadata,
        }


class PublicChatMessage(Base):
    """Individual message in a chat session."""
    __tablename__ = "public_chat_messages"

    id = Column(String(100), primary_key=True)
    session_id = Column(String(100), ForeignKey("public_chat_sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    sources = Column(Text)  # JSON array
    feedback = Column(String(20))
    feedback_comment = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    session = relationship("PublicChatSession", back_populates="messages")

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="check_role"),
        CheckConstraint("feedback IN ('positive', 'negative') OR feedback IS NULL", name="check_feedback"),
    )

    def to_dict(self):
        """Convert to dictionary."""
        data = {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
        
        if self.sources:
            data["sources"] = json.loads(self.sources) if isinstance(self.sources, str) else self.sources
        
        if self.feedback:
            data["feedback"] = self.feedback
        
        if self.feedback_comment:
            data["feedback_comment"] = self.feedback_comment
        
        return data


class PublicChatFeedback(Base):
    """Feedback submitted by users."""
    __tablename__ = "public_chat_feedback"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(100), nullable=False)
    message_id = Column(String(100), ForeignKey("public_chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    feedback_type = Column(String(20), nullable=False)
    comment = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        CheckConstraint("feedback_type IN ('positive', 'negative')", name="check_feedback_type"),
    )

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "message_id": self.message_id,
            "feedback_type": self.feedback_type,
            "comment": self.comment,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
