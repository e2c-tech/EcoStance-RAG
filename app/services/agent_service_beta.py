"""
ReAct Agent Service for QuickShip Logistics
Handles conversational AI for customer service queries
"""

import re
import logging
from typing import List, Dict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.config import GOOGLE_API_KEY
from app.services.agent_tools import (
    get_shipment_status,
    search_shipments_by_customer,
    track_by_tracking_number,
    get_delivery_estimate,
    check_cod_payment_status,
    get_complaint_status,
    search_knowledge_base,
    list_available_knowledge_bases
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
- search_knowledge_base(collection_name, query): Search company documents for policies, FAQs, procedures

When to use each type:
- Use shipment tools for: "Track QS250001", "Where is my order?", "Check payment", "Delivery estimate"
- Use knowledge base tools for: "What is your policy?", "How do I...?", "Tell me about...", "What are your rates?"
- If unsure which knowledge base to search, first use list_available_knowledge_bases()

IMPORTANT: When a user asks about policies, procedures, rates, or general information (not about a specific shipment),
you MUST use the search_knowledge_base tool. Do not try to answer from memory.

Remember:
- Shipment IDs are in format: QS250XXX
- Tracking numbers are in format: TRKXXXXXXXXX
- Always end with: "Is there anything else I can help you with?"

When you need to use a tool, call it directly and use the result to answer the customer."""


class AgentService:
    """Service for managing agent conversations with tool calling"""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            google_api_key=GOOGLE_API_KEY,
            temperature=0.3
        )
        
        # Bind tools to the model
        self.tools = [
            get_shipment_status,
            search_shipments_by_customer,
            track_by_tracking_number,
            get_delivery_estimate,
            check_cod_payment_status,
            get_complaint_status,
            search_knowledge_base,
            list_available_knowledge_bases
        ]
        
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Store conversations by session_id
        self.conversations: Dict[str, List[Dict]] = {}
    
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
    
    def chat(self, session_id: str, message: str, knowledge_base: str = None) -> Dict:
        """
        Process a chat message and return agent response
        
        Args:
            session_id: Unique session identifier
            message: User message
            knowledge_base: Optional knowledge base name to search (from sidebar)
            
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
            
            # Add user message to history
            self.conversations[session_id].append({
                "role": "user",
                "content": message
            })
            
            # Classify the query type
            query_type = self._classify_query(message)
            logger.info(f"Query classified as: {query_type}")
            
            # For database queries, use tools directly without LLM reformatting
            if query_type == 'database':
                logger.info(f"Direct database tool execution for: {message}")
                
                # Determine which tool to use based on query
                tool_result = None
                
                # Check for shipment ID pattern (QS250XXX)
                if 'qs250' in message.lower():
                    match = re.search(r'QS250\d{3}', message, re.IGNORECASE)
                    if match:
                        shipment_id = match.group(0).upper()
                        from app.services.agent_tools import get_shipment_status
                        tool_result = get_shipment_status.invoke({"shipment_id": shipment_id})
                
                # Check for tracking number pattern (TRKXXXXXXXXX)
                elif 'trk' in message.lower():
                    match = re.search(r'TRK\d+', message, re.IGNORECASE)
                    if match:
                        tracking_number = match.group(0).upper()
                        from app.services.agent_tools import track_by_tracking_number
                        tool_result = track_by_tracking_number.invoke({"tracking_number": tracking_number})
                
                # Check for phone number
                elif 'phone' in message.lower() or re.search(r'\d{10}', message):
                    match = re.search(r'\d{10}', message)
                    if match:
                        phone = match.group(0)
                        from app.services.agent_tools import search_shipments_by_customer
                        tool_result = search_shipments_by_customer.invoke({"phone": phone})
                
                # Check for email
                elif '@' in message:
                    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', message)
                    if match:
                        email = match.group(0)
                        from app.services.agent_tools import search_shipments_by_customer
                        tool_result = search_shipments_by_customer.invoke({"email": email})
                
                # If we got a result, return it directly
                if tool_result:
                    self.conversations[session_id].append({
                        "role": "assistant",
                        "content": tool_result
                    })
                    return {
                        "response": tool_result,
                        "session_id": session_id,
                        "success": True
                    }
                
                # If no tool result, provide helpful prompt for missing information
                else:
                    help_msg = """I'd be happy to help you track your order! To find your shipment, I need one of the following:

📋 **Option 1:** Shipment ID (e.g., QS250001)
📱 **Option 2:** Your phone number (10 digits)
📧 **Option 3:** Your email address
🔍 **Option 4:** Tracking number (e.g., TRK123456789)

**Examples:**
- "Track QS250001"
- "My phone is 9224217802"
- "My email is customer@example.com"
- "Track TRK123456789"

Please provide any of these details and I'll look up your order right away!"""
                    
                    self.conversations[session_id].append({
                        "role": "assistant",
                        "content": help_msg
                    })
                    return {
                        "response": help_msg,
                        "session_id": session_id,
                        "success": True
                    }
            
            # Handle out-of-scope queries
            if query_type == 'out_of_scope':
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
            
            # If it's clearly a KB query and we have a KB, search it directly
            if query_type == 'knowledge_base' and session_id in self.session_kb:
                logger.info(f"Direct KB search for: {message}")
                try:
                    from app.services.agent_tools import search_knowledge_base
                    kb_result = search_knowledge_base.invoke({
                        "collection_name": self.session_kb[session_id],
                        "query": message
                    })
                    
                    # Add agent response to history
                    self.conversations[session_id].append({
                        "role": "assistant",
                        "content": kb_result
                    })
                    
                    return {
                        "response": kb_result,
                        "session_id": session_id,
                        "success": True
                    }
                except Exception as e:
                    logger.error(f"KB search failed: {e}", exc_info=True)
                    error_msg = f"I encountered an error searching the knowledge base: {str(e)}"
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
            
            # Build system prompt with KB context
            kb_context = ""
            if session_id in self.session_kb:
                kb_context = f"\n\nIMPORTANT: When searching the knowledge base, use the collection name: '{self.session_kb[session_id]}'"
            
            # Build messages for the model
            messages = [SystemMessage(content=SYSTEM_PROMPT + kb_context)]
            
            # Add conversation history
            for msg in self.conversations[session_id]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                else:
                    messages.append(AIMessage(content=msg["content"]))
            
            # Get response from model with tools
            logger.info(f"Invoking LLM with {len(messages)} messages")
            response = self.llm_with_tools.invoke(messages)
            
            # Check if model wants to use tools
            if hasattr(response, 'tool_calls') and response.tool_calls:
                logger.info(f"Model requested {len(response.tool_calls)} tool calls")
                # Execute tool calls
                tool_results = []
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get("name")
                    tool_args = tool_call.get("args", {})
                    
                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                    
                    # Find and execute the tool
                    tool_found = False
                    for tool in self.tools:
                        if tool.name == tool_name:
                            tool_found = True
                            try:
                                result = tool.invoke(tool_args)
                                logger.info(f"Tool {tool_name} returned: {result[:100]}...")
                                tool_results.append(f"Tool {tool_name} result: {result}")
                            except Exception as e:
                                logger.error(f"Tool {tool_name} error: {e}", exc_info=True)
                                tool_results.append(f"Tool {tool_name} error: {str(e)}")
                            break
                    
                    if not tool_found:
                        logger.warning(f"Tool {tool_name} not found in available tools")
                
                # Add tool results to messages and get final response
                messages.append(response)
                messages.append(HumanMessage(content="\n\n".join(tool_results)))
                final_response = self.llm.invoke(messages)
                response_text = final_response.content
            else:
                logger.info("No tool calls requested by model")
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                # If response is empty or very short, provide helpful message
                if not response_text or len(response_text.strip()) < 10:
                    if session_id in self.session_kb:
                        response_text = "I'm not sure how to help with that. Try asking about shipment tracking (e.g., 'Track QS250001') or company policies (e.g., 'What are your shipping rates?')."
                    else:
                        response_text = "I'm not sure how to help with that. Try asking about shipment tracking (e.g., 'Track QS250001')."
            
            # Add agent response to history
            self.conversations[session_id].append({
                "role": "assistant",
                "content": response_text
            })
            
            return {
                "response": response_text,
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


# Global agent service instance
agent_service = AgentService()
