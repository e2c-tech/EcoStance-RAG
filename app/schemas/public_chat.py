"""
Public Chat schemas - Pydantic models for request/response validation.
"""
from pydantic import BaseModel, Field, validator, conint, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import re


# ============================================================================
# Public Chat Query Schemas
# ============================================================================

class ConversationMessage(BaseModel):
    """Single message in conversation history."""
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")

    @validator('role')
    def validate_role(cls, v):
        if v not in ['user', 'assistant']:
            raise ValueError("Role must be 'user' or 'assistant'")
        return v


class PublicChatQueryRequest(BaseModel):
    """Request for public chat query."""
    session_id: str = Field(..., min_length=1, max_length=100, description="Unique session identifier")
    query: str = Field(..., min_length=1, max_length=2000, description="User query")
    conversation_history: Optional[List[ConversationMessage]] = Field(default=[], description="Previous conversation")


class SourceInfo(BaseModel):
    """Information about a source document."""
    filename: str
    chunk_number: Optional[int] = None
    similarity: Optional[float] = None
    preview: Optional[str] = None


class PublicChatQueryResponse(BaseModel):
    """Response for public chat query."""
    answer: str = Field(..., description="AI-generated answer")
    sources: Optional[List[SourceInfo]] = Field(default=[], description="Source documents")
    session_id: str = Field(..., description="Session identifier")
    timestamp: str = Field(..., description="Response timestamp")


# ============================================================================
# Public Chat Configuration Schemas
# ============================================================================

class BrandingConfig(BaseModel):
    """Branding configuration."""
    logo: Optional[str] = Field(None, description="Logo URL")
    primary_color: str = Field("#0066CC", description="Primary color (hex)")
    company_name: str = Field(..., min_length=1, max_length=100, description="Company name")
    
    @validator('primary_color')
    def validate_color(cls, v):
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError("Primary color must be a valid hex color (#RRGGBB)")
        return v


class RateLimitConfig(BaseModel):
    """Rate limit configuration."""
    queries_per_minute: conint(ge=1, le=100) = Field(10, description="Queries per minute")
    max_messages_per_session: conint(ge=1, le=200) = Field(50, description="Max messages per session")


class FeaturesConfig(BaseModel):
    """Features configuration."""
    show_sources: bool = Field(True, description="Show source documents")
    allow_feedback: bool = Field(True, description="Allow user feedback")
    show_suggested_questions: bool = Field(True, description="Show suggested questions")


class PublicChatConfigResponse(BaseModel):
    """Public chat configuration response (for public endpoint)."""
    enabled: bool
    welcome_message: str
    suggested_questions: List[str]
    branding: BrandingConfig
    rate_limit: RateLimitConfig
    features: FeaturesConfig


class PublicChatConfigDisabledResponse(BaseModel):
    """Response when public chat is disabled."""
    enabled: bool = False
    message: str = "Public chat is currently disabled."


# ============================================================================
# Feedback Schemas
# ============================================================================

class PublicChatFeedbackRequest(BaseModel):
    """Request to submit feedback."""
    session_id: str = Field(..., min_length=1, max_length=100)
    message_id: str = Field(..., min_length=1, max_length=100)
    feedback_type: str = Field(..., description="'positive' or 'negative'")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional comment")

    @validator('feedback_type')
    def validate_feedback_type(cls, v):
        if v not in ['positive', 'negative']:
            raise ValueError("Feedback type must be 'positive' or 'negative'")
        return v


class PublicChatFeedbackResponse(BaseModel):
    """Response after submitting feedback."""
    success: bool = True
    message: str = "Thank you for your feedback!"


# ============================================================================
# Admin Configuration Schemas
# ============================================================================

class AdminPublicChatConfigResponse(BaseModel):
    """Full configuration response for admin."""
    enabled: bool
    allowed_kbs: List[str]
    welcome_message: str
    suggested_questions: List[str]
    branding: BrandingConfig
    rate_limit: RateLimitConfig
    features: FeaturesConfig
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None


class AdminPublicChatConfigUpdate(BaseModel):
    """Request to update configuration."""
    enabled: bool
    allowed_kbs: List[str] = Field(..., description="List of KB IDs")
    welcome_message: str = Field(..., min_length=1, max_length=500)
    suggested_questions: List[str] = Field(..., max_items=10, description="Max 10 questions")
    branding: BrandingConfig
    rate_limit: RateLimitConfig
    features: FeaturesConfig

    @validator('suggested_questions')
    def validate_suggested_questions(cls, v):
        for q in v:
            if len(q) < 1 or len(q) > 200:
                raise ValueError("Each question must be 1-200 characters")
        return v


class AdminPublicChatConfigUpdateResponse(BaseModel):
    """Response after updating configuration."""
    success: bool = True
    message: str = "Configuration updated successfully"
    config: AdminPublicChatConfigResponse


# ============================================================================
# Knowledge Base Schemas
# ============================================================================

class AvailableKnowledgeBase(BaseModel):
    """Available knowledge base for selection."""
    id: str
    name: str
    document_count: int
    is_public: bool = False
    created_at: Optional[str] = None


class AvailableKnowledgeBasesResponse(BaseModel):
    """Response with available knowledge bases."""
    knowledge_bases: List[AvailableKnowledgeBase]


# ============================================================================
# Analytics Schemas
# ============================================================================

class AnalyticsPeriod(BaseModel):
    """Analytics period information."""
    start_date: str
    end_date: str
    days: int


class AnalyticsSummary(BaseModel):
    """Summary analytics."""
    total_sessions: int
    total_queries: int
    unique_visitors: int
    average_queries_per_session: float
    average_rating: Optional[float] = None


class TopQuestion(BaseModel):
    """Top question statistics."""
    question: str
    count: int
    percentage: float


class FeedbackSummary(BaseModel):
    """Feedback summary."""
    total_feedback: int
    positive: int
    negative: int
    positive_percentage: float


class UsageByDay(BaseModel):
    """Usage statistics by day."""
    date: str
    sessions: int
    queries: int
    positive_feedback: int
    negative_feedback: int


class RateLimitHits(BaseModel):
    """Rate limit violations."""
    queries_per_minute: int
    max_messages_per_session: int


class PublicChatAnalyticsResponse(BaseModel):
    """Analytics response."""
    period: AnalyticsPeriod
    summary: AnalyticsSummary
    top_questions: List[TopQuestion]
    feedback_summary: FeedbackSummary
    usage_by_day: List[UsageByDay]
    rate_limit_hits: RateLimitHits


# ============================================================================
# Session Details Schemas
# ============================================================================

class SessionMessage(BaseModel):
    """Message in session details."""
    id: str
    role: str
    content: str
    timestamp: str
    sources: Optional[List[SourceInfo]] = None
    feedback: Optional[str] = None


class SessionMetadata(BaseModel):
    """Session metadata."""
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    referrer: Optional[str] = None


class SessionDetailsResponse(BaseModel):
    """Detailed session information."""
    session_id: str
    started_at: str
    ended_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    message_count: int
    messages: List[SessionMessage]
    metadata: SessionMetadata


# ============================================================================
# Error Schemas
# ============================================================================

class PublicChatError(BaseModel):
    """Error response."""
    detail: str
    error_code: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class RateLimitError(BaseModel):
    """Rate limit error response."""
    detail: str = "Rate limit exceeded. Please wait before sending another message."
    retry_after: int = Field(..., description="Seconds to wait")
