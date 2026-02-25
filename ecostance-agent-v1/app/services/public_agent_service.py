"""
Public Agent Service - Business logic for public agent functionality.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json
import uuid
import logging

from ..models.public_agent import (
    PublicAgentConfig,
    PublicAgentSession,
    PublicAgentMessage,
    PublicAgentFeedback
)
from ..models.tenant_knowledge_base import TenantKnowledgeBase
from ..schemas.public_agent import (
    PublicAgentChatRequest,
    AdminPublicAgentConfigUpdate,
    ConversationMessage
)

logger = logging.getLogger(__name__)


class PublicAgentService:
    """Service for managing public agent functionality."""

    def __init__(self, db: Session):
        self.db = db

    # ========================================================================
    # Configuration Management
    # ========================================================================

    def get_config(self, tenant_id: str) -> Optional[PublicAgentConfig]:
        """Get public agent configuration for tenant."""
        return self.db.query(PublicAgentConfig).filter(
            PublicAgentConfig.tenant_id == tenant_id
        ).first()

    def get_or_create_config(self, tenant_id: str, tenant_name: str) -> PublicAgentConfig:
        """Get or create default configuration."""
        config = self.get_config(tenant_id)
        if not config:
            config = PublicAgentConfig(
                tenant_id=tenant_id,
                enabled=False,
                allowed_kbs="[]",
                allowed_dbs="[]",
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
                    "show_suggested_questions": True,
                    "enable_database_tools": True,
                    "enable_knowledge_base": True
                }),
                agent_type="generic"
            )
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
        return config

    def update_config(
        self,
        tenant_id: str,
        update_data: AdminPublicAgentConfigUpdate,
        updated_by: str
    ) -> PublicAgentConfig:
        """Update public agent configuration."""
        config = self.get_config(tenant_id)
        if not config:
            raise ValueError("Configuration not found")

        logger.info(f"Updating public agent config for tenant {tenant_id}")
        logger.info(f"Allowed KBs: {update_data.allowed_kbs}")
        logger.info(f"Allowed DBs: {update_data.allowed_dbs}")
        logger.info(f"Allowed Tools: {update_data.allowed_tools}")

        # Update fields only if provided
        if update_data.enabled is not None:
            config.enabled = update_data.enabled
        if update_data.allowed_kbs is not None:
            config.allowed_kbs = json.dumps(update_data.allowed_kbs)
        if update_data.allowed_dbs is not None:
            config.allowed_dbs = json.dumps(update_data.allowed_dbs)
        if update_data.allowed_tools is not None:
            config.allowed_tools = json.dumps(update_data.allowed_tools)
        if update_data.welcome_message is not None:
            config.welcome_message = update_data.welcome_message
        if update_data.suggested_questions is not None:
            config.suggested_questions = json.dumps(update_data.suggested_questions)
        if update_data.branding is not None:
            config.branding = json.dumps(update_data.branding.dict())
        if update_data.rate_limit is not None:
            config.rate_limit = json.dumps(update_data.rate_limit.dict())
        if update_data.features is not None:
            config.features = json.dumps(update_data.features.dict())
        if update_data.agent_type is not None:
            config.agent_type = update_data.agent_type
            
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
    ) -> PublicAgentSession:
        """Get or create an agent session. Securely verified by tenant_id."""
        session = self.db.query(PublicAgentSession).filter(
            PublicAgentSession.session_id == session_id
        ).first()

        if session:
            # Security Check: Ensure session belongs to this tenant
            if session.tenant_id != tenant_id:
                logger.warning(f"Security Warning: Tenant {tenant_id} attempted to access session {session_id} belonging to Tenant {session.tenant_id}")
                raise ValueError("Unauthorized session access")
            
            # Update last activity
            session.last_activity = datetime.utcnow()
            self.db.commit()
            return session

        # Create new session if not found
        session = PublicAgentSession(
            session_id=session_id,
            tenant_id=tenant_id,
            title="New Conversation",
            session_metadata=json.dumps(metadata or {})
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def update_session_activity(self, session_id: str, tenant_id: str, is_query: bool = False):
        """Update session activity timestamp and counters with tenant verification."""
        session = self.db.query(PublicAgentSession).filter(
            and_(
                PublicAgentSession.session_id == session_id,
                PublicAgentSession.tenant_id == tenant_id
            )
        ).first()

        if session:
            session.last_activity = datetime.utcnow()
            session.message_count += 1
            if is_query:
                session.query_count += 1
            self.db.commit()

    def rename_session(self, session_id: str, tenant_id: str, new_title: str) -> bool:
        """Rename a session title with tenant verification."""
        session = self.db.query(PublicAgentSession).filter(
            and_(
                PublicAgentSession.session_id == session_id,
                PublicAgentSession.tenant_id == tenant_id
            )
        ).first()

        if session:
            session.title = new_title
            session.last_activity = datetime.utcnow()
            self.db.commit()
            return True
        return False

    def list_sessions(self, tenant_id: str) -> List[PublicAgentSession]:
        """List all sessions for a tenant, ordered by last activity."""
        return self.db.query(PublicAgentSession).filter(
            PublicAgentSession.tenant_id == tenant_id
        ).order_by(PublicAgentSession.last_activity.desc()).all()

    def get_session(self, session_id: str, tenant_id: str = None) -> Optional[PublicAgentSession]:
        """Get session by ID with optional tenant filtering."""
        query = self.db.query(PublicAgentSession).filter(
            PublicAgentSession.session_id == session_id
        )
        if tenant_id:
            query = query.filter(PublicAgentSession.tenant_id == tenant_id)
        return query.first()

    def delete_session(self, session_id: str, tenant_id: str) -> bool:
        """Delete a session and its associated messages/feedback by ID with tenant verification."""
        session = self.get_session(session_id, tenant_id)
        if session:
            self.db.delete(session)
            self.db.commit()
            return True
        return False

    def is_session_expired(self, session_id: str, tenant_id: str, hours: int = 24) -> bool:
        """Check if session has expired, scoped to tenant."""
        session = self.get_session(session_id, tenant_id)
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
        sources: Optional[List[Dict]] = None,
        tool_used: Optional[str] = None
    ) -> PublicAgentMessage:
        """Add a message to the session."""
        message = PublicAgentMessage(
            id=f"msg-{uuid.uuid4().hex[:16]}",
            session_id=session_id,
            tenant_id=tenant_id,
            role=role,
            content=content if isinstance(content, str) else json.dumps(content),
            sources=json.dumps(sources) if sources else None,
            tool_used=tool_used
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_session_messages(self, session_id: str, tenant_id: str) -> List[PublicAgentMessage]:
        """Get all messages for a session, filtered by tenant for security."""
        return self.db.query(PublicAgentMessage).filter(
            and_(
                PublicAgentMessage.session_id == session_id,
                PublicAgentMessage.tenant_id == tenant_id
            )
        ).order_by(PublicAgentMessage.timestamp).all()

    def update_message_feedback(
        self,
        message_id: str,
        feedback_type: str,
        comment: Optional[str] = None
    ):
        """Update message feedback."""
        message = self.db.query(PublicAgentMessage).filter(
            PublicAgentMessage.id == message_id
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
    ) -> PublicAgentFeedback:
        """Add feedback for a message."""
        feedback = PublicAgentFeedback(
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
        config: PublicAgentConfig
    ) -> Tuple[bool, Optional[str]]:
        """Check if session has exceeded rate limits."""
        # RATE LIMITS FULLY DISABLED FOR DEV/TESTING
        return True, None

        # Original logic commented out below:
        # rate_limit = json.loads(config.rate_limit) if isinstance(config.rate_limit, str) else config.rate_limit
        # session = self.get_session(session_id)
        # if not session:
        #     return True, None

        # Check max messages per session
        # if session.message_count >= rate_limit.get("max_messages_per_session", 50):
        #     return False, "Maximum messages per session exceeded"

        # Check queries per minute
        # one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
        # recent_queries = self.db.query(func.count(PublicAgentMessage.id)).filter(
        #     and_(
        #         PublicAgentMessage.session_id == session_id,
        #         PublicAgentMessage.role == "user",
        #         PublicAgentMessage.timestamp >= one_minute_ago
        #     )
        # ).scalar()

        # if recent_queries >= rate_limit.get("queries_per_minute", 10):
        #     return False, "Rate limit exceeded. Please wait before sending another message."

        # return True, None

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
                "is_public": False,
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
        """Get analytics for public agent."""
        # Total sessions
        total_sessions = self.db.query(func.count(PublicAgentSession.session_id)).filter(
            and_(
                PublicAgentSession.tenant_id == tenant_id,
                PublicAgentSession.started_at >= start_date,
                PublicAgentSession.started_at <= end_date
            )
        ).scalar() or 0

        # Total queries (user messages)
        total_queries = self.db.query(func.count(PublicAgentMessage.id)).filter(
            and_(
                PublicAgentMessage.tenant_id == tenant_id,
                PublicAgentMessage.role == "user",
                PublicAgentMessage.timestamp >= start_date,
                PublicAgentMessage.timestamp <= end_date
            )
        ).scalar() or 0

        # Database vs KB queries
        db_queries = self.db.query(func.count(PublicAgentMessage.id)).filter(
            and_(
                PublicAgentMessage.tenant_id == tenant_id,
                PublicAgentMessage.tool_used == "database",
                PublicAgentMessage.timestamp >= start_date,
                PublicAgentMessage.timestamp <= end_date
            )
        ).scalar() or 0

        kb_queries = self.db.query(func.count(PublicAgentMessage.id)).filter(
            and_(
                PublicAgentMessage.tenant_id == tenant_id,
                PublicAgentMessage.tool_used == "knowledge_base",
                PublicAgentMessage.timestamp >= start_date,
                PublicAgentMessage.timestamp <= end_date
            )
        ).scalar() or 0

        # Feedback summary
        feedback_stats = self.db.query(
            PublicAgentFeedback.feedback_type,
            func.count(PublicAgentFeedback.id)
        ).filter(
            and_(
                PublicAgentFeedback.tenant_id == tenant_id,
                PublicAgentFeedback.timestamp >= start_date,
                PublicAgentFeedback.timestamp <= end_date
            )
        ).group_by(PublicAgentFeedback.feedback_type).all()

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

        # Top questions
        top_questions_raw = self.db.query(
            PublicAgentMessage.content,
            func.count(PublicAgentMessage.id).label('count')
        ).filter(
            and_(
                PublicAgentMessage.tenant_id == tenant_id,
                PublicAgentMessage.role == "user",
                PublicAgentMessage.timestamp >= start_date,
                PublicAgentMessage.timestamp <= end_date
            )
        ).group_by(PublicAgentMessage.content).order_by(
            func.count(PublicAgentMessage.id).desc()
        ).limit(10).all()

        top_questions = [
            {
                "question": q.content[:100],
                "count": q.count,
                "percentage": (q.count / total_queries * 100) if total_queries > 0 else 0
            }
            for q in top_questions_raw
        ]

        return {
            "total_sessions": total_sessions,
            "total_queries": total_queries,
            "unique_visitors": total_sessions,
            "average_queries_per_session": round(avg_queries, 2),
            "average_rating": round(positive_percentage / 20, 2) if total_feedback > 0 else None,
            "database_queries": db_queries,
            "knowledge_base_queries": kb_queries,
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
        session = self.db.query(PublicAgentSession).filter(
            and_(
                PublicAgentSession.session_id == session_id,
                PublicAgentSession.tenant_id == tenant_id
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
