"""
ReAct Agent Service for QuickShip Logistics
Handles conversational AI for customer service queries
"""

import re
import json
import logging
import time
from typing import List, Dict, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .config import LLM_PROVIDER, AGENT_MODEL, AGENT_TEMPERATURE, GROQ_MODELS, GEMINI_MODELS
from .llm_factory import LLMFactory

# Import LangSmith tracing
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.services.langsmith_service import trace_agent, trace_llm

# Import LangSmith traceable for proper hierarchy
from langsmith import traceable
from .tools.database_tools import (
    get_shipment_status,
    search_shipments_by_customer,
    track_by_tracking_number,
    get_delivery_estimate,
    check_cod_payment_status,
    get_complaint_status,
)
from .tools.knowledge_base_tools import (
    create_search_knowledge_base_tool,
    create_list_knowledge_bases_tool
)

logger = logging.getLogger(__name__)

# System prompt for the agent
SYSTEM_PROMPT = """You are QuickShip's helpful and professional customer service agent.

Your role:
- Help customers track their shipments
- Provide delivery estimates
- Answer questions about payments and complaints
- Always be polite, professional, and empathetic

Guidelines:
1. If customer doesn't provide shipment ID, politely ask for phone number, email, or tracking number
2. If multiple shipments are found, list them clearly and ask which one they want to know about
3. Use the available tools to get accurate information from the database
4. NEVER make up information - only use data returned by the tools
5. If a shipment is delayed or has issues, acknowledge the inconvenience and provide helpful information
6. For complaints, check the complaint status and inform the customer about resolution
7. Be concise but friendly in your responses

Available Tools:

**Shipment & Database Tools:**
- get_shipment_status(shipment_id): Get full details of a shipment by ID (format: QS250XXX)
- search_shipments_by_customer(phone, email): Find shipments by phone or email
- track_by_tracking_number(tracking_number): Track using tracking number (format: TRKXXXXXXXXX)
- get_delivery_estimate(shipment_id): Get delivery date estimates
- check_cod_payment_status(shipment_id): Check COD payment collection status
- get_complaint_status(shipment_id): Check if there are complaints for a shipment

**Knowledge Base Tools:**
- list_available_knowledge_bases(): List all available knowledge bases
- search_knowledge_base(kb_name, query): Search company documents for policies, FAQs, procedures

When to use each type:
- Use shipment tools for: "Track QS250001", "Where is my order?", "Check payment", "Delivery estimate"
- Use knowledge base tools for: "What is your policy?", "How do I...?", "Tell me about...", "What are your rates?"

IMPORTANT: When a user asks about policies, procedures, rates, or general information (not about a specific shipment):
1. FIRST call list_available_knowledge_bases() to see what KBs exist
2. THEN call search_knowledge_base(kb_name, query) with one of the available KB names
3. Do NOT assume KB names - always list them first if you haven't already in this conversation

Remember:
- Shipment IDs are in format: QS250XXX
- Tracking numbers are in format: TRKXXXXXXXXX
- Always end with: "Is there anything else I can help you with?"

When you need to use a tool, call it directly and use the result to answer the customer."""


