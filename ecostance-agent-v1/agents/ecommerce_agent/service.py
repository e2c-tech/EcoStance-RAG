"""
E-Commerce Agent Service
Handles the specific logic for the E-Commerce Bot.
"""
import logging
import json
import re
from typing import List, Dict, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from .config import AGENT_MODEL, GOOGLE_API_KEY, GROQ_API_KEY, LLM_PROVIDER, AGENT_TEMPERATURE
from .tools.product_tools import find_products, get_all_categories, get_my_orders
from agents.generic_agent.tools.kb_tools import create_search_knowledge_base_tool, create_list_knowledge_bases_tool
from agents.generic_agent.tools.db_tools import create_db_query_tool, create_list_db_tables_tool

from app.services.multilingual_utils import MultilingualAgentMixin

logger = logging.getLogger(__name__)

_ECOMMERCE_EN_PROMPT = """You are the E-Commerce Shopping Assistant.
Your goal is to help customers find products, check their orders, and answer questions about the product catalog.
Respond in the same language as the customer's question.

### RESPONSE FORMAT RULES
1. **Normal Chat**: If you are just talking, greeting, or explaining, answer normally.
2. **Data Found**: If you use a tool and get results, provide a helpful human-friendly summary.
3. **Links/Actions**: If the user needs a specific page (like login), return:
   {"type": "url_action", "message": "Please log in first", "data": {"url": "/login", "button_text": "Log In"}}

### AVAILABLE TOOLS:
1. `list_database_tables()`: CALL THIS FIRST to see the database schema before writing SQL.
2. `query_database(query)`: Run SQL queries against the connected database.
3. `find_products(search, category_slug)`: Search products via API (if no DB connected).
4. `get_all_categories()`: Get product categories via API (if no DB connected).
5. `get_my_orders(user_id)`: Get order history via API (if no DB connected).
6. `search_knowledge_base(kb_name, query)`: Search company documents/FAQs.
7. `list_available_knowledge_bases()`: List available knowledge bases.

### CRITICAL RULES:
- If a database is connected, ALWAYS use `list_database_tables` then IMMEDIATELY `query_database` to answer the question. Do NOT stop after listing tables — use the schema to write and run the SQL query.
- NEVER guess column names — always check schema first.
- NEVER make up data — only use what tools return.
- NEVER just describe the schema to the user — always proceed to answer their question with a query.
"""

ECOMMERCE_SYSTEM_PROMPTS = {"en": _ECOMMERCE_EN_PROMPT}

# Strict whitelist of allowed tools for E-Commerce agent
SAFE_TOOL_WHITELIST = {"product_search", "categories", "orders", "knowledge_base", "database_query"}

