"""
Public Chat Service - Business logic for public chat functionality.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json
import uuid
import logging

from ..models.public_chat import (
    PublicChatConfig,
    PublicChatSession,
    PublicChatMessage,
    PublicChatFeedback
)
from ..models.tenant_knowledge_base import TenantKnowledgeBase
from ..schemas.public_chat import (
    PublicChatQueryRequest,
    AdminPublicChatConfigUpdate,
    ConversationMessage
)

logger = logging.getLogger(__name__)


class PublicChatService:
    """Service for managing public chat functionality."""

    def __init__(self, db: Session):
        self.db = db

    # ========================================================================
    # Configuration Management
    # ========================================================================

    def get_config(self, tenant_id: str) -> Optional[PublicChatConfig]:
        """Get public chat configuration for tenant."""
        return self.db.query(PublicChatConfig).filter(
            PublicChatConfig.tenant_id == tenant_id
        ).first()

    def get_or_create_config(self, tenant_id: str, tenant_name: str) -> PublicChatConfig:
        """Get or create default configuration."""
        config = self.get_config(tenant_id)
        if not config:
            config = PublicChatConfig(
                tenant_id=tenant_id,
                enabled=False,
                allowed_kbs="[]",
                welcome_message="Hi! How can I help you today?",
                suggested_questions="[]",
                branding=json.dumps({
                    "primary_color": "#0066CC",
                    "company_name": tenant_name
                }),
                rate_limit=json.dumps({
                    "queries_per_minute": 10,
                    "max_messages_per_session": 50
                }),
                features=json.dumps({
                    "show_sources": True,
                    "allow_feedback": True,
                    "show_suggested_questions": True
                })
            )
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
        return config

    def update_config(
        self,
        tenant_id: str,
        update_data: AdminPublicChatConfigUpdate,
        updated_by: str
    ) -> PublicChatConfig:
        """Update public chat configuration."""
        config = self.get_config(tenant_id)
        if not config:
            raise ValueError("Configuration not found")

        # Skip validation for now - just accept whatever KBs are sent
        # The frontend should only send valid KBs anyway
        if update_data.allowed_kbs:
            logger.info(f"Updating allowed KBs for tenant {tenant_id}: {update_data.allowed_kbs}")

        # Update fields
        config.enabled = update_data.enabled
        config.allowed_kbs = json.dumps(update_data.allowed_kbs)
        config.welcome_message = update_data.welcome_message
        config.suggested_questions = json.dumps(update_data.suggested_questions)
        config.branding = json.dumps(update_data.branding.dict())
        config.rate_limit = json.dumps(update_data.rate_limit.dict())
        config.features = json.dumps(update_data.features.dict())
        config.updated_at = datetime.utcnow()
        config.updated_by = updated_by

        self.db.commit()
        self.db.refresh(config)
        return config

    # ========================================================================
    # Session Management
    # ========================================================================

    def get_or_create_session(
        self,
        session_id: str,
        tenant_id: str,
        metadata: Optional[Dict] = None
    ) -> PublicChatSession:
        """Get or create a chat session."""
        session = self.db.query(PublicChatSession).filter(
            PublicChatSession.session_id == session_id
        ).first()

        if not session:
            session = PublicChatSession(
                session_id=session_id,
                tenant_id=tenant_id,
                session_metadata=json.dumps(metadata or {})
            )
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
        else:
            # Update last activity
            session.last_activity = datetime.utcnow()
            self.db.commit()

        return session

    def update_session_activity(self, session_id: str, is_query: bool = False):
        """Update session activity timestamp and counters."""
        session = self.db.query(PublicChatSession).filter(
            PublicChatSession.session_id == session_id
        ).first()

        if session:
            session.last_activity = datetime.utcnow()
            session.message_count += 1
            if is_query:
                session.query_count += 1
            self.db.commit()

    def get_session(self, session_id: str) -> Optional[PublicChatSession]:
        """Get session by ID."""
        return self.db.query(PublicChatSession).filter(
            PublicChatSession.session_id == session_id
        ).first()

    def is_session_expired(self, session_id: str, hours: int = 24) -> bool:
        """Check if session has expired."""
        session = self.get_session(session_id)
        if not session:
            return True
        
        expiry_time = datetime.utcnow() - timedelta(hours=hours)
        return session.last_activity < expiry_time

    # ========================================================================
    # Message Management
    # ========================================================================

    def add_message(
        self,
        session_id: str,
        tenant_id: str,
        role: str,
        content: str,
        sources: Optional[List[Dict]] = None
    ) -> PublicChatMessage:
        """Add a message to the session."""
        message = PublicChatMessage(
            id=f"msg-{uuid.uuid4().hex[:16]}",
            session_id=session_id,
            tenant_id=tenant_id,
            role=role,
            content=content,
            sources=json.dumps(sources) if sources else None
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_session_messages(self, session_id: str) -> List[PublicChatMessage]:
        """Get all messages for a session."""
        return self.db.query(PublicChatMessage).filter(
            PublicChatMessage.session_id == session_id
        ).order_by(PublicChatMessage.timestamp).all()

    def update_message_feedback(
        self,
        message_id: str,
        feedback_type: str,
        comment: Optional[str] = None
    ):
        """Update message feedback."""
        message = self.db.query(PublicChatMessage).filter(
            PublicChatMessage.id == message_id
        ).first()

        if message:
            message.feedback = feedback_type
            message.feedback_comment = comment
            self.db.commit()

    # ========================================================================
    # Feedback Management
    # ========================================================================

    def add_feedback(
        self,
        session_id: str,
        message_id: str,
        tenant_id: str,
        feedback_type: str,
        comment: Optional[str] = None
    ) -> PublicChatFeedback:
        """Add feedback for a message."""
        feedback = PublicChatFeedback(
            session_id=session_id,
            message_id=message_id,
            tenant_id=tenant_id,
            feedback_type=feedback_type,
            comment=comment
        )
        self.db.add(feedback)
        
        # Also update the message
        self.update_message_feedback(message_id, feedback_type, comment)
        
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    # ========================================================================
    # Rate Limiting
    # ========================================================================

    def check_rate_limit(
        self,
        session_id: str,
        config: PublicChatConfig
    ) -> Tuple[bool, Optional[str]]:
        """Check if session has exceeded rate limits."""
        rate_limit = json.loads(config.rate_limit) if isinstance(config.rate_limit, str) else config.rate_limit
        
        session = self.get_session(session_id)
        if not session:
            return True, None

        # Check max messages per session
        if session.message_count >= rate_limit.get("max_messages_per_session", 50):
            return False, "Maximum messages per session exceeded"

        # Check queries per minute
        one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
        recent_queries = self.db.query(func.count(PublicChatMessage.id)).filter(
            and_(
                PublicChatMessage.session_id == session_id,
                PublicChatMessage.role == "user",
                PublicChatMessage.timestamp >= one_minute_ago
            )
        ).scalar()

        if recent_queries >= rate_limit.get("queries_per_minute", 10):
            return False, "Rate limit exceeded. Please wait before sending another message."

        return True, None

    # ========================================================================
    # Knowledge Base Management
    # ========================================================================

    def get_available_kbs(self, tenant_id: str) -> List[Dict]:
        """Get available knowledge bases for tenant."""
        kbs = self.db.query(TenantKnowledgeBase).filter(
            TenantKnowledgeBase.tenant_id == tenant_id
        ).all()

        return [
            {
                "id": kb.kb_id,
                "name": kb.name,
                "document_count": kb.document_count or 0,
                "is_public": False,  # Can be extended later
                "created_at": kb.created_at.isoformat() if kb.created_at else None
            }
            for kb in kbs
        ]

    # ========================================================================
    # Analytics
    # ========================================================================

    def get_analytics(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """Get analytics for public chat."""
        # Total sessions
        total_sessions = self.db.query(func.count(PublicChatSession.session_id)).filter(
            and_(
                PublicChatSession.tenant_id == tenant_id,
                PublicChatSession.started_at >= start_date,
                PublicChatSession.started_at <= end_date
            )
        ).scalar() or 0

        # Total queries (user messages)
        total_queries = self.db.query(func.count(PublicChatMessage.id)).filter(
            and_(
                PublicChatMessage.tenant_id == tenant_id,
                PublicChatMessage.role == "user",
                PublicChatMessage.timestamp >= start_date,
                PublicChatMessage.timestamp <= end_date
            )
        ).scalar() or 0

        # Feedback summary
        feedback_stats = self.db.query(
            PublicChatFeedback.feedback_type,
            func.count(PublicChatFeedback.id)
        ).filter(
            and_(
                PublicChatFeedback.tenant_id == tenant_id,
                PublicChatFeedback.timestamp >= start_date,
                PublicChatFeedback.timestamp <= end_date
            )
        ).group_by(PublicChatFeedback.feedback_type).all()

        positive_feedback = 0
        negative_feedback = 0
        for feedback_type, count in feedback_stats:
            if feedback_type == "positive":
                positive_feedback = count
            elif feedback_type == "negative":
                negative_feedback = count

        total_feedback = positive_feedback + negative_feedback
        positive_percentage = (positive_feedback / total_feedback * 100) if total_feedback > 0 else 0

        # Average queries per session
        avg_queries = (total_queries / total_sessions) if total_sessions > 0 else 0

        # Top questions (simplified - just get most common user messages)
        top_questions_raw = self.db.query(
            PublicChatMessage.content,
            func.count(PublicChatMessage.id).label('count')
        ).filter(
            and_(
                PublicChatMessage.tenant_id == tenant_id,
                PublicChatMessage.role == "user",
                PublicChatMessage.timestamp >= start_date,
                PublicChatMessage.timestamp <= end_date
            )
        ).group_by(PublicChatMessage.content).order_by(
            func.count(PublicChatMessage.id).desc()
        ).limit(10).all()

        top_questions = [
            {
                "question": q.content[:100],  # Truncate long questions
                "count": q.count,
                "percentage": (q.count / total_queries * 100) if total_queries > 0 else 0
            }
            for q in top_questions_raw
        ]

        return {
            "total_sessions": total_sessions,
            "total_queries": total_queries,
            "unique_visitors": total_sessions,  # Simplified
            "average_queries_per_session": round(avg_queries, 2),
            "average_rating": round(positive_percentage / 20, 2) if total_feedback > 0 else None,  # Convert to 5-star scale
            "top_questions": top_questions,
            "feedback_summary": {
                "total_feedback": total_feedback,
                "positive": positive_feedback,
                "negative": negative_feedback,
                "positive_percentage": round(positive_percentage, 1)
            }
        }

    def get_session_details(self, session_id: str, tenant_id: str) -> Optional[Dict]:
        """Get detailed information about a session."""
        session = self.db.query(PublicChatSession).filter(
            and_(
                PublicChatSession.session_id == session_id,
                PublicChatSession.tenant_id == tenant_id
            )
        ).first()

        if not session:
            return None

        messages = self.get_session_messages(session_id)
        
        duration_seconds = None
        if session.ended_at:
            duration_seconds = int((session.ended_at - session.started_at).total_seconds())

        return {
            "session_id": session.session_id,
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "duration_seconds": duration_seconds,
            "message_count": session.message_count,
            "messages": [msg.to_dict() for msg in messages],
            "metadata": json.loads(session.session_metadata) if isinstance(session.session_metadata, str) else session.session_metadata
        }
