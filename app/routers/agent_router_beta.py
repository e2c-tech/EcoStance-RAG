"""
Beta Agent Router - API endpoints for ReAct agent
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import uuid
import logging

from app.services.agent_service_beta import agent_service

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    knowledge_base: Optional[str] = None  # Selected KB from sidebar


class ChatResponse(BaseModel):
    response: str
    session_id: str
    success: bool
    error: Optional[str] = None


class ConversationHistory(BaseModel):
    session_id: str
    messages: List[Dict]


@router.post("/agent/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    Chat with the QuickShip AI agent
    
    - **session_id**: Optional session ID (will be generated if not provided)
    - **message**: User message/query
    - **knowledge_base**: Optional knowledge base name to search (from sidebar selection)
    """
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        logger.info(f"Agent chat request - Session: {session_id}, Message: {request.message}, KB: {request.knowledge_base}")
        
        # Process message through agent with selected KB
        result = agent_service.chat(session_id, request.message, knowledge_base=request.knowledge_base)
        
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
