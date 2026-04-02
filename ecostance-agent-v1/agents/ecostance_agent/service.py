"""
EcoStance Agent Service
Handles Customer Support, FAQ, Shopping Assistance, and Carbon Tracking.
"""
import logging
import json
import re
from typing import List, Dict, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from .config import AGENT_MODEL, GOOGLE_API_KEY, GROQ_API_KEY, LLM_PROVIDER, AGENT_TEMPERATURE, ECOMMERCE_API_URL
import requests
from .tools.certificate_tools import get_certificate_details, search_certificates, get_certificate_stats
from .tools.shopping_tools import search_eco_products, get_eco_impact_summary
from .tools.kb_tools import create_ecostance_kb_tools

from agents.generic_agent.tools.db_tools import create_db_query_tool, create_list_db_tables_tool
from agents.generic_agent.tools.web_search_tools import create_web_search_tool

# Shared tools from the platform
from app.tools.shared_tools import (
    create_search_knowledge_base_tool,
    create_list_knowledge_bases_tool
)

from app.services.multilingual_utils import MultilingualAgentMixin

logger = logging.getLogger(__name__)

ECOSTANCE_SYSTEM_PROMPTS = {
    "en": """You are an EcoStance climate advisor.

### SCOPE & GROUNDING (CRITICAL)
1. You are NOT a general assistant. You do NOT know about the weather, sports, recent news, or general trivia.
2. If a user asks a question outside your scope (e.g., "What is the weather?", "Who won the game?"), politely refuse and guide them back to EcoStance topics.
   - Example: "I'm sorry, I can only help with carbon offsetting and our eco-friendly products. How can I assist you with your sustainability goals?"
3. Do NOT try to awkwardly bridge unrelated topics (like weather) to selling products. Just stick to your role.

### VISUAL TAG RULES (STRICT)
You MUST use these tags to render cards:
- **Products**: [PRODUCT:id] (e.g., [PRODUCT:e1]) -> Use for "buy", "shop", "price" queries.
- **Projects**: [PROJECT:id] (e.g., [PROJECT:1]) -> Use for "learn about", "support", "project info" queries.
- **Certificates**: [CERTIFICATE:id] (e.g., [CERTIFICATE:ECO-2024-123]) -> Use ONLY for "track", "validate", "my certificate" queries.

### PRIVACY & SECURITY
1. **Certificates are private.** NEVER search for or show a certificate unless the user explicitly provides a Certificate ID, Number, or Serial.
2. If a user asks about "projects", show them [PROJECT:id] or [PRODUCT:id] options. Do NOT try to track a certificate.
3. If a user asks "show my certificates" without an ID, ask them to provide their Certificate Number first (unless they are logged in and you have their user_id).

### KNOWLEDGE BASE HINTS
- For product/project searches, use the provided Knowledge Base name if one is 'Active'. 
- If no Knowledge Base is active, do NOT attempt to search. Ask the user to select one instead.

### DATABASE USAGE
- If a database connection is active, you can use `query_database` to look up structured information that might not be in the knowledge base.
- Do NOT search the database unless a connection is listed as Active.

CRITICAL: Always use type: "text" in your response containing the tags.
"""
}

SAFE_TOOLS = {"certificates", "shopping", "impact", "faq", "knowledge_base", "tracking", "payments", "complaints", "database_query", "web_search"}

