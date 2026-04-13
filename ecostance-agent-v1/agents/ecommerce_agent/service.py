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
from .tools.web_search_tools import create_web_search_tool

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
1. `list_database_tables()` / `get_database_schema()`: CALL THIS FIRST to see the database schema before writing SQL.
2. `get_data_from_connected_database(sql_query)`: Run SQL queries against the connected database.
3. `find_products(search, category_slug)`: Search products via API (if no DB connected).
4. `get_all_categories()`: Get product categories via API (if no DB connected).
5. `get_my_orders(user_id)`: Get order history via API (if no DB connected).
6. `search_knowledge_base(kb_name, query)`: Search company documents/FAQs.
7. `list_available_knowledge_bases()`: List available knowledge bases.
8. `web_search(query)`: Search the web for general/educational information only (e.g. "what is aromatherapy", "difference between eau de parfum and eau de toilette"). NEVER use web search results to suggest, list, or recommend products.

### CRITICAL RULES:
- If a database is connected, ALWAYS use `list_database_tables` / `get_database_schema` then IMMEDIATELY `query_database` / `get_data_from_connected_database` to answer the question. Do NOT stop after listing tables — use the schema to write and run the SQL query.
- NEVER guess column names — always check schema first.
- NEVER make up data — only use what tools return.
- NEVER just describe the schema to the user — always proceed to answer their question with a query.
- KEY DB RELATIONSHIPS: perfume scent notes are in `scent_notes` table joined via `perfume_notes` (perfume_id, scent_note_id). Moods via `perfume_moods` → `moods`. Family via `fragrance_families`. Brand via `brands`. Pricing via `perfume_sizes`. NEVER query `perfumes.ingredients` — it does not exist.
- PRODUCT SUGGESTIONS RULE: When a user asks both an educational question AND for a product suggestion (e.g. "explain aromatherapy and suggest a perfume"), you MUST:
  1. Use `web_search` ONLY for the educational/informational part.
  2. Use `find_products` or `get_data_from_connected_database` for the product suggestion part.
  3. NEVER carry over product names, brands, or items from web search results into your product suggestions.
  4. Only suggest products that actually exist in our shop's database or API response.
  5. NEVER use your own training knowledge to name or suggest products — if the DB/API returns no results, say "we don't have that in our store" instead of inventing product names.
  6. If PRE_FETCHED SCHEMA is present in context, use it immediately to write a SQL query — do NOT call list_database_tables again.
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
        # Web search with Tavily → DuckDuckGo fallback, ecommerce topics only
        self.tools.append(create_web_search_tool())
            
        self.tool_map = {tool.name: tool for tool in self.tools}
        
        # In-memory conversation storage
        self.conversations: Dict[str, List[Dict]] = {}
        
    def _prefetch_products(self, message: str, session_id: str) -> bool:
        """
        Fetch full product catalog from DB and inject into context.
        Returns True if successful so caller can bypass the tool loop.
        """
        query_tool = self.tool_map.get('get_data_from_connected_database')
        if not query_tool:
            return False

        try:
            from app.routers import db_router
            connector = db_router.db_connector
            if not connector or not (connector.engine or connector.client):
                return False
        except Exception:
            return False

        try:
            catalog_sql = """
                SELECT p.name, b.name as brand, p.concentration, p.gender_target,
                       ff.name as fragrance_family,
                       GROUP_CONCAT(sn.name || ' (' || pn.layer || ')', ', ') as notes
                FROM perfumes p
                JOIN brands b ON p.brand_id = b.id
                JOIN fragrance_families ff ON p.fragrance_family_id = ff.id
                LEFT JOIN perfume_notes pn ON pn.perfume_id = p.id
                LEFT JOIN scent_notes sn ON sn.id = pn.scent_note_id
                WHERE p.is_discontinued = 0
                GROUP BY p.id
                ORDER BY p.name
            """
            catalog = query_tool.invoke({"sql_query": catalog_sql.strip()})
            if not catalog or 'Error' in catalog:
                logger.warning(f"Prefetch catalog failed: {catalog[:100]}")
                return False

            self.conversations[session_id].append({
                "role": "system",
                "content": (
                    "STORE PRODUCT CATALOG — complete list of all real products with their scent notes:\n"
                    f"{catalog}"
                )
            })
            logger.info(f"Prefetch complete for session {session_id}, catalog length: {len(catalog)}")
            return True

        except Exception as e:
            logger.warning(f"Prefetch failed: {e}")
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

            # Always append the current user message
            self.conversations[session_id].append({"role": "user", "content": message})

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

            # Pre-fetch DB schema when product intent detected — MUST be after session_db is set
            prefetch_done = self._prefetch_products(message, session_id)

            # If prefetch ran successfully, skip the tool loop — answer directly from catalog
            if prefetch_done:
                from langchain_core.messages import SystemMessage as SM
                catalog_content = next(
                    (m["content"] for m in reversed(self.conversations[session_id])
                     if m["role"] == "system" and "STORE PRODUCT CATALOG" in m.get("content", "")),
                    ""
                )
                final_result = self.llm.invoke([
                    SM(content=(
                        f"{self.get_system_prompt(preferred_lang)}\n\n"
                        "Answer the customer using ONLY the products listed below. "
                        "Do NOT invent product names not in this list.\n\n"
                        f"{catalog_content}"
                    )),
                    HumanMessage(content=message)
                ])
                content = final_result.content
                self.conversations[session_id].append({"role": "assistant", "content": content})
                return {"response": content, "session_id": session_id, "language": preferred_lang, "success": True}
            
            # Get language-specific system prompt
            system_prompt = self.get_system_prompt(preferred_lang)
            
            # Construct Prompt
            tool_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])

            context_info = f"\nUser ID: {user_id if user_id else 'Not Logged In'}\nDetected Language: {detected_lang}\nPreferred Response Language: {preferred_lang}"
            if session_id in self.session_kb:
                 context_info += f"\nActive Knowledge Base: {self.session_kb[session_id]}"
            if session_id in self.session_db:
                 context_info += f"\nActive Database: {self.session_db[session_id]} (CONNECTED — use list_database_tables then get_data_from_connected_database for all product/data queries)"
            else:
                 context_info += f"\nActive Database: None (use find_products / get_all_categories API tools instead)"

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
- If PRE_FETCHED PRODUCT DATA is present in the conversation, use it DIRECTLY to answer — do NOT call any database tools again, the data is already there.
- If you just got a TOOL_RESULT from `list_database_tables` / `get_database_schema`, you MUST immediately call `query_database` / `get_data_from_connected_database` with the correct SQL to answer the user's question. DO NOT stop and describe the schema.
- If you have query results, ANALYZE THEM and provide a human-friendly answer.
- NEVER tell the user what the schema looks like — just use it to answer their question.
- If the user asks an educational question AND wants a product suggestion (e.g. "explain aromatherapy and suggest a perfume"), split the work: use `web_search` for the educational part, then use `find_products` or `get_data_from_connected_database` for the product part. NEVER suggest products based on web search results — only suggest products returned by shop tools.
- If a web_search result starts with "WEB_SEARCH_UNAVAILABLE", skip the web explanation and go directly to the shop database tools to answer the product part. NEVER use your own training knowledge to suggest products — only use what the DB or API tools return.