class AgentService:
    """Service for managing agent conversations with tool calling"""
    
    def __init__(self, tenant_id: str = None, db_session=None, llm_provider: str = None, model: str = None):
        # Create LLM using factory
        try:
            self.llm = LLMFactory.create_llm(
                provider=llm_provider,
                model=model,
                temperature=AGENT_TEMPERATURE
            )
            self.current_provider = llm_provider or LLM_PROVIDER
            self.current_model = model or AGENT_MODEL
            logger.info(f"Initialized AgentService with {self.current_provider} provider, model: {self.current_model}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            # Fallback to Gemini if available
            try:
                self.llm = LLMFactory.create_llm(provider="gemini")
                self.current_provider = "gemini"
                self.current_model = AGENT_MODEL
                logger.warning("Fell back to Gemini provider")
            except Exception as fallback_error:
                logger.error(f"Fallback to Gemini also failed: {fallback_error}")
                raise ValueError("No LLM provider could be initialized. Please check your API keys.")
        
        self.tenant_id = tenant_id
        self.db_session = db_session  # For LLM tracking
        
        # Define available tools
        base_tools = [
            get_shipment_status,
            search_shipments_by_customer,
            track_by_tracking_number,
            get_delivery_estimate,
            check_cod_payment_status,
            get_complaint_status,
        ]
        
        # Add tenant-specific KB tools if tenant_id is provided
        if tenant_id:
            kb_tools = [
                create_search_knowledge_base_tool(tenant_id),
                create_list_knowledge_bases_tool(tenant_id)
            ]
            self.tools = base_tools + kb_tools
        else:
            self.tools = base_tools
        
        # Create a tool map for easy lookup when executing
        self.tool_map = {tool.name: tool for tool in self.tools}
        
        # Store conversations by session_id
        self.conversations: Dict[str, List[Dict]] = {}
    
    def _get_tool_descriptions(self) -> str:
        """Generate tool descriptions for the LLM"""
        descriptions = []
        for tool in self.tools:
            desc = f"- {tool.name}: {tool.description}"
            descriptions.append(desc)
        return "\n".join(descriptions)
    
    def _is_out_of_scope(self, message: str) -> bool:
        """
        Check if query is out of scope (not related to logistics)
        
        Returns: True if out of scope, False if in scope
        """
        message_lower = message.lower()
        
        # Out of scope indicators (programming, general knowledge, etc.)
        out_of_scope_indicators = [
            'write code', 'python code', 'javascript', 'program', 'function',
            'hello world', 'print', 'console.log', 'def ', 'class ',
            'weather', 'news', 'stock', 'recipe', 'movie', 'song',
            'joke', 'story', 'poem', 'translate', 'calculate',
            'what is the capital', 'who is', 'when was', 'history of',
            'math problem', 'solve equation', 'homework'
        ]
        
        return any(indicator in message_lower for indicator in out_of_scope_indicators)
    
    @traceable(name="llm_call")
    def _invoke_llm_with_tracing(self, prompt: str, session_id: str):
        """Invoke LLM with LangSmith tracing"""
        # Add provider-specific tags
        tags = ["llm", self.current_provider]
        return self.llm.invoke([HumanMessage(content=prompt)])
    
    def _classify_query(self, message: str) -> str:
        """
        Classify query type to determine which tool to use
        
        Returns: 'database', 'knowledge_base', 'out_of_scope', or 'unknown'
        """
        message_lower = message.lower()
        
        # Check if out of scope first
        if self._is_out_of_scope(message):
            return 'out_of_scope'
        
        # Database query indicators (shipment tracking)
        db_indicators = [
            'track', 'qs250', 'shipment', 'order', 'delivery boy', 'cod collected',
            'payment status', 'complaint for', 'where is my', 'phone is', 'email is',
            'trk', 'delivered', 'in transit', 'estimate for'
        ]
        
        # Knowledge base query indicators (policies, rates, procedures)
        kb_indicators = [
            'rate', 'cost', 'price', 'how much', 'policy', 'procedure', 
            'how do i', 'what is your', 'what are your', 'tell me about',
            'how long does', 'do you offer', 'what documents', 'why is',
            'how to', 'can you', 'shipping', 'delivery time', 'pickup',
            'international', 'express', 'same-day', 'next-day'
        ]
        
        # Check for database indicators
        if any(indicator in message_lower for indicator in db_indicators):
            return 'database'
        
        # Check for knowledge base indicators
        if any(indicator in message_lower for indicator in kb_indicators):
            return 'knowledge_base'
        
        return 'unknown'
    
    @traceable(name="agent_conversation", tags=["agent", "conversation"])
    def chat(self, session_id: str, message: str, knowledge_base: str = None, database_connection: str = None) -> Dict:
        """
        Process a chat message using ReAct pattern (Reasoning + Acting)
        
        The LLM analyzes the query and decides which tool to call, then we execute it.
        
        Args:
            session_id: Unique session identifier
            message: User message
            knowledge_base: Optional knowledge base name to search (from sidebar)
            database_connection: Optional database connection name (from UI)
            
        Returns:
            Dict with response and metadata
        """
        try:
            # Initialize conversation history if new session
            if session_id not in self.conversations:
                self.conversations[session_id] = []
            
            # Store selected knowledge base for this session
            if not hasattr(self, 'session_kb'):
                self.session_kb = {}
            if knowledge_base:
                self.session_kb[session_id] = knowledge_base
            
            # Store selected database connection for this session
            if not hasattr(self, 'session_db'):
                self.session_db = {}
            if database_connection:
                self.session_db[session_id] = database_connection
            
            # Add user message to history
            self.conversations[session_id].append({
                "role": "user",
                "content": message
            })
            
            # Check if query is out of scope first
            if self._is_out_of_scope(message):
                out_of_scope_msg = """I'm sorry, but I can't help with that. I'm a QuickShip logistics assistant specialized in:

📦 **Shipment Tracking:**
- Track shipments by ID (e.g., "Track QS250001")
- Check delivery status and estimates
- View payment and COD status
- Check complaints

📚 **Company Information:**
- Shipping rates and costs
- Delivery timelines
- Pickup services
- Policies and procedures

**Try asking:**
- "What are your shipping rates?"
- "Track QS250001"
- "How long does delivery take?"
- "My phone is 9224217802, show my orders"

Is there anything related to shipments or logistics I can help you with?"""
                
                self.conversations[session_id].append({
                    "role": "assistant",
                    "content": out_of_scope_msg
                })
                
                return {
                    "response": out_of_scope_msg,
                    "session_id": session_id,
                    "success": True
                }
            
            # Build context about selected KB and DB
            context_info = ""
            if session_id in self.session_kb:
                context_info += f"\n\nIMPORTANT: User has selected knowledge base '{self.session_kb[session_id]}'. If you need to search knowledge base, you MUST use kb_name='{self.session_kb[session_id]}'."
            if session_id in self.session_db:
                context_info += f"\n\nDatabase connection: {self.session_db[session_id]}"
            
            # Use LLM to analyze query and decide which tool to use
            analysis_prompt = f"""Analyze this customer query and determine which tool to use.

Query: "{message}"{context_info}

Available tools:
{self._get_tool_descriptions()}

Respond with ONLY a JSON object in this format:
{{
    "tool": "tool_name",
    "args": {{"arg1": "value1", "arg2": "value2"}},
    "reasoning": "why this tool"
}}

If no tool is needed (greeting, clarification, etc.), respond with:
{{
    "tool": "none",
    "response": "your direct response"
}}

Examples:
- "Track QS250001" → {{"tool": "get_shipment_status", "args": {{"shipment_id": "QS250001"}}}}
- "My phone is 9224217802" → {{"tool": "search_shipments_by_customer", "args": {{"phone": "9224217802"}}}}
- "What are your rates?" → {{"tool": "search_knowledge_base", "args": {{"kb_name": "policies", "query": "shipping rates"}}}}
- "Hello" → {{"tool": "none", "response": "Hi! How can I help you today?"}}"""
            
            logger.info(f"Asking LLM to analyze query: {message}")
            
            # Track LLM call if db_session is available
            start_time = time.time()
            analysis_response = self._invoke_llm_with_tracing(analysis_prompt, session_id)
            latency_ms = int((time.time() - start_time) * 1000)
            
            analysis_text = analysis_response.content if hasattr(analysis_response, 'content') else str(analysis_response)
            
            # Track usage if we have db_session and tenant_id
            if self.db_session and self.tenant_id:
                try:
                    from app.services.llm_tracking_service import LLMTrackingService
                    
                    # Estimate tokens (rough approximation: 1 token ≈ 4 chars)
                    input_tokens = len(analysis_prompt) // 4
                    output_tokens = len(analysis_text) // 4
                    
                    LLMTrackingService.track_llm_call(
                        db=self.db_session,
                        tenant_id=str(self.tenant_id),
                        model=AGENT_MODEL,
                        operation_type='agent',
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        success=True,
                        latency_ms=latency_ms,
                        endpoint='/api/v1/beta/agent/chat',
                        session_id=session_id
                    )
                except Exception as e:
                    logger.warning(f"Failed to track LLM usage: {e}")
            
            logger.info(f"LLM analysis: {analysis_text}")
            
            # Parse the LLM's decision
            try:
                # Extract JSON from response (handle markdown code blocks)
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', analysis_text, re.DOTALL)
                if json_match:
                    analysis_text = json_match.group(1)
                else:
                    # Try to find JSON without code blocks
                    json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
                    if json_match:
                        analysis_text = json_match.group(0)
                
                decision = json.loads(analysis_text)
                tool_name = decision.get('tool')
                
                # If no tool needed, return direct response
                if tool_name == 'none':
                    response_text = decision.get('response', "I'm here to help! What would you like to know?")
                    
                    self.conversations[session_id].append({
                        "role": "assistant",
                        "content": response_text
                    })
                    
                    return {
                        "response": response_text,
                        "session_id": session_id,
                        "success": True
                    }
                
                # Execute the tool
                if tool_name in self.tool_map:
                    tool = self.tool_map[tool_name]
                    tool_args = decision.get('args', {})
                    
                    # If it's a KB search and we have a selected KB, use it
                    if tool_name == 'search_knowledge_base':
                        # Use UI-selected KB if available
                        ui_selected_kb = self.session_kb.get(session_id)
                        
                        if ui_selected_kb:
                            tool_args['collection_name'] = ui_selected_kb
                        elif 'collection_name' not in tool_args:
                            # No KB selected, ask user to select one
                            kb_msg = "To search our knowledge base, please select a knowledge base from the sidebar first."
                            self.conversations[session_id].append({
                                "role": "assistant",
                                "content": kb_msg
                            })
                            return {
                                "response": kb_msg,
                                "session_id": session_id,
                                "success": True
                            }
                        # LLM hallucinated a collection name but none is selected in UI
                        elif not ui_selected_kb:
                            kb_msg = "To search our knowledge base, please select a knowledge base from the sidebar first."
                            self.conversations[session_id].append({"role": "assistant", "content": kb_msg})
                            return {"response": kb_msg, "session_id": session_id, "success": True}
                    
                    # If it's a database tool, check if DB is connected
                    db_tools = ['get_shipment_status', 'search_shipments_by_customer', 
                               'track_by_tracking_number', 'get_delivery_estimate',
                               'check_cod_payment_status', 'get_complaint_status']
                    
                    if tool_name in db_tools:
                        if not hasattr(self, 'session_db') or session_id not in self.session_db:
                            # No DB connected, inform user
                            db_msg = """To query shipment data, please connect to a database first.

Click on the **Database** dropdown in the sidebar and select a database connection (e.g., "logistics-demo").

Once connected, I'll be able to:
- Track shipments by ID
- Search by phone/email
- Check delivery status
- View payment information"""
                            
                            self.conversations[session_id].append({
                                "role": "assistant",
                                "content": db_msg
                            })
                            return {
                                "response": db_msg,
                                "session_id": session_id,
                                "success": True
                            }
                    
                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                    
                    try:
                        result = tool.invoke(tool_args)
                        logger.info(f"Tool returned: {result[:100]}...")
                        
                        self.conversations[session_id].append({
                            "role": "assistant",
                            "content": result
                        })
                        
                        return {
                            "response": result,
                            "session_id": session_id,
                            "success": True
                        }
                    except Exception as e:
                        error_msg = f"Error executing tool: {str(e)}"
                        logger.error(error_msg, exc_info=True)
                        
                        self.conversations[session_id].append({
                            "role": "assistant",
                            "content": error_msg
                        })
                        
                        return {
                            "response": error_msg,
                            "session_id": session_id,
                            "success": False,
                            "error": str(e)
                        }
                else:
                    error_msg = f"Tool '{tool_name}' not found"
                    logger.warning(error_msg)
                    
                    self.conversations[session_id].append({
                        "role": "assistant",
                        "content": error_msg
                    })
                    
                    return {
                        "response": error_msg,
                        "session_id": session_id,
                        "success": False
                    }
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM decision: {e}")
                logger.error(f"LLM response was: {analysis_text}")
                
                # Fallback: use the LLM's response directly
                fallback_msg = "I'm not sure how to help with that. Could you please rephrase your question?"
                
                self.conversations[session_id].append({
                    "role": "assistant",
                    "content": fallback_msg
                })
                
                return {
                    "response": fallback_msg,
                    "session_id": session_id,
                    "success": True
                }
            
        except Exception as e:
            logger.error(f"Error in agent chat: {e}", exc_info=True)
            error_response = "I apologize, but I encountered an error. Please try again or contact support."
            
            self.conversations[session_id].append({
                "role": "assistant",
                "content": error_response
            })
            
            return {
                "response": error_response,
                "session_id": session_id,
                "success": False,
                "error": str(e)
            }
    
    def get_conversation_history(self, session_id: str) -> List[Dict]:
        """Get conversation history for a session"""
        return self.conversations.get(session_id, [])
    
    def reset_conversation(self, session_id: str) -> bool:
        """Reset conversation history for a session"""
        if session_id in self.conversations:
            del self.conversations[session_id]
            return True
        return False
    
    def switch_llm_provider(self, provider: str, model: str = None) -> Dict:
        """
        Switch to a different LLM provider
        
        Args:
            provider: New provider ('gemini' or 'groq')
            model: Optional model name. If not provided, uses default for provider
            
        Returns:
            Dict with success status and message
        """
        try:
            # Validate provider configuration
            is_valid, error_msg = LLMFactory.validate_provider_config(provider)
            if not is_valid:
                return {
                    "success": False,
                    "message": f"Cannot switch to {provider}: {error_msg}"
                }
            
            # Create new LLM instance
            old_provider = self.current_provider
            old_model = self.current_model
            
            self.llm = LLMFactory.create_llm(
                provider=provider,
                model=model,
                temperature=AGENT_TEMPERATURE
            )
            
            self.current_provider = provider
            self.current_model = model or (GROQ_MODELS[0] if provider == "groq" else AGENT_MODEL)
            
            logger.info(f"Switched LLM from {old_provider}:{old_model} to {self.current_provider}:{self.current_model}")
            
            return {
                "success": True,
                "message": f"Successfully switched to {self.current_provider} with model {self.current_model}",
                "previous_provider": old_provider,
                "previous_model": old_model,
                "current_provider": self.current_provider,
                "current_model": self.current_model
            }
            
        except Exception as e:
            logger.error(f"Failed to switch LLM provider: {e}")
            return {
                "success": False,
                "message": f"Failed to switch to {provider}: {str(e)}"
            }
    
    def get_current_llm_info(self) -> Dict:
        """Get information about the current LLM configuration"""
        return {
            "provider": self.current_provider,
            "model": self.current_model,
            "temperature": AGENT_TEMPERATURE,
            "available_providers": LLMFactory.get_available_providers()
        }

