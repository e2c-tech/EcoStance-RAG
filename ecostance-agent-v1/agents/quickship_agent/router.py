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
    content: str
    session_id: str
    success: bool
    agent_type: str
    timestamp: str
    tool_used: Optional[str] = None
    error: Optional[str] = None

class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None
    tool_used: Optional[str] = None

class ConversationHistory(BaseModel):
    session_id: str
    messages: List[ConversationMessage]

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
        session_id = request.session_id or str(uuid.uuid4())
        tenant_id = request.tenant_id or current_user.get("tenant_id")
        
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant ID is required")
        
        # Determine agent type
        config = db.query(PublicAgentConfig).filter(PublicAgentConfig.tenant_id == tenant_id).first()
        agent_type = config.agent_type if config else "quickship"
        
        # Get service
        agent_service = get_agent_service(tenant_id, db, request.database_connection)
        
        # --- Persistence Integration ---
        from app.services.public_agent_service import PublicAgentService
        persistence_service = PublicAgentService(db)
        
        # Ensure session exists and get history
        persistence_service.get_or_create_session(session_id, tenant_id)
        db_history = persistence_service.get_session_messages(session_id, tenant_id)
        
        # Format history for the agent service
        # Agent services expect list of {"role": "user/assistant", "content": "..."}
        formatted_history = []
        if db_history:
            for msg in db_history:
                formatted_history.append({"role": msg.role, "content": msg.content})
            
            # Load into agent service memory
            if hasattr(agent_service, 'conversations'):
                agent_service.conversations[session_id] = formatted_history
        
        # Add current user message to DB
        persistence_service.add_message(session_id, tenant_id, "user", request.message)
        
        # Process message via thread pool (chat is synchronous)
        result = await run_in_threadpool(
            agent_service.chat,
            session_id, 
            request.message, 
            knowledge_base=request.knowledge_base,
            database_connection=request.database_connection,
            chat_history=formatted_history
        )
        
        # Add assistant response to DB
        content = result.get("content", "")
        tool_used = result.get("tool_used")
        persistence_service.add_message(session_id, tenant_id, "assistant", content, tool_used=tool_used)
        
        # Update session activity
        persistence_service.update_session_activity(session_id, tenant_id, is_query=True)
        
        from datetime import datetime
        return ChatResponse(
            agent_type=agent_type, 
            timestamp=datetime.utcnow().isoformat(),
            **result
        )
        
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
        from app.services.public_agent_service import PublicAgentService as PersistenceService
        persistence_service = PersistenceService(db)
        
        db_messages = persistence_service.get_session_messages(session_id, tenant_id)
        messages = [
            ConversationMessage(
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp.isoformat() if msg.timestamp else None,
                tool_used=msg.tool_used
            )
            for msg in db_messages
        ]
        
        return ConversationHistory(session_id=session_id, messages=messages)
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class RenameSessionRequest(BaseModel):
    title: str

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

@router.patch("/agent/rename/{session_id}")
async def rename_session(
    session_id: str,
    request: RenameSessionRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rename a conversation session"""
    try:
        tenant_id = current_user.get("tenant_id")
        from app.services.public_agent_service import PublicAgentService
        service = PublicAgentService(db)
        
        success = service.rename_session(session_id, tenant_id, request.title)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found or unauthorized")
            
        return {"message": "Session renamed successfully", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renaming session: {e}")
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

@router.get("/agent/sessions")
async def get_agent_sessions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all agent chat sessions for the current tenant"""
    from app.models.public_agent import PublicAgentSession
    tenant_id = current_user.get("tenant_id")
    
    sessions = db.query(PublicAgentSession).filter(
        PublicAgentSession.tenant_id == tenant_id
    ).order_by(PublicAgentSession.last_activity.desc()).all()
    
    return [s.to_dict() for s in sessions]

@router.delete("/agent/sessions/{session_id}")
async def delete_agent_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an agent chat session and all its messages."""
    try:
        tenant_id = current_user.get("tenant_id")
        from app.services.public_agent_service import PublicAgentService
        service = PublicAgentService(db)
        
        success = service.delete_session(session_id, tenant_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found or unauthorized")
            
        return {"message": "Session deleted successfully", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agent/summary")
async def get_agent_summary(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a summary of agent activity for the tenant"""
    from app.models.public_agent import PublicAgentSession
    tenant_id = current_user.get("tenant_id")
    
    total_sessions = db.query(PublicAgentSession).filter(PublicAgentSession.tenant_id == tenant_id).count()
    
    return {
        "total_sessions": total_sessions,
        "tenant_id": tenant_id
    }
