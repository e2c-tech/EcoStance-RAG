"""
Public Agent Service - Restricted version of agent service for customer-facing use.
Only allows specific tool categories based on admin configuration.
"""

import re
import json
import logging
from typing import List, Dict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from .config import GOOGLE_API_KEY, AGENT_MODEL, AGENT_TEMPERATURE
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

# Tool category mapping
TOOL_CATEGORIES = {
    "tracking": [get_shipment_status, track_by_tracking_number],
    "customer_search": [search_shipments_by_customer],
    "delivery_estimates": [get_delivery_estimate],
    "payments": [check_cod_payment_status],
    "complaints": [get_complaint_status]
}

# System prompt for public agent
PUBLIC_SYSTEM_PROMPT = """You are a helpful customer service agent.

Your role:
- Help customers track their shipments
- Provide delivery information
- Answer questions about payments
- Check complaint status
- Always be polite, professional, and empathetic

Guidelines:
1. If customer doesn't provide shipment ID, politely ask for phone number, email, or tracking number
2. If multiple shipments are found, list them clearly and ask which one they want to know about
3. Use the available tools to get accurate information from the database
4. NEVER make up information - only use data returned by the tools
5. If a shipment is delayed or has issues, acknowledge the inconvenience and provide helpful information
6. Be concise but friendly in your responses

Available Tools:
{tool_descriptions}

Remember:
- Shipment IDs are in format: QS250XXX
- Tracking numbers are in format: TRKXXXXXXXXX
- Always end with: "Is there anything else I can help you with?"

When you need to use a tool, call it directly and use the result to answer the customer."""


class PublicAgentService:
    """Service for managing public agent conversations with restricted tool access"""
    
    def __init__(self, tenant_id: str = None, allowed_tools: List[str] = None):
        self.llm = ChatGoogleGenerativeAI(
            model=AGENT_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=AGENT_TEMPERATURE
        )
        
        self.tenant_id = tenant_id
        self.allowed_tools = allowed_tools if allowed_tools is not None else ["tracking", "payments", "complaints", "delivery_estimates"]
        
        # Build tool list based on allowed categories
        self.tools = self._build_tool_list()
        
        # Create a tool map for easy lookup
        self.tool_map = {tool.name: tool for tool in self.tools}
        
        # Store conversations by session_id
        self.conversations: Dict[str, List[Dict]] = {}
    
    def _build_tool_list(self) -> List:
        """Build list of tools based on allowed categories"""
        tools = []
        
        # Add database tools based on allowed categories
        for category in self.allowed_tools:
            if category in TOOL_CATEGORIES:
                tools.extend(TOOL_CATEGORIES[category])
        
        # Add KB tools if tenant_id is provided (KB tools are always available if tenant exists)
        if self.tenant_id:
            kb_tools = [
                create_search_knowledge_base_tool(self.tenant_id),
                create_list_knowledge_bases_tool(self.tenant_id)
            ]
            tools.extend(kb_tools)
        
        logger.info(f"Built tool list with {len(tools)} tools for categories: {self.allowed_tools}")
        logger.info(f"Tool names: {[t.name for t in tools]}")
        return tools
    
    def _get_tool_descriptions(self) -> str:
        """Generate tool descriptions for the LLM"""
        descriptions = []
        for tool in self.tools:
            desc = f"- {tool.name}: {tool.description}"
            descriptions.append(desc)
        return "\n".join(descriptions)
    
    def _is_out_of_scope(self, message: str) -> bool:
        """Check if query is out of scope"""
        message_lower = message.lower()
        
        out_of_scope_indicators = [
            'write code', 'python code', 'javascript', 'program', 'function',
            'hello world', 'print', 'console.log', 'def ', 'class ',
            'weather', 'news', 'stock', 'recipe', 'movie', 'song',
            'joke', 'story', 'poem', 'translate', 'calculate',
            'what is the capital', 'who is', 'when was', 'history of',
            'math problem', 'solve equation', 'homework'
        ]
        
        return any(indicator in message_lower for indicator in out_of_scope_indicators)
    
    def chat(self, session_id: str, message: str, knowledge_base: str = None, database_connection: str = None) -> Dict:
        """
        Process a chat message using ReAct pattern with restricted tools
        
        Args:
            session_id: Unique session identifier
            message: User message
            knowledge_base: Optional knowledge base name
            database_connection: Optional database connection name
            
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
            
            # Check if query is out of scope
            if self._is_out_of_scope(message):
                out_of_scope_msg = """I'm sorry, but I can't help with that. I'm a customer service assistant specialized in:

📦 **Shipment Tracking:**
- Track shipments by ID (e.g., "Track QS250001")
- Check delivery status and estimates
- View payment and COD status
- Check complaints

**Try asking:**
- "Track QS250001"
- "Where is my order?"
- "My phone is 9224217802, show my orders"
- "Check payment status for QS250001"

Is there anything related to shipments I can help you with?"""
                
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
            tool_descriptions = self._get_tool_descriptions()
            system_prompt = PUBLIC_SYSTEM_PROMPT.format(tool_descriptions=tool_descriptions)
            
            analysis_prompt = f"""{system_prompt}

Query: "{message}"{context_info}

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
- "Hello" → {{"tool": "none", "response": "Hi! How can I help you today?"}}"""
            
            logger.info(f"Asking LLM to analyze query: {message}")
            analysis_response = self.llm.invoke([HumanMessage(content=analysis_prompt)])
            analysis_text = analysis_response.content if hasattr(analysis_response, 'content') else str(analysis_response)
            
            logger.info(f"LLM analysis: {analysis_text}")
            
            # Parse the LLM's decision
            try:
                # Extract JSON from response
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', analysis_text, re.DOTALL)
                if json_match:
                    analysis_text = json_match.group(1)
                else:
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
                
                # Check if tool is allowed
                if tool_name not in self.tool_map:
                    error_msg = f"I'm sorry, but I don't have access to that information. I can help you with: {', '.join([t.name for t in self.tools])}"
                    logger.warning(f"Tool '{tool_name}' not in allowed tools")
                    
                    self.conversations[session_id].append({
                        "role": "assistant",
                        "content": error_msg
                    })
                    
                    return {
                        "response": error_msg,
                        "session_id": session_id,
                        "success": False
                    }
                
                # Execute the tool
                tool = self.tool_map[tool_name]
                tool_args = decision.get('args', {})
                
                # Handle KB search
                if tool_name == 'search_knowledge_base':
                    if session_id in self.session_kb:
                        tool_args['collection_name'] = self.session_kb[session_id]
                    elif 'collection_name' not in tool_args:
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
                
                # Check if DB is connected for database tools
                db_tools = ['get_shipment_status', 'search_shipments_by_customer', 
                           'track_by_tracking_number', 'get_delivery_estimate',
                           'check_cod_payment_status', 'get_complaint_status']
                
                if tool_name in db_tools:
                    if not hasattr(self, 'session_db') or session_id not in self.session_db:
                        db_msg = """To query shipment data, please connect to a database first.

Click on the **Database** dropdown in the sidebar and select a database connection.

Once connected, I'll be able to help you track shipments and check delivery status."""
                        
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
                        "success": True,
                        "tool_used": tool_name
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
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM decision: {e}")
                logger.error(f"LLM response was: {analysis_text}")
                
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
            logger.error(f"Error in public agent chat: {e}", exc_info=True)
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