class EcoStanceAgentService(MultilingualAgentMixin):
    def __init__(self, tenant_id: str = None, allowed_tools: List[str] = None, database_connection: str = None, **kwargs):
        super().__init__(system_prompts=ECOSTANCE_SYSTEM_PROMPTS)
        
        if str(LLM_PROVIDER).lower() == "groq":
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
        self.database_connection = database_connection
        
        # Build tools
        self.tools = []
        requested_tools = allowed_tools if allowed_tools else list(SAFE_TOOLS)
        
        logger.info(f"Initializing EcoStance agent with tools: {requested_tools}")
        
        if "certificates" in requested_tools:
            self.tools.extend([get_certificate_details, search_certificates, get_certificate_stats])
        if "shopping" in requested_tools:
            self.tools.append(search_eco_products)
        if "impact" in requested_tools:
            self.tools.append(get_eco_impact_summary)
        if "faq" in requested_tools:
            kb_tools = create_ecostance_kb_tools(self.tenant_id)
            self.tools.extend(kb_tools)
            
        # Add platform-wide Knowledge Base tools
        if "knowledge_base" in requested_tools:
            self.tools.extend([
                create_search_knowledge_base_tool(self.tenant_id),
                create_list_knowledge_bases_tool(self.tenant_id)
            ])
            
        # Add Database tools
        if "database_query" in requested_tools:
            self.tools.append(create_db_query_tool(self.database_connection, tenant_id=self.tenant_id))
            self.tools.append(create_list_db_tables_tool(self.database_connection, tenant_id=self.tenant_id))

        # Add web search — eco/sustainability/carbon topics only
        if "web_search" in requested_tools:
            self.tools.append(create_web_search_tool(
                allowed_topics=["business", "technology", "industry", "company", "product", "brand"],
                block_store_queries=False
            ))
            
            
        self.tool_map = {tool.name: tool for tool in self.tools}
        self.conversations: Dict[str, List[Dict]] = {}
        self._product_registry = {}  # Cache: { "name": "[PRODUCT:id]" }
        
    def _get_dynamic_product_mapping(self, context_text: str = "") -> str:
        """
        Dynamically builds a mapping string for the prompt based on existing products.
        If context_text is provided, it can prioritize mentioned products.
        """
        try:
            # 1. Refresh registry if empty
            if not self._product_registry:
                # Load products
                res = requests.get(f"{ECOMMERCE_API_URL}/products", timeout=3)
                if res.status_code == 200:
                    data = res.json().get('data', [])
                    for p in data:
                        p_id = p.get('id')
                        p_name = p.get('name')
                        if p_id and p_name:
                            self._product_registry[p_name] = f"[PRODUCT:{p_id}]"
                
                # Load projects
                res = requests.get(f"{ECOMMERCE_API_URL}/projects", timeout=3)
                if res.status_code == 200:
                    data = res.json().get('data', [])
                    for p in data:
                        p_id = p.get('id')
                        p_title = p.get('title')
                        if p_id and p_title:
                            self._product_registry[p_title] = f"[PROJECT:{p_id}]"

            # 2. Filter mapping to only include products mentioned in context_text (if any)
            relevant_mapping = []
            for name, tag in self._product_registry.items():
                if not context_text or name.lower() in context_text.lower():
                    relevant_mapping.append(f'- "{name}" -> {tag}')
            
            if not relevant_mapping:
                 # If context given but no match, return empty to avoid bloat
                 if context_text: return "No matching products found in this context."
                 # If no context given (global fetch), show top few
                 return "\n".join([f'- "{k}" -> {v}' for k, v in list(self._product_registry.items())[:12]])
                
            return "\n".join(relevant_mapping)
        except Exception as e:
            logger.error(f"Error building dynamic registry: {e}")
            return "No specific mapping available."
        
    def chat(self, session_id: str, message: str, knowledge_base: str = None, database_connection: str = None, user_id: str = None, user_language: str = None, chat_history: List[Dict] = None, **kwargs) -> Dict:
        try:
            detected_lang, preferred_lang, confidence = self.get_language_context(
                message, session_id, user_language
            )
            
            if session_id not in self.conversations:
                self.conversations[session_id] = []
                if chat_history:
                    # Filter history to only include user and assistant roles for compatibility
                    for msg in chat_history:
                        if msg.get("role") in ["user", "assistant"]:
                            self.conversations[session_id].append(msg)
            
            self.conversations[session_id].append({"role": "user", "content": message})
            
            # Context about selected KB and DB
            context_info = ""
            if knowledge_base:
                context_info += f"\n- Active Knowledge Base: {knowledge_base}. (Use this as 'kb_name' when searching)"
            if database_connection:
                context_info += f"\n- Database Connection: {database_connection}"
            
            system_prompt = self.get_system_prompt(preferred_lang)
            tool_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])
            
            full_prompt = f"""{system_prompt}

Tools Available:
{tool_descriptions}

Context:
- User ID: {user_id or 'Anonymous'}
- Detected Language: {detected_lang}
- Responding in: {preferred_lang}{context_info}

Question: "{message}"

Respond with the appropriate JSON structure or text.

### TOOL USAGE RULES (STRICT)
1. If you need data, output ONLY the JSON for the tool call.
2. DO NOT make up or "simulate" the tool output. Wait for the system to run it.
3. DO NOT output a second JSON object with fake products.
4. **Lowest Price Queries**: If the user asks for "lowest price" or "cheapest", DO NOT set `price_max: 0`. It will return nothing. Instead, leave it empty or set a reasonable limit (e.g. 100).
5. **Category Filter**: Leave `category` empty unless the user explicitly asks for a specific category (e.g., "Show me wind energy" or "carbon offsets"). Do not guess.

Format for tool call:
{{
  "tool": "tool_name",
  "args": {{...}},
  "reasoning": "..."
}}
"""
            result = self.llm.invoke([HumanMessage(content=full_prompt)])
            decision_text = result.content
            logger.info(f"LLM Decision Text: {decision_text}")
            
            # Improved parsing to handle cases where LLM outputs multiple JSONs or extra text
            match = re.search(r'(\{.*?\})\s*(?=\{|$)', decision_text, re.DOTALL)
            if not match:
                # Fallback: try finding the first block bounded by {}
                try:
                    start = decision_text.index('{')
                    end = decision_text.rindex('}') + 1
                    # This is still risky if multiple objects exist, so we parse iteratively if needed
                    # But for now, let's try to grab just the first object if the regex failed
                    possible_json = decision_text[start:]
                    decoder = json.JSONDecoder()
                    decision, _ = decoder.raw_decode(possible_json)
                except (ValueError, IndexError):
                     # Text only response
                    final_response = {"type": "text", "message": decision_text, "data": None}
                    decision = {} # Valid decision object to skip 'else' block
            else:
                try:
                    decision = json.loads(match.group(1))
                except json.JSONDecodeError:
                     # If regex failed to isolate clean JSON, try raw_decode technique
                    try:
                        start = decision_text.index('{')
                        decoder = json.JSONDecoder()
                        decision, _ = decoder.raw_decode(decision_text[start:])
                    except:
                        decision = {}
                        final_response = {"type": "text", "message": decision_text, "data": None}
                if 'tool' in decision and decision['tool'] != 'none':
                    tool_name = decision['tool']
                    logger.info(f"Agent decided to use tool: {tool_name}")
                    
                    if tool_name in self.tool_map:
                        tool_args = decision.get('args', {})
                        # Special handling for user_id in impact summary
                        if tool_name == 'get_eco_impact_summary' and not tool_args.get('user_id'):
                            tool_args['user_id'] = user_id or "Guest"
                            
                        tool_result = self.tool_map[tool_name].invoke(tool_args)
                        logger.info(f"Tool {tool_name} returned result length: {len(str(tool_result))}")
                        
                        # Map tool result back to a custom UI component using the tag protocol
                        if tool_name in ['get_certificate_details', 'search_certificates']:
                            # Extract identifier for tagging
                            cert_id = "unknown"
                            if isinstance(tool_result, dict):
                                cert_id = tool_result.get('id') or tool_result.get('certificate_number') or "unknown"
                            
                            format_prompt = f"""
                            You are the EcoStance Ambassador. You just searched for a certificate.
                            Result Data: {tool_result}
                            
                            TASK:
                            1. Interpret the data.
                            2. If found, respond with a text message and use [CERTIFICATE:{cert_id}] to show the card.
                            3. If multiple found, use multiple tags.
                            4. If not found, explain nicely.
                            
                            Respond ONLY with the natural chat text.
                            """
                            format_res = self.llm.invoke([HumanMessage(content=format_prompt)])
                            final_response = {"type": "text", "message": format_res.content, "data": None}
                            
                        elif tool_name == 'get_certificate_stats':
                            final_response = {
                                "type": "impact_stats",
                                "message": "Here is the global sustainability summary:",
                                "data": tool_result
                            }
                        elif tool_name == 'search_eco_products':
                            if isinstance(tool_result, list) and len(tool_result) > 0:
                                # Convert the list of products into a tagged response
                                items_tags = "".join([f"[PRODUCT:{item.get('id', 'unknown')}]" if item.get('item_type') != 'project' else f"[PROJECT:{item.get('id', 'unknown')}]" for item in tool_result[:5]])
                                final_response = {
                                    "type": "text",
                                    "message": f"I've found some options for you! {items_tags}",
                                    "data": None
                                }
                            else:
                                # Fallback: Try searching Knowledge Base IF one is selected
                                selected_kb = knowledge_base or tool_args.get('kb_name')
                                if selected_kb:
                                    logger.info(f"Product search empty, falling back to KB search in: {selected_kb}")
                                    kb_tool = self.tool_map.get('search_knowledge_base')
                                    if kb_tool:
                                        kb_query = tool_args.get('search') or tool_args.get('category') or message
                                        kb_result = kb_tool.invoke({
                                            "query": kb_query, 
                                            "kb_name": selected_kb
                                        })
                                        
                                        # Use the KB formatter logic
                                        format_prompt = f"""
                                        You are the expert EcoStance Ambassador.
                                        User Query: {message}
                                        Knowledge Base Content: {kb_result}
                                        
                                        YOUR GOAL: Answer the user's question. You MUST show relevant PRODUCT or PROJECT cards.
                                        
                                        INSTRUCTIONS:
                                        1. Identify the MOST RELEVANT products/projects (MAX 3) mentioned in the Knowledge Base Content provided below.
                                        2. Map names to IDs using this guide:
    {self._get_dynamic_product_mapping(str(kb_result))}
                                        
                                        3. Construct a natural response.
                                        4. CRITICAL: Include ONLY the top relevant [PRODUCT:id] or [PROJECT:id] tags. Do NOT list products that are not in the search results.
                                        
                                        Respond ONLY with the natural chat text containing the tags.
                                        """
                                        format_res = self.llm.invoke([HumanMessage(content=format_prompt)])
                                        final_response = {"type": "text", "message": format_res.content, "data": None}
                                    else:
                                        final_response = {
                                            "type": "text",
                                            "message": "I couldn't find those products in the store or our records.",
                                            "data": None
                                        }
                                else:
                                    final_response = {
                                        "type": "text",
                                        "message": "I couldn't find those products in the store. Please select a Knowledge Base to search for more detailed documentation.",
                                        "data": None
                                    }
                        elif tool_name == 'get_eco_impact_summary':
                            final_response = {
                                "type": "impact_stats",
                                "message": "Here is your sustainability impact summary.",
                                "data": tool_result
                            }
                        elif tool_name in ['search_knowledge_base', 'search_faq']:
                            # Intercept if no KB selected
                            selected_kb = knowledge_base or tool_args.get('kb_name')
                            if not selected_kb:
                                final_response = {
                                    "type": "text",
                                    "message": "Please select a Knowledge Base from the sidebar before I can search for expert documentation.",
                                    "data": None
                                }
                            else:
                                # Use the LLM to format the KB result into a conversation response with [PRODUCT:id] tags
                                format_prompt = f"""
                                You are the expert EcoStance Ambassador.
                                User Query: {message}
                                Knowledge Base Content: {tool_result}
                                
                                YOUR GOAL: Answer the user's question. You MUST show relevant PRODUCT or PROJECT cards.
                                
                                INSTRUCTIONS:
                                1. Identify the MOST RELEVANT products/projects (MAX 3) mentioned in the tool results provided below.
                                2. Map names to IDs using this guide:
    {self._get_dynamic_product_mapping(str(tool_result))}
                                
                                3. Construct a natural response that answers the specific question.
                                4. CRITICAL: Include ONLY the relevant [PRODUCT:id] or [PROJECT:id] tags. Do NOT tag products that are not found in the results.
                                
                                Example: "We have Nitrous Gas Removal ($540). [PRODUCT:e1]"
                                
                                Respond ONLY with the natural chat text containing the tags.
                                """
                                format_res = self.llm.invoke([HumanMessage(content=format_prompt)])
                                # Force type: text as per protocol
                                final_response = {"type": "text", "message": format_res.content, "data": None}
                        else:
                            final_response = {
                                "type": "text",
                                "message": str(tool_result),
                                "data": None
                            }
                    else:
                        # Fallback for hallucinated tools
                        final_response = {"type": "text", "message": "I tried to use a tool that isn't available. Let me try answering from my general knowledge.", "data": None}
                else:
                    # It was already a direct response in JSON or malformed
                    final_response = decision if 'type' in decision else {"type": "text", "message": str(decision), "data": None}

            content = final_response.get("message") if isinstance(final_response, dict) else str(final_response)
            self.conversations[session_id].append({"role": "assistant", "content": content})
            
            return {
                "response": content,
                "session_id": session_id,
                "language": preferred_lang,
                "success": True
            }

        except Exception as e:
            logger.error(f"EcoStance Agent Error: {e}", exc_info=True)
            return {
                "response": "I'm having a bit of trouble connecting to my service, please try again.",
                "session_id": session_id,
                "success": False,
                "error": str(e)
            }
    def reset_conversation(self, session_id: str) -> bool:
        """Reset conversation history for a session."""
        if session_id in self.conversations:
            self.conversations[session_id] = []
            return True
        return False
