"""
Public Agent Router - API endpoints for public agent functionality.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import logging
import json

from ..db.database import get_db
from ..services.public_agent_service import PublicAgentService
from ..auth.dependencies import get_current_user, require_admin
from ..models.tenant_user import TenantUser
from ..schemas.public_agent import (
    PublicAgentChatRequest,
    PublicAgentChatResponse,
    PublicAgentConfigResponse,
    PublicAgentConfigDisabledResponse,
    PublicAgentFeedbackRequest,
    PublicAgentFeedbackResponse,
    AdminPublicAgentConfigResponse,
    AdminPublicAgentConfigUpdate,
    AdminPublicAgentConfigUpdateResponse,
    AvailableKnowledgeBasesResponse,
    AvailableDatabasesResponse,
    AvailableDatabase,
    PublicAgentAnalyticsResponse,
    SessionDetailsResponse,
    PublicAgentError,
    RateLimitError,
    SourceInfo,
    BrandingConfig,
    RateLimitConfig,
    FeaturesConfig
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Helper Functions
# ============================================================================

def get_tenant_id_from_request(request: Request) -> str:
    """Extract tenant ID from request (from subdomain, header, or default)."""
    # Try to get from header first
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        return tenant_id
    
    # For now, use CertifyDigital tenant as default
    return "badcd123-6cc6-4011-b01b-d33d1153f10d"


def get_client_metadata(request: Request) -> dict:
    """Extract client metadata from request."""
    return {
        "user_agent": request.headers.get("user-agent"),
        "ip_address": request.client.host if request.client else None,
        "referrer": request.headers.get("referer")
    }


# ============================================================================
# Public Agent Endpoints (No Authentication Required)
# ============================================================================

@router.post(
    "/api/v1/public-agent/chat",
    response_model=PublicAgentChatResponse,
    responses={
        429: {"model": RateLimitError},
        503: {"model": PublicAgentError}
    },
    tags=["Public Agent"]
)
async def chat_with_public_agent(
    request_data: PublicAgentChatRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Send a message to the public agent and get an AI response.
    
    The agent can query databases and search knowledge bases based on the question.
    This endpoint is public and does not require authentication.
    Rate limiting is applied per session.
    """
    try:
        tenant_id = get_tenant_id_from_request(request)
        service = PublicAgentService(db)
        
        # Get configuration
        config = service.get_config(tenant_id)
        if not config or not config.enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Public agent is currently disabled."
            )
        
        # Check rate limits
        allowed, error_msg = service.check_rate_limit(request_data.session_id, config)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_msg,
                headers={"Retry-After": "60"}
            )
        
        # Get or create session
        metadata = get_client_metadata(request)
        session = service.get_or_create_session(
            request_data.session_id,
            tenant_id,
            metadata
        )
        
        # Check if session is expired
        if service.is_session_expired(request_data.session_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session has expired"
            )
        
        # Add user message
        user_message = service.add_message(
            session_id=request_data.session_id,
            tenant_id=tenant_id,
            role="user",
            content=request_data.message
        )
        
        # Get allowed KBs, DBs, and tools
        allowed_kbs = json.loads(config.allowed_kbs) if isinstance(config.allowed_kbs, str) else config.allowed_kbs
        allowed_dbs = json.loads(config.allowed_dbs) if isinstance(config.allowed_dbs, str) else config.allowed_dbs
        allowed_tools = json.loads(config.allowed_tools) if isinstance(config.allowed_tools, str) else config.allowed_tools
        features = json.loads(config.features) if isinstance(config.features, str) else config.features
        
        # Check if at least one tool is enabled
        if not features.get("enable_database_tools") and not features.get("enable_knowledge_base"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No tools are enabled for the public agent"
            )
        
        # Use the agent service to process the message
        from quickship_agent.public_agent_service import PublicAgentService as AgentServiceClass
        
        agent = AgentServiceClass(tenant_id=tenant_id, allowed_tools=allowed_tools)
        
        # Determine which KB to use (first allowed KB)
        kb_name = allowed_kbs[0] if allowed_kbs and features.get("enable_knowledge_base") else None
        
        # Determine which DB to use (first allowed DB)
        db_connection = allowed_dbs[0] if allowed_dbs and features.get("enable_database_tools") else None
        
        logger.info(f"Public agent chat for tenant {tenant_id}")
        logger.info(f"Message: {request_data.message}")
        logger.info(f"KB: {kb_name}, DB: {db_connection}")
        logger.info(f"Allowed tools: {allowed_tools}")
        
        # Call the agent
        agent_response = agent.chat(
            session_id=request_data.session_id,
            message=request_data.message,
            knowledge_base=kb_name,
            database_connection=db_connection
        )
        
        response_text = agent_response.get("response", "I'm sorry, I couldn't process your request.")
        tool_used = agent_response.get("tool_used")  # Can be added to agent response
        
        # Add assistant message
        assistant_message = service.add_message(
            session_id=request_data.session_id,
            tenant_id=tenant_id,
            role="assistant",
            content=response_text,
            sources=None,  # Can add source retrieval later
            tool_used=tool_used
        )
        
        # Update session activity
        service.update_session_activity(request_data.session_id, is_query=True)
        
        return PublicAgentChatResponse(
            response=response_text,
            sources=[],
            tool_used=tool_used,
            session_id=request_data.session_id,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in public agent chat: {str(e)}", exc_info=True)
        return PublicAgentChatResponse(
            response="I'm sorry, I encountered an error while processing your message. Please try again.",
            sources=[],
            tool_used=None,
            session_id=request_data.session_id,
            timestamp=datetime.utcnow().isoformat()
        )


@router.get(
    "/api/v1/public-agent/config",
    response_model=PublicAgentConfigResponse,
    responses={
        503: {"model": PublicAgentConfigDisabledResponse}
    },
    tags=["Public Agent"]
)
async def get_public_agent_config(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get the current public agent configuration for rendering the UI.
    
    This endpoint is public and does not require authentication.
    """
    try:
        tenant_id = get_tenant_id_from_request(request)
        service = PublicAgentService(db)
        
        config = service.get_config(tenant_id)
        if not config or not config.enabled:
            return PublicAgentConfigResponse(
                enabled=False,
                welcome_message="Public agent is currently disabled.",
                suggested_questions=[],
                branding=BrandingConfig(
                    primary_color="#0066CC",
                    company_name="QuickShip"
                ),
                rate_limit=RateLimitConfig(
                    queries_per_minute=10,
                    max_messages_per_session=50
                ),
                features=FeaturesConfig(
                    show_sources=True,
                    allow_feedback=True,
                    show_suggested_questions=True,
                    enable_database_tools=True,
                    enable_knowledge_base=True
                )
            )
        
        config_dict = config.to_dict(include_sensitive=False)
        
        return PublicAgentConfigResponse(
            enabled=config_dict["enabled"],
            welcome_message=config_dict["welcome_message"],
            suggested_questions=config_dict["suggested_questions"],
            branding=BrandingConfig(**config_dict["branding"]),
            rate_limit=RateLimitConfig(**config_dict["rate_limit"]),
            features=FeaturesConfig(**config_dict["features"])
        )
        
    except Exception as e:
        logger.error(f"Error getting public agent config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching configuration"
        )


@router.post(
    "/api/v1/public-agent/feedback",
    response_model=PublicAgentFeedbackResponse,
    tags=["Public Agent"]
)
async def submit_feedback(
    feedback_data: PublicAgentFeedbackRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Submit feedback for an agent message.
    
    This endpoint is public and does not require authentication.
    """
    try:
        tenant_id = get_tenant_id_from_request(request)
        service = PublicAgentService(db)
        
        # Verify session exists
        session = service.get_session(feedback_data.session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Add feedback
        service.add_feedback(
            session_id=feedback_data.session_id,
            message_id=feedback_data.message_id,
            tenant_id=tenant_id,
            feedback_type=feedback_data.feedback_type,
            comment=feedback_data.comment
        )
        
        return PublicAgentFeedbackResponse()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while submitting feedback"
        )


# ============================================================================
# Admin Configuration Endpoints (Authentication Required)
# ============================================================================

@router.get(
    "/api/v1/admin/public-agent/config",
    response_model=AdminPublicAgentConfigResponse,
    dependencies=[Depends(require_admin)],
    tags=["Public Agent Admin"]
)
async def get_admin_config(
    current_user: TenantUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the full public agent configuration for admin panel.
    
    Requires admin or super_admin role.
    """
    try:
        service = PublicAgentService(db)
        
        from ..models.tenant import Tenant
        
        tenant_id = current_user["tenant_id"]
        
        try:
            tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
            tenant_name = tenant.name if tenant else "Unknown"
        except Exception as e:
            logger.warning(f"Could not fetch tenant name: {e}")
            tenant_name = "Unknown"
        
        config = service.get_or_create_config(tenant_id, tenant_name)
        config_dict = config.to_dict(include_sensitive=True)
        
        return AdminPublicAgentConfigResponse(
            enabled=config_dict["enabled"],
            allowed_kbs=config_dict["allowed_kbs"],
            allowed_dbs=config_dict["allowed_dbs"],
            allowed_tools=config_dict.get("allowed_tools", ["tracking", "payments", "complaints", "delivery_estimates"]),
            welcome_message=config_dict["welcome_message"],
            suggested_questions=config_dict["suggested_questions"],
            branding=BrandingConfig(**config_dict["branding"]),
            rate_limit=RateLimitConfig(**config_dict["rate_limit"]),
            features=FeaturesConfig(**config_dict["features"]),
            created_at=config_dict.get("created_at"),
            updated_at=config_dict.get("updated_at"),
            updated_by=config_dict.get("updated_by")
        )
        
    except Exception as e:
        logger.error(f"Error getting admin config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching configuration: {str(e)}"
        )


@router.put(
    "/api/v1/admin/public-agent/config",
    response_model=AdminPublicAgentConfigUpdateResponse,
    dependencies=[Depends(require_admin)],
    tags=["Public Agent Admin"]
)
async def update_admin_config(
    update_data: AdminPublicAgentConfigUpdate,
    current_user: TenantUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the public agent configuration.
    
    Requires admin or super_admin role.
    """
    try:
        service = PublicAgentService(db)
        
        # Update configuration
        config = service.update_config(
            tenant_id=current_user["tenant_id"],
            update_data=update_data,
            updated_by=current_user.get("email", "unknown")
        )
        
        config_dict = config.to_dict(include_sensitive=True)
        
        return AdminPublicAgentConfigUpdateResponse(
            config=AdminPublicAgentConfigResponse(
                enabled=config_dict["enabled"],
                allowed_kbs=config_dict["allowed_kbs"],
                allowed_dbs=config_dict["allowed_dbs"],
                allowed_tools=config_dict.get("allowed_tools", ["tracking", "payments", "complaints", "delivery_estimates"]),
                welcome_message=config_dict["welcome_message"],
                suggested_questions=config_dict["suggested_questions"],
                branding=BrandingConfig(**config_dict["branding"]),
                rate_limit=RateLimitConfig(**config_dict["rate_limit"]),
                features=FeaturesConfig(**config_dict["features"]),
                created_at=config_dict.get("created_at"),
                updated_at=config_dict.get("updated_at"),
                updated_by=config_dict.get("updated_by")
            )
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating admin config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating configuration"
        )


@router.get(
    "/api/v1/admin/public-agent/available-kbs",
    response_model=AvailableKnowledgeBasesResponse,
    dependencies=[Depends(require_admin)],
    tags=["Public Agent Admin"]
)
async def get_available_kbs(
    current_user: TenantUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of knowledge bases that can be selected for public agent.
    
    Requires admin or super_admin role.
    """
    try:
        service = PublicAgentService(db)
        kbs = service.get_available_kbs(current_user["tenant_id"])
        
        return AvailableKnowledgeBasesResponse(knowledge_bases=kbs)
        
    except Exception as e:
        logger.error(f"Error getting available KBs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching knowledge bases: {str(e)}"
        )


@router.get(
    "/api/v1/admin/public-agent/available-dbs",
    response_model=AvailableDatabasesResponse,
    dependencies=[Depends(require_admin)],
    tags=["Public Agent Admin"]
)
async def get_available_dbs(
    current_user: TenantUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of database connections available for the tenant.
    
    Requires admin or super_admin role.
    """
    try:
        import json
        import os
        
        connections_file = ".db_connections/connections.json"
        
        if not os.path.exists(connections_file):
            return AvailableDatabasesResponse(databases=[])
        
        with open(connections_file, 'r') as f:
            connections = json.load(f)
        
        # Format connections for response
        databases = []
        for conn_id, conn_data in connections.items():
            databases.append(AvailableDatabase(
                id=conn_id,
                name=conn_id.replace("-", " ").title(),
                type=conn_data.get("type", "unknown"),
                database=conn_data.get("database", ""),
                host=conn_data.get("host", "") if conn_data.get("type") != "sqlite" else None
            ))
        
        return AvailableDatabasesResponse(databases=databases)
        
    except Exception as e:
        logger.error(f"Error getting available databases: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching databases: {str(e)}"
        )


@router.get(
    "/api/v1/admin/public-agent/available-tools",
    dependencies=[Depends(require_admin)],
    tags=["Public Agent Admin"]
)
async def get_available_tools(
    current_user: TenantUser = Depends(get_current_user)
):
    """
    Get list of available tool categories that can be enabled for public agent.
    
    Requires admin or super_admin role.
    """
    return {
        "tools": [
            {
                "id": "tracking",
                "name": "Shipment Tracking",
                "description": "Track shipments by ID or tracking number",
                "functions": ["get_shipment_status", "track_by_tracking_number"]
            },
            {
                "id": "customer_search",
                "name": "Customer Search",
                "description": "Search shipments by customer phone or email",
                "functions": ["search_shipments_by_customer"]
            },
            {
                "id": "delivery_estimates",
                "name": "Delivery Estimates",
                "description": "Get delivery date estimates",
                "functions": ["get_delivery_estimate"]
            },
            {
                "id": "payments",
                "name": "Payment Information",
                "description": "Check COD and payment status",
                "functions": ["check_cod_payment_status"]
            },
            {
                "id": "complaints",
                "name": "Complaint Status",
                "description": "Check complaint status for shipments",
                "functions": ["get_complaint_status"]
            }
        ]
    }


@router.get(
    "/api/v1/admin/public-agent/analytics",
    response_model=PublicAgentAnalyticsResponse,
    dependencies=[Depends(require_admin)],
    tags=["Public Agent Admin"]
)
async def get_analytics(
    days: int = 30,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: TenantUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get usage statistics and analytics for public agent.
    
    Requires admin or super_admin role.
    """
    try:
        service = PublicAgentService(db)
        
        # Parse dates
        if start_date and end_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end = datetime.utcnow()
            start = end - timedelta(days=days)
        
        # Get analytics
        analytics = service.get_analytics(current_user["tenant_id"], start, end)
        
        return PublicAgentAnalyticsResponse(
            period={
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "days": (end - start).days
            },
            summary=analytics,
            top_questions=analytics["top_questions"],
            feedback_summary=analytics["feedback_summary"],
            usage_by_day=[],
            rate_limit_hits={"queries_per_minute": 0, "max_messages_per_session": 0}
        )
        
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching analytics"
        )


@router.get(
    "/api/v1/admin/public-agent/sessions/{session_id}",
    response_model=SessionDetailsResponse,
    dependencies=[Depends(require_admin)],
    tags=["Public Agent Admin"]
)
async def get_session_details(
    session_id: str,
    current_user: TenantUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific session.
    
    Requires admin or super_admin role.
    """
    try:
        service = PublicAgentService(db)
        
        session_details = service.get_session_details(session_id, current_user["tenant_id"])
        if not session_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        return SessionDetailsResponse(**session_details)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session details: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching session details"
        )
