"""
FastAPI Router for QuickShip AI Agent
Provides REST API endpoints for the agent
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import uuid
import logging

from app.services.multilingual_integration_service import get_multilingual_integration_service
from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.models.public_agent import PublicAgentConfig
from fastapi.concurrency import run_in_threadpool

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Schemas ---

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    tenant_id: Optional[str] = None
    knowledge_base: Optional[str] = None
    database_connection: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    success: bool
    agent_type: str
    error: Optional[str] = None


class ConversationHistory(BaseModel):
    session_id: str
    messages: List[Dict]

# --- Service Factory ---

def get_agent_service(tenant_id: str, db: Session, database_connection: str = None):
    """Factory to create the assigned agent service for a tenant"""
    config = db.query(PublicAgentConfig).filter(PublicAgentConfig.tenant_id == tenant_id).first()
    agent_type = config.agent_type if config else "quickship"
    
    logger.debug(f"Tenant {tenant_id} initializing agent type: {agent_type}")
    
    if agent_type == "quickship":
        from .multilingual_agent_service import MultilingualAgentService
        return MultilingualAgentService(tenant_id=tenant_id, db_session=db)
    elif agent_type == "ecommerce":
        from agents.ecommerce_agent.service import EcommerceAgentService
        return EcommerceAgentService(tenant_id=tenant_id)
    elif agent_type == "ecostance":
        from agents.ecostance_agent.service import EcoStanceAgentService
        return EcoStanceAgentService(tenant_id=tenant_id)
    elif agent_type == "security_analyst":
        from agents.security_analyst.service import SecurityAnalystService
        return SecurityAnalystService(tenant_id=tenant_id, database_connection=database_connection)
    else:
        from agents.generic_agent.service import GenericAgentService
        return GenericAgentService(tenant_id=tenant_id)

# --- Endpoints ---

@router.post("/agent/chat", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Chat with the assigned AI agent for the tenant"""
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Get tenant_id from request or current user
        tenant_id = request.tenant_id or current_user.get("tenant_id")
        
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant ID is required")
        
        # Determine agent type
        config = db.query(PublicAgentConfig).filter(PublicAgentConfig.tenant_id == tenant_id).first()
        agent_type = config.agent_type if config else "quickship"
        
        # Get service
        agent_service = get_agent_service(tenant_id, db, request.database_connection)
        
        # Process message via thread pool (chat is synchronous)
        result = await run_in_threadpool(
            agent_service.chat,
            session_id, 
            request.message, 
            knowledge_base=request.knowledge_base,
            database_connection=request.database_connection
        )
        
        return ChatResponse(agent_type=agent_type, **result)
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/history/{session_id}", response_model=ConversationHistory)
async def get_conversation_history(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get conversation history for a session"""
    try:
        tenant_id = current_user.get("tenant_id")
        agent_service = get_agent_service(tenant_id, db)
        messages = agent_service.get_conversation_history(session_id)
        return ConversationHistory(session_id=session_id, messages=messages)
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/reset/{session_id}")
async def reset_conversation(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reset conversation history for a session"""
    try:
        tenant_id = current_user.get("tenant_id")
        agent_service = get_agent_service(tenant_id, db)
        success = agent_service.reset_conversation(session_id)
        
        return {
            "message": "Conversation reset successfully" if success else "Session not found",
            "success": success
        }
        
    except Exception as e:
        logger.error(f"Error resetting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agent/config")
async def get_agent_config(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current tenant's assigned agent configuration"""
    tenant_id = current_user.get("tenant_id")
    config = db.query(PublicAgentConfig).filter(PublicAgentConfig.tenant_id == tenant_id).first()
    agent_type = config.agent_type if config else "quickship"
    
    return {
        "tenant_id": tenant_id,
        "agent_type": agent_type,
        "is_customized": config is not None
    }
