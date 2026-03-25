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

# Per-tenant agent service cache to avoid re-initializing heavy models per request
_agent_service_cache: Dict[str, object] = {}


def _sanitize_agent_content(raw: str) -> str:
    """
    THE GATEKEEPER: Extract only the clean, human-readable final answer.
    Strips all intermediate tool calls, JSON artifacts, database schemas,
    and scratchpad text. Only the answer passes through.
    """
    import json
    import re
    
    if not raw or not isinstance(raw, str):
        return raw or ""
    
    text = raw.strip()
    
    # --- Step 1: Try to extract response from JSON blocks ---
    # Use bracket counting to find all top-level JSON objects
    blocks = []
    brace_count = 0
    start_pos = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if brace_count == 0:
                start_pos = i
            brace_count += 1
        elif ch == '}':
            brace_count -= 1
            if brace_count == 0 and start_pos != -1:
                blocks.append(text[start_pos:i+1])
    
    final_answer = None
    has_tool_call = False
    
    # Check blocks in reverse (last block is usually the final answer)
    for block in reversed(blocks):
        parsed = None
        
        # Try parsing
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError:
            # LLM put literal newlines in string values — try sanitizing
            try:
                sanitized = block.replace('\n', '\\n').replace('\r', '\\r')
                parsed = json.loads(sanitized)
            except:
                pass
            
            # Regex fallback: extract "response" field directly
            if not parsed and '"response"' in block:
                resp_match = re.search(r'"response"\s*:\s*"([\s\S]*?)"\s*[,\n}]', block)
                if resp_match:
                    candidate = resp_match.group(1).replace('\\n', '\n').strip()
                    if candidate:
                        final_answer = candidate
                        break
        
        if parsed and isinstance(parsed, dict):
            tool = parsed.get('tool', '')
            
            # Final answer: tool is "none" 
            if tool == 'none' and parsed.get('response'):
                final_answer = parsed['response']
                break
            
            # Intermediate tool call: skip it
            if tool and tool != 'none':
                has_tool_call = True
                continue
            
            # Object with a response/answer field
            if parsed.get('response'):
                final_answer = parsed['response']
                break
            if parsed.get('answer'):
                final_answer = parsed['answer']
                break
    
    if final_answer:
        return final_answer.strip()
    
    # --- Step 2: No JSON answer found. If there were tool calls, strip all artifacts ---
    if has_tool_call or blocks:
        cleaned = text
        # Remove all JSON blocks
        for block in blocks:
            cleaned = cleaned.replace(block, '')
        
        # Remove scratchpad artifacts
        scratchpad_patterns = [
            r'\*\*Database Schema:\*\*[\s\S]*?(?=\n\n|\*\*|$)',
            r'\*\*Database Tables:\*\*[\s\S]*?(?=\n\n|\*\*|$)',
            r'\*\*Database Columns:\*\*[\s\S]*?(?=\n\n|\*\*|$)',
            r'\*\*Database Query Results:\*\*[\s\S]*?(?=\n\n|\*\*|$)',
            r'\*\*Database Results:\*\*[\s\S]*?(?=\n\n|\*\*|$)',
            r'TOOL_RESULT\s*\([^)]*\):\s*[\s\S]*?(?=\n\n|$)',
            r'list_database_tables',
            r'Final Answer:\*?\s*',
            r'```json\s*[\s\S]*?```',
            r'```\s*[\s\S]*?```',
        ]
        for pattern in scratchpad_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        cleaned = cleaned.strip()
        if len(cleaned) > 20:
            return cleaned
    
    # --- Step 3: Plain text — just return as is ---
    # Remove code fences if present
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    return text.strip()

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
    """Factory to create the assigned agent service for a tenant, cached per tenant."""
    config = db.query(PublicAgentConfig).filter(PublicAgentConfig.tenant_id == tenant_id).first()
    agent_type = config.agent_type if config else "quickship"

    cache_key = f"{tenant_id}:{agent_type}"
    if cache_key in _agent_service_cache:
        return _agent_service_cache[cache_key]

    logger.debug(f"Tenant {tenant_id} initializing agent type: {agent_type}")

    if agent_type == "quickship":
        from .multilingual_agent_service import MultilingualAgentService
        service = MultilingualAgentService(tenant_id=tenant_id, db_session=db)
    elif agent_type == "ecommerce":
        from agents.ecommerce_agent.service import EcommerceAgentService
        service = EcommerceAgentService(tenant_id=tenant_id)
    elif agent_type == "ecostance":
        from agents.ecostance_agent.service import EcoStanceAgentService
        service = EcoStanceAgentService(tenant_id=tenant_id)
    elif agent_type == "security_analyst":
        from agents.security_analyst.service import SecurityAnalystService
        service = SecurityAnalystService(tenant_id=tenant_id, database_connection=database_connection)
    else:
        from agents.generic_agent.service import GenericAgentService
        service = GenericAgentService(tenant_id=tenant_id)

    _agent_service_cache[cache_key] = service
    return service

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
                # MultilingualAgentService expects {"messages": [], "language": "en"}
                # EcommerceAgentService and others expect a flat list
                from agents.quickship_agent.multilingual_agent_service import MultilingualAgentService
                if isinstance(agent_service, MultilingualAgentService):
                    agent_service.conversations[session_id] = {
                        "messages": formatted_history,
                        "language": "en"
                    }
                else:
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
        
        # Sanitize: extract only the clean final answer, strip all thinking/JSON/scratchpad
        raw_content = result.get("content", result.get("response", ""))
        content = _sanitize_agent_content(raw_content)
        
        tool_used = result.get("tool_used")
        persistence_service.add_message(session_id, tenant_id, "assistant", content, tool_used=tool_used)
        
        # Update session activity
        persistence_service.update_session_activity(session_id, tenant_id, is_query=True)
        
        from datetime import datetime
        
        return ChatResponse(
            agent_type=agent_type, 
            timestamp=datetime.utcnow().isoformat(),
            content=content,
            session_id=session_id,
            success=result.get("success", True),
            tool_used=tool_used,
            error=result.get("error"),
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