class EcommerceAgentService(MultilingualAgentMixin):
    def __init__(self, tenant_id: str = None, allowed_tools: List[str] = None, **kwargs):
        # Initialize Mixin for multilingual support
        super().__init__(system_prompts=ECOMMERCE_SYSTEM_PROMPTS)
        
        if LLM_PROVIDER == "groq":
            self.llm = ChatGroq(
                model=AGENT_MODEL,
                groq_api_key=GROQ_API_KEY,
                temperature=AGENT_TEMPERATURE
            )
        else:
            self.llm = ChatGoogleGenerativeAI(
                model=AGENT_MODEL,
                google_api_key=GOOGLE_API_KEY,
                temperature=AGENT_TEMPERATURE
            )
        self.tenant_id = tenant_id
        
        # Validate allowed tools
        requested_tools = allowed_tools if allowed_tools is not None else ["product_search", "categories", "orders"]
        self.allowed_tools = [t for t in requested_tools if t in SAFE_TOOL_WHITELIST]
        
        if not self.allowed_tools:
            logger.warning(f"No safe tools found for Ecommerce agent in: {requested_tools}. Using all safe tools.")
            self.allowed_tools = list(SAFE_TOOL_WHITELIST)

        # Map tools to internal objects with safety check
        self.tools = []
        if "product_search" in self.allowed_tools:
            self.tools.append(find_products)
        if "categories" in self.allowed_tools:
            self.tools.append(get_all_categories)
        if "orders" in self.allowed_tools:
            self.tools.append(get_my_orders)

        # Always add generic DB tools — they use the global connector set by /db/connect
        self.tools.append(create_list_db_tables_tool(tenant_id=tenant_id))
        self.tools.append(create_db_query_tool(tenant_id=tenant_id))
        # KB tools scoped to tenant
        self.tools.append(create_search_knowledge_base_tool(tenant_id))
        self.tools.append(create_list_knowledge_bases_tool(tenant_id))
            
        self.tool_map = {tool.name: tool for tool in self.tools}
        
        # In-memory conversation storage
        self.conversations: Dict[str, List[Dict]] = {}
        
    def _is_out_of_scope(self, message: str) -> bool:
        """Simple keyword check for clearly out-of-scope queries."""
        return False

    def reset_conversation(self, session_id: str) -> bool:
        """Reset conversation history for a session."""
        if session_id in self.conversations:
            self.conversations[session_id] = []
            return True
        return False

    def chat(self, session_id: str, message: str, knowledge_base: str = None, database_connection: str = None, user_id: str = None, user_language: str = None, chat_history: List[Dict] = None, **kwargs) -> Dict:
        """
        Process a chat message using ReAct pattern with multilingual support
        """
        try:
            # Language Detection
            detected_lang, preferred_lang, confidence = self.get_language_context(
                message, session_id, user_language
            )

            # Initialize conversation history if new session
            if session_id not in self.conversations:
                self.conversations[session_id] = []
                if chat_history:
                    for msg in chat_history:
                        if msg.get("role") in ["user", "assistant"]:
                            self.conversations[session_id].append(msg)
            
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
            
            # Get language-specific system prompt
            system_prompt = self.get_system_prompt(preferred_lang)
            
            # Construct Prompt
            tool_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])

            context_info = f"\nUser ID: {user_id if user_id else 'Not Logged In'}\nDetected Language: {detected_lang}\nPreferred Response Language: {preferred_lang}"
            if session_id in self.session_kb:
                 context_info += f"\nActive Knowledge Base: {self.session_kb[session_id]}"
            if session_id in self.session_db:
                 context_info += f"\nActive Database: {self.session_db[session_id]}"

            max_iterations = 4
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                is_last_turn = (iteration == max_iterations)
                
                # Build message history for reasoning
                from langchain_core.messages import SystemMessage, AIMessage
                lc_messages = [SystemMessage(content=f"""{system_prompt}

### SELECTION STRICTNESS RULES:
1. **DATABASE ONLY**: If the user has a Database selected, PRIORITIZE using database tools for quantitative queries.
2. **KB ONLY**: If the user has a Knowledge Base selected but NO Database, use KB.
3. **NOT SELECTED**: If a tool requires a Knowledge Base or Database that is NOT currently selected in the context, DO NOT use that tool. Instead, explain that the source is not selected.

### AVAILABLE TOOLS:
{tool_descriptions}

### ACTIVE CONTEXT:
{context_info}

### INSTRUCTIONS:
- You MUST respond with exactly one JSON object.
- If you just got a TOOL_RESULT from `list_database_tables`, you MUST immediately call `query_database` with the correct SQL to answer the user's question. DO NOT stop and describe the schema.
- If you have query results, ANALYZE THEM and provide a human-friendly answer.
- NEVER tell the user what the schema looks like — just use it to answer their question.

FORMAT:
{{
    "tool": "tool_name",
    "args": {{...}},
    "reasoning": "why this tool"
}}
OR (if finished):
{{
    "tool": "none",
    "response": {{
        "type": "text",
        "message": "Your helpful analysis or answer here",
        "data": null
    }}
}}
""")]
                
                # Add history
                for msg in self.conversations[session_id][-6:]:
                    if msg["role"] == "user":
                        lc_messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        lc_messages.append(AIMessage(content=msg["content"]))
                    elif msg["role"] == "system":
                        lc_messages.append(SystemMessage(content=msg["content"]))

                # Ask LLM
                result = self.llm.invoke(lc_messages)
                text = result.content
                
                # Robust JSON extraction
                match = re.search(r'\{.*\}', text, re.DOTALL)
                decision = None
                if match:
                    try:
                        decision = json.loads(match.group(0))
                    except:
                        # Try first block if greedy fails
                        match_first = re.search(r'\{.*?\}', text, re.DOTALL)
                        if match_first:
                            try: decision = json.loads(match_first.group(0))
                            except: pass

                if not decision:
                    self.conversations[session_id].append({"role": "assistant", "content": text})
                    return {"response": text, "session_id": session_id, "success": True}

                tool_name = decision.get('tool')
                
                if tool_name == 'none' or not tool_name or is_last_turn:
                    final_response = decision.get('response', text)
                    if isinstance(final_response, dict):
                        content = final_response.get('message', str(final_response))
                    else:
                        content = str(final_response)
                        
                    self.conversations[session_id].append({"role": "assistant", "content": content})
                    return {
                        "response": content,
                        "session_id": session_id,
                        "language": preferred_lang,
                        "success": True
                    }

                # Execute Tool
                if tool_name in self.tool_map:
                    tool_args = decision.get('args', {})
                    if tool_name == 'get_my_orders' and user_id:
                         tool_args['user_id'] = user_id
                    
                    # Log thinking
                    self.conversations[session_id].append({"role": "assistant", "content": json.dumps(decision)})
                    
                    try:
                        tool_result = self.tool_map[tool_name].invoke(tool_args)
                        self.conversations[session_id].append({
                            "role": "system",
                            "content": f"TOOL_RESULT ({tool_name}): {str(tool_result)}"
                        })
                    except Exception as e:
                        self.conversations[session_id].append({
                            "role": "system",
                            "content": f"Error executing {tool_name}: {str(e)}"
                        })
                else:
                    self.conversations[session_id].append({
                        "role": "system",
                        "content": f"Tool '{tool_name}' not found."
                    })

            # Save assistant response
            if isinstance(final_response, dict):
                content = final_response.get('message', str(final_response))
            else:
                content = str(final_response)
                
            self.conversations[session_id].append({"role": "assistant", "content": content})
            
            return {
                "response": content,
                "session_id": session_id,
                "language": preferred_lang,
                "success": True
            }

        except Exception as e:
            logger.error(f"Ecommerce Agent Error: {e}", exc_info=True)
            return {
                "response": "An error occurred while processing your e-commerce request.",
                "session_id": session_id,
                "success": False,
                "error": str(e)
            }
