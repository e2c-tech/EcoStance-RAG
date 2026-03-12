"""
Public Agent schemas - Pydantic models for request/response validation.
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import re


# ============================================================================
# Public Agent Chat Schemas
# ============================================================================

class ConversationMessage(BaseModel):
    """Single message in conversation history."""
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: Any = Field(..., description="Message content")

    @validator('role')
    def validate_role(cls, v):
        if v not in ['user', 'assistant']:
            raise ValueError("Role must be 'user' or 'assistant'")
        return v


class PublicAgentChatRequest(BaseModel):
    """Request for public agent chat."""
    session_id: str = Field(..., min_length=1, max_length=100, description="Unique session identifier")
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    conversation_history: Optional[List[ConversationMessage]] = Field(default=[], description="Previous conversation")
    agent_type: Optional[str] = Field(None, description="Optional agent type override (quickship, ecommerce, etc.)")
    user_language: Optional[str] = Field(None, description="Optional user language preference (en, es, fr, etc.)")
    knowledge_base: Optional[str] = Field(None, description="Optional selected knowledge base name")
    database_connection: Optional[str] = Field(None, description="Optional selected database connection ID")


class SourceInfo(BaseModel):
    """Information about a source document."""
    filename: str
    chunk_number: Optional[int] = None
    similarity: Optional[float] = None
    preview: Optional[str] = None


class PublicAgentChatResponse(BaseModel):
    """Response for public agent chat."""
    response: Any = Field(..., description="AI-generated response")
    sources: Optional[List[SourceInfo]] = Field(default=[], description="Source documents")
    tool_used: Optional[str] = Field(None, description="Tool that was used (database/knowledge_base)")
    session_id: str = Field(..., description="Session identifier")
    agent_type: str = Field(..., description="Type of agent that processed the request")
    timestamp: str = Field(..., description="Response timestamp")


# ============================================================================
# Public Agent Configuration Schemas
# ============================================================================

class BrandingConfig(BaseModel):
    """Branding configuration."""
    logo_url: Optional[str] = Field(None, description="Logo URL")
    primary_color: str = Field("#0066CC", description="Primary color (hex)")
    company_name: str = Field(..., min_length=1, max_length=100, description="Company name")
    font_family: Optional[str] = Field("Arial, sans-serif", description="Font family (e.g., 'Arial, sans-serif')")
    font_size: Optional[str] = Field("14px", description="Base font size (e.g., '14px')")
    
    @validator('primary_color')
    def validate_color(cls, v):
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError("Primary color must be a valid hex color (#RRGGBB)")
        return v


class RateLimitConfig(BaseModel):
    """Rate limit configuration."""
    queries_per_minute: int = Field(10, ge=1, le=100, description="Queries per minute")
    max_messages_per_session: int = Field(50, ge=1, le=200, description="Max messages per session")


class FeaturesConfig(BaseModel):
    """Features configuration."""
    show_sources: bool = Field(True, description="Show source documents")
    allow_feedback: bool = Field(True, description="Allow user feedback")
    show_suggested_questions: bool = Field(True, description="Show suggested questions")
    enable_database_tools: bool = Field(True, description="Enable database query tools")
    enable_knowledge_base: bool = Field(True, description="Enable knowledge base search")


class PublicAgentConfigResponse(BaseModel):
    """Public agent configuration response (for public endpoint)."""
    enabled: bool
    welcome_message: str
    suggested_questions: List[str]
    branding: BrandingConfig
    rate_limit: RateLimitConfig
    features: FeaturesConfig
    agent_type: str = Field("quickship", description="Type of agent (e.g., quickship, ecommerce)")


class PublicAgentConfigDisabledResponse(BaseModel):
    """Response when public agent is disabled."""
    enabled: bool = False
    message: str = "Public agent is currently disabled."


# ============================================================================
# Feedback Schemas
# ============================================================================

class PublicAgentFeedbackRequest(BaseModel):
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


class PublicAgentFeedbackResponse(BaseModel):
    """Response after submitting feedback."""
    success: bool = True
    message: str = "Thank you for your feedback!"


# ============================================================================
# Admin Configuration Schemas
# ============================================================================

class AdminPublicAgentConfigResponse(BaseModel):
    """Full configuration response for admin."""
    enabled: bool
    allowed_kbs: List[str]
    allowed_dbs: List[str]
    allowed_tools: List[str] = Field(..., description="Allowed tool categories: tracking, payments, complaints, delivery_estimates")
    welcome_message: str
    suggested_questions: List[str]
    branding: BrandingConfig
    rate_limit: RateLimitConfig
    features: FeaturesConfig
    agent_type: str = Field("quickship", description="Type of agent (e.g., quickship, ecommerce)")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None


class AdminPublicAgentConfigUpdate(BaseModel):
    """Request to update configuration."""
    enabled: Optional[bool] = None
    allowed_kbs: Optional[List[str]] = Field(None, description="List of KB IDs")
    allowed_dbs: Optional[List[str]] = Field(None, description="List of database connection IDs")
    allowed_tools: Optional[List[str]] = Field(None, description="Allowed tool categories")
    welcome_message: Optional[str] = Field(None, min_length=1, max_length=500)
    suggested_questions: Optional[List[str]] = Field(None, max_items=10, description="Max 10 questions")
    branding: Optional[BrandingConfig] = None
    rate_limit: Optional[RateLimitConfig] = None
    features: Optional[FeaturesConfig] = None
    agent_type: Optional[str] = Field(None, description="Type of agent (e.g., quickship, ecommerce)")

    @validator('agent_type')
    def validate_agent_type(cls, v):
        valid_agents = ['quickship', 'ecommerce', 'ecostance', 'realestate', 'generic', 'security_analyst']
        if v not in valid_agents:
            raise ValueError(f"Invalid agent type: {v}. Must be one of: {', '.join(valid_agents)}")
        return v

    @validator('allowed_tools')
    def validate_allowed_tools(cls, v):
        valid_tools = [
            'tracking', 'payments', 'complaints', 'delivery_estimates', 'customer_search',
            'certificates', 'shopping', 'impact', 'faq', 'siem'
        ]
        for tool in v:
            if tool not in valid_tools:
                raise ValueError(f"Invalid tool: {tool}. Must be one of: {', '.join(valid_tools)}")
        return v

    @validator('suggested_questions')
    def validate_suggested_questions(cls, v):
        for q in v:
            if len(q) < 1 or len(q) > 200:
                raise ValueError("Each question must be 1-200 characters")
        return v


class AdminPublicAgentConfigUpdateResponse(BaseModel):
    """Response after updating configuration."""
    success: bool = True
    message: str = "Configuration updated successfully"
    config: AdminPublicAgentConfigResponse


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
# Database Schemas
# ============================================================================

class AvailableDatabase(BaseModel):
    """Available database connection for selection."""
    id: str
    name: str
    type: str
    database: str
    host: Optional[str] = None


class AvailableDatabasesResponse(BaseModel):
    """Response with available databases."""
    databases: List[AvailableDatabase]


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
    database_queries: int
    knowledge_base_queries: int


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


class PublicAgentAnalyticsResponse(BaseModel):
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
    content: Any
    timestamp: str
    sources: Optional[List[SourceInfo]] = None
    tool_used: Optional[str] = None
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

class PublicAgentError(BaseModel):
    """Error response."""
    detail: str
    error_code: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class RateLimitError(BaseModel):
    """Rate limit error response."""
    detail: str = "Rate limit exceeded. Please wait before sending another message."
    retry_after: int = Field(..., description="Seconds to wait")
