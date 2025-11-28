"""
FastAPI Router for QuickShip AI Agent
Provides REST API endpoints for the agent
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional
import uuid
import logging

from .agent_service import AgentService
from app.auth.dependencies import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Store agent services per tenant
_agent_services: Dict[str, AgentService] = {}


def get_agent_service(tenant_id: str) -> AgentService:
    """Get or create an agent service for a tenant"""
    if tenant_id not in _agent_services:
        _agent_services[tenant_id] = AgentService(tenant_id=tenant_id)
    return _agent_services[tenant_id]


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    tenant_id: Optional[str] = None  # Optional - will be extracted from auth if not provided
    knowledge_base: Optional[str] = None  # Selected KB from sidebar
    database_connection: Optional[str] = None  # Selected database connection name


class ChatResponse(BaseModel):
    response: str
    session_id: str
    success: bool
    error: Optional[str] = None


class ConversationHistory(BaseModel):
    session_id: str
    messages: List[Dict]


@router.post("/agent/chat", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Chat with the QuickShip AI agent
    
    - **session_id**: Optional session ID (will be generated if not provided)
    - **message**: User message/query
    - **tenant_id**: Optional tenant ID (extracted from auth if not provided)
    - **knowledge_base**: Optional knowledge base name to search (from sidebar selection)
    - **database_connection**: Optional database connection name (from UI database selector)
    """
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Get tenant_id from request or current user
        tenant_id = request.tenant_id or current_user.get("tenant_id")
        
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant ID is required")
        
        logger.info(f"Agent chat request - Tenant: {tenant_id}, Session: {session_id}, Message: {request.message}, KB: {request.knowledge_base}, DB: {request.database_connection}")
        
        # Get tenant-specific agent service
        agent_service = get_agent_service(tenant_id)
        
        # Process message through agent with selected KB and DB
        result = agent_service.chat(
            session_id, 
            request.message, 
            knowledge_base=request.knowledge_base,
            database_connection=request.database_connection
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/history/{session_id}", response_model=ConversationHistory)
async def get_conversation_history(session_id: str):
    """
    Get conversation history for a session
    
    - **session_id**: Session identifier
    """
    try:
        messages = agent_service.get_conversation_history(session_id)
        
        return ConversationHistory(
            session_id=session_id,
            messages=messages
        )
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/reset/{session_id}")
async def reset_conversation(session_id: str):
    """
    Reset conversation history for a session
    
    - **session_id**: Session identifier
    """
    try:
        success = agent_service.reset_conversation(session_id)
        
        return {
            "message": "Conversation reset successfully" if success else "Session not found",
            "success": success
        }
        
    except Exception as e:
        logger.error(f"Error resetting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