FORMAT:
{{
    "tool": "tool_name",
    "args": {{...}},
    "reasoning": "why this tool"
}}
OR (if finished):
{{
    "tool": "none",
    "response": "Your complete human-friendly answer here including all data"
}}
""")]
                
                # Build history: include all user/assistant turns, but only system (tool) messages from current turn
                # Find index of the current user message (last user message)
                history = self.conversations[session_id]
                last_user_idx = max((i for i, m in enumerate(history) if m["role"] == "user"), default=0)
                
                for msg in history[-8:]:
                    idx = history.index(msg) if msg in history else -1
                    if msg["role"] == "user":
                        lc_messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        lc_messages.append(AIMessage(content=msg["content"]))
                    elif msg["role"] == "system" and history.index(msg) >= last_user_idx:
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

                # Normalize OpenAI function-calling format → our internal format
                # e.g. {"type": "function", "name": "tool_name", "parameters": {...}}
                if decision and decision.get('type') == 'function' and 'name' in decision:
                    decision = {
                        'tool': decision['name'],
                        'args': decision.get('parameters', decision.get('arguments', {})),
                        'reasoning': 'normalized from function-call format'
                    }

                if not decision:
                    self.conversations[session_id].append({"role": "assistant", "content": text})
                    return {"response": text, "session_id": session_id, "success": True}

                tool_name = decision.get('tool')
                
                if tool_name == 'none' or not tool_name:
                    final_response = decision.get('response', text)
                    if isinstance(final_response, dict):
                        message = final_response.get('message', '')
                        data = final_response.get('data')
                        if data:
                            content = f"{message}\n{json.dumps(data, indent=2)}" if message else json.dumps(data, indent=2)
                        else:
                            content = message or str(final_response)
                    else:
                        content = str(final_response)
                        
                    self.conversations[session_id].append({"role": "assistant", "content": content})
                    return {
                        "response": content,
                        "session_id": session_id,
                        "language": preferred_lang,
                        "success": True
                    }

                # On last iteration, force a final answer instead of leaking raw tool JSON
                if is_last_turn:
                    self.conversations[session_id].append({
                        "role": "system",
                        "content": "You have reached the maximum number of steps. Summarize what you know so far into a final human-friendly answer."
                    })
                    final_result = self.llm.invoke(lc_messages + [SystemMessage(content="Provide your final answer now based on all results so far.")])
                    content = final_result.content
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
                message = final_response.get('message', '')
                data = final_response.get('data')
                if data:
                    content = f"{message}\n{json.dumps(data, indent=2)}" if message else json.dumps(data, indent=2)
                else:
                    content = message or str(final_response)
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
