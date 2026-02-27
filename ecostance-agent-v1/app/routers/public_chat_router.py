"""
Public Chat Router - API endpoints for public chat functionality.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import logging
import json

from ..db.database import get_db
from ..services.public_chat_service import PublicChatService
from ..services.rag_service import RAGService
from ..auth.dependencies import get_current_user, require_admin
from ..models.tenant_user import TenantUser
from ..schemas.public_chat import (
    PublicChatQueryRequest,
    PublicChatQueryResponse,
    PublicChatConfigResponse,
    PublicChatConfigDisabledResponse,
    PublicChatFeedbackRequest,
    PublicChatFeedbackResponse,
    AdminPublicChatConfigResponse,
    AdminPublicChatConfigUpdate,
    AdminPublicChatConfigUpdateResponse,
    AvailableKnowledgeBasesResponse,
    PublicChatAnalyticsResponse,
    SessionDetailsResponse,
    PublicChatError,
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
    """Extract tenant ID from request (typically from X-Tenant-ID header)."""
    # Try to get from header first
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id:
        # Check if it was set by middleware in request state (e.g. from JWT)
        tenant_id = getattr(request.state, "tenant_id", None)
        
    if not tenant_id:
        logger.error("Request missing X-Tenant-ID header in public chat")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header is missing. This is required to identify the tenant."
        )
    return tenant_id


def get_client_metadata(request: Request) -> dict:
    """Extract client metadata from request."""
    return {
        "user_agent": request.headers.get("user-agent"),
        "ip_address": request.client.host if request.client else None,
        "referrer": request.headers.get("referer")
    }


# ============================================================================
# Public Chat Endpoints (No Authentication Required)
# ============================================================================

@router.post(
    "/api/v1/public-chat/query",
    response_model=PublicChatQueryResponse,
    responses={
        429: {"model": RateLimitError},
        503: {"model": PublicChatError}
    },
    tags=["Public Chat"]
)
async def query_public_chat(
    request_data: PublicChatQueryRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Send a query to the public chat and get an AI response.
    
    This endpoint is public and does not require authentication.
    Rate limiting is applied per session.
    """
    try:
        tenant_id = get_tenant_id_from_request(request)
        service = PublicChatService(db)
        
        # Get configuration
        config = service.get_config(tenant_id)
        if not config or not config.enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Public chat is currently disabled."
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
            content=request_data.query
        )
        
        # Get allowed KBs
        allowed_kbs = json.loads(config.allowed_kbs) if isinstance(config.allowed_kbs, str) else config.allowed_kbs
        if not allowed_kbs:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No knowledge bases configured for public chat"
            )
        
        # Use shared multilingual RAG service
        from app.services.rag_service import RAGService
        from app.config.multilingual_app_config import should_use_multilingual_processing
        from ..services.qdrant_service import get_qdrant_client
        from ..services.tenant_service import get_tenant_service
        from langchain_core.messages import HumanMessage, AIMessage
        from ..models.tenant_knowledge_base import TenantKnowledgeBase
        
        # Get the first allowed KB - it might be a collection name or kb_name
        first_kb = allowed_kbs[0]
        
        # Check if it's a full collection name or just a kb_name
        if first_kb.startswith("tenant_"):
            # It's a full collection name, use it directly
            collection_name = first_kb
            # Extract kb_name from collection for logging
            kb_name = first_kb.split("_", 2)[-1] if "_" in first_kb else first_kb
        else:
            # It's a kb_name, generate the collection name
            kb_name = first_kb
            qdrant_client = get_qdrant_client()
            tenant_service = get_tenant_service(qdrant_client)
            collection_name = tenant_service.get_collection_name(tenant_id, kb_name)
        
        # Verify collection exists
        qdrant_client = get_qdrant_client()
        tenant_service = get_tenant_service(qdrant_client)
        if not tenant_service.collection_exists(collection_name):
            raise HTTPException(
                status_code=404,
                detail=f"Knowledge base '{kb_name}' not found"
            )
        
        logger.info(f"Public chat query for tenant {tenant_id}, kb: {kb_name}, collection: {collection_name}")
        logger.info(f"Query: {request_data.query}")
        
        # Convert conversation history to LangChain format
        processed_chat_history = []
        if request_data.conversation_history:
            for msg in request_data.conversation_history[-5:]:  # Last 5 messages
                if msg.role == "user":
                    processed_chat_history.append(HumanMessage(content=msg.content))
                else:
                    processed_chat_history.append(AIMessage(content=msg.content))
        
        # Execute query using multilingual RAG service
        try:
            if should_use_multilingual_processing(tenant_id):
                # Use shared multilingual RAG service
                rag_service_instance = RAGService(db)
                
                answer = await rag_service_instance.query_knowledge_base_multilingual(
                    tenant_id=tenant_id,
                    kb_name=kb_name,
                    query=request_data.query,
                    chat_history=processed_chat_history
                )
            else:
                # Fallback to legacy service
                from ..services.query_service import execute_query
                answer = execute_query(collection_name, request_data.query, processed_chat_history, tenant_id=tenant_id)
                
        except Exception as query_error:
            logger.error(f"Error executing query: {query_error}")
            answer = "I apologize, but I'm having trouble accessing the information right now. Please try again later."
        logger.info(f"Query executed successfully. Answer: {answer}")
        
        # Add assistant message
        assistant_message = service.add_message(
            session_id=request_data.session_id,
            tenant_id=tenant_id,
            role="assistant",
            content=answer,
            sources=None  # Can add source retrieval later if needed
        )
        
        # Update session activity
        service.update_session_activity(request_data.session_id, is_query=True)
        
        return PublicChatQueryResponse(
            answer=answer,
            sources=[],  # Empty for now, matching the working endpoint
            session_id=request_data.session_id,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in public chat query: {str(e)}", exc_info=True)
        return PublicChatQueryResponse(
            answer="I'm sorry, I encountered an error while processing your question. Please try again.",
            sources=[],
            session_id=request_data.session_id,
            timestamp=datetime.utcnow().isoformat()
        )


@router.get(
    "/api/v1/public-chat/config",
    response_model=PublicChatConfigResponse,
    responses={
        503: {"model": PublicChatConfigDisabledResponse}
    },
    tags=["Public Chat"]
)
async def get_public_chat_config(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get the current public chat configuration for rendering the UI.
    
    This endpoint is public and does not require authentication.
    """
    try:
        tenant_id = get_tenant_id_from_request(request)
        service = PublicChatService(db)
        
        config = service.get_config(tenant_id)
        if not config or not config.enabled:
            # Return a proper config response with enabled=False
            # This ensures the response matches the expected schema
            return PublicChatConfigResponse(
                enabled=False,
                welcome_message="Public chat is currently disabled.",
                suggested_questions=[],
                branding=BrandingConfig(
                    primary_color="#0066CC",
                    company_name="Assistant"
                ),
                rate_limit=RateLimitConfig(
                    queries_per_minute=10,
                    max_messages_per_session=50
                ),
                features=FeaturesConfig(
                    show_sources=True,
                    allow_feedback=True,
                    show_suggested_questions=True
                )
            )
        
        config_dict = config.to_dict(include_sensitive=False)
        
        return PublicChatConfigResponse(
            enabled=config_dict["enabled"],
            welcome_message=config_dict["welcome_message"],
            suggested_questions=config_dict["suggested_questions"],
            branding=BrandingConfig(**config_dict["branding"]),
            rate_limit=RateLimitConfig(**config_dict["rate_limit"]),
            features=FeaturesConfig(**config_dict["features"])
        )
        
    except Exception as e:
        logger.error(f"Error getting public chat config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching configuration"
        )


@router.post(
    "/api/v1/public-chat/feedback",
    response_model=PublicChatFeedbackResponse,
    tags=["Public Chat"]
)
async def submit_feedback(
    feedback_data: PublicChatFeedbackRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Submit feedback for a chat message.
    
    This endpoint is public and does not require authentication.
    """
    try:
        tenant_id = get_tenant_id_from_request(request)
        service = PublicChatService(db)
        
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
        
        return PublicChatFeedbackResponse()
        
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
    "/api/v1/admin/public-chat/config",
    response_model=AdminPublicChatConfigResponse,
    dependencies=[Depends(require_admin)],
    tags=["Public Chat Admin"]
)
async def get_admin_config(
    current_user: TenantUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the full public chat configuration for admin panel.
    
    Requires admin or super_admin role.
    """
    try:
        service = PublicChatService(db)
        
        # Get or create config
        from ..models.tenant import Tenant
        
        # current_user is a dict, not an object
        tenant_id = current_user["tenant_id"]
        
        try:
            tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
            tenant_name = tenant.name if tenant else "Unknown"
        except Exception as e:
            logger.warning(f"Could not fetch tenant name: {e}")
            tenant_name = "Unknown"
        
        config = service.get_or_create_config(tenant_id, tenant_name)
        logger.info(f"Got config for tenant {tenant_id}")
        
        try:
            config_dict = config.to_dict(include_sensitive=True)
            logger.info(f"Config dict: {config_dict}")
        except Exception as dict_error:
            logger.error(f"Error converting config to dict: {str(dict_error)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error converting configuration: {str(dict_error)}"
            )
        
        try:
            return AdminPublicChatConfigResponse(
                enabled=config_dict["enabled"],
                allowed_kbs=config_dict["allowed_kbs"],
                welcome_message=config_dict["welcome_message"],
                suggested_questions=config_dict["suggested_questions"],
                branding=BrandingConfig(**config_dict["branding"]),
                rate_limit=RateLimitConfig(**config_dict["rate_limit"]),
                features=FeaturesConfig(**config_dict["features"]),
                created_at=config_dict.get("created_at"),
                updated_at=config_dict.get("updated_at"),
                updated_by=config_dict.get("updated_by")
            )
        except Exception as response_error:
            logger.error(f"Error creating response: {str(response_error)}", exc_info=True)
            logger.error(f"Config dict was: {config_dict}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating response: {str(response_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting admin config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching configuration: {str(e)}"
        )


@router.put(
    "/api/v1/admin/public-chat/config",
    response_model=AdminPublicChatConfigUpdateResponse,
    dependencies=[Depends(require_admin)],
    tags=["Public Chat Admin"]
)
async def update_admin_config(
    update_data: AdminPublicChatConfigUpdate,
    current_user: TenantUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the public chat configuration.
    
    Requires admin or super_admin role.
    """
    try:
        service = PublicChatService(db)
        
        # Update configuration
        config = service.update_config(
            tenant_id=current_user["tenant_id"],
            update_data=update_data,
            updated_by=current_user.get("email", "unknown")
        )
        
        config_dict = config.to_dict(include_sensitive=True)
        
        return AdminPublicChatConfigUpdateResponse(
            config=AdminPublicChatConfigResponse(
                enabled=config_dict["enabled"],
                allowed_kbs=config_dict["allowed_kbs"],
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
    "/api/v1/admin/public-chat/available-kbs",
    response_model=AvailableKnowledgeBasesResponse,
    dependencies=[Depends(require_admin)],
    tags=["Public Chat Admin"]
)
async def get_available_kbs(
    current_user: TenantUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of knowledge bases that can be selected for public chat.
    
    Requires admin or super_admin role.
    """
    try:
        service = PublicChatService(db)
        try:
            kbs = service.get_available_kbs(current_user["tenant_id"])
        except Exception as kb_error:
            logger.error(f"Error in get_available_kbs: {str(kb_error)}", exc_info=True)
            # Return empty list if there's an error
            kbs = []
        
        return AvailableKnowledgeBasesResponse(knowledge_bases=kbs)
        
    except Exception as e:
        logger.error(f"Error getting available KBs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching knowledge bases: {str(e)}"
        )


@router.get(
    "/api/v1/admin/public-chat/available-dbs",
    dependencies=[Depends(require_admin)],
    tags=["Public Chat Admin"]
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
            return {"databases": []}
        
        with open(connections_file, 'r') as f:
            connections = json.load(f)
        
        # Format connections for response
        databases = []
        for conn_id, conn_data in connections.items():
            databases.append({
                "id": conn_id,
                "name": conn_id.replace("-", " ").title(),
                "type": conn_data.get("type", "unknown"),
                "database": conn_data.get("database", ""),
                "host": conn_data.get("host", "") if conn_data.get("type") != "sqlite" else None
            })
        
        return {"databases": databases}
        
    except Exception as e:
        logger.error(f"Error getting available databases: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching databases: {str(e)}"
        )


@router.get(
    "/api/v1/admin/public-chat/analytics",
    response_model=PublicChatAnalyticsResponse,
    dependencies=[Depends(require_admin)],
    tags=["Public Chat Admin"]
)
async def get_analytics(
    days: int = 30,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: TenantUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get usage statistics and analytics for public chat.
    
    Requires admin or super_admin role.
    """
    try:
        service = PublicChatService(db)
        
        # Parse dates
        if start_date and end_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end = datetime.utcnow()
            start = end - timedelta(days=days)
        
        # Get analytics
        analytics = service.get_analytics(current_user["tenant_id"], start, end)
        
        return PublicChatAnalyticsResponse(
            period={
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "days": (end - start).days
            },
            summary=analytics,
            top_questions=analytics["top_questions"],
            feedback_summary=analytics["feedback_summary"],
            usage_by_day=[],  # Can be implemented later
            rate_limit_hits={"queries_per_minute": 0, "max_messages_per_session": 0}  # Can be tracked later
        )
        
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching analytics"
        )


@router.get(
    "/api/v1/admin/public-chat/sessions/{session_id}",
    response_model=SessionDetailsResponse,
    dependencies=[Depends(require_admin)],
    tags=["Public Chat Admin"]
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
        service = PublicChatService(db)
        
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
