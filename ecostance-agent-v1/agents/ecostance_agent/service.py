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

from .config import AGENT_MODEL, GOOGLE_API_KEY, GROQ_API_KEY, LLM_PROVIDER, AGENT_TEMPERATURE
from .tools.certificate_tools import get_certificate_details, search_certificates, get_certificate_stats
from .tools.shopping_tools import search_eco_products, get_eco_impact_summary
from .tools.kb_tools import create_ecostance_kb_tools

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
- For product/project searches, typically use `kb_name="eco-product-list"`.

CRITICAL: Always use type: "text" in your response containing the tags.
"""
}

SAFE_TOOLS = {"certificates", "shopping", "impact", "faq", "knowledge_base", "tracking", "payments", "complaints"}

class EcoStanceAgentService(MultilingualAgentMixin):
    def __init__(self, tenant_id: str = None, allowed_tools: List[str] = None, **kwargs):
        super().__init__(system_prompts=ECOSTANCE_SYSTEM_PROMPTS)
        
        if str(LLM_PROVIDER).lower() == "groq":
            self.llm = ChatGroq(
                model=AGENT_MODEL,
                groq_api_key=GROQ_API_KEY,
                model_name=AGENT_MODEL,
                temperature=AGENT_TEMPERATURE
            )
        else:
            self.llm = ChatGoogleGenerativeAI(
                model=AGENT_MODEL,
                google_api_key=GOOGLE_API_KEY,
                temperature=AGENT_TEMPERATURE
            )
        self.tenant_id = tenant_id
        
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
        for category in ["tracking", "payments", "complaints", "delivery_estimates"]:
            if category in requested_tools and category in TOOL_CATEGORIES:
                self.tools.extend(TOOL_CATEGORIES[category])
            
        self.tool_map = {tool.name: tool for tool in self.tools}
        self.conversations: Dict[str, List[Dict]] = {}
        
    def chat(self, session_id: str, message: str, knowledge_base: str = None, database_connection: str = None, user_id: str = None, user_language: str = None) -> Dict:
        try:
            detected_lang, preferred_lang, confidence = self.get_language_context(
                message, session_id, user_language
            )
            
            if session_id not in self.conversations:
                self.conversations[session_id] = []
            
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
                                items_tags = "".join([f"[PRODUCT:{item.get('id', 'unknown')}]" if item.get('item_type') != 'project' else f"[PROJECT:{item.get('id', 'unknown')}]" for item in tool_result[:3]])
                                final_response = {
                                    "type": "text",
                                    "message": f"I've found some options for you! {items_tags}",
                                    "data": None
                                }
                            else:
                                # Fallback: Try searching Knowledge Base if store API failed
                                logger.info("Product search empty, falling back to KB search")
                                kb_tool = self.tool_map.get('search_knowledge_base')
                                if kb_tool:
                                    kb_query = tool_args.get('search') or tool_args.get('category') or message
                                    # Fix: Provide both query and kb_name
                                    kb_result = kb_tool.invoke({
                                        "query": kb_query, 
                                        "kb_name": tool_args.get('kb_name', 'eco-product-list')
                                    })
                                    
                                    # Use the KB formatter logic
                                    format_prompt = f"""
                                    You are the expert EcoStance Ambassador.
                                    User Query: {message}
                                    Knowledge Base Content: {kb_result}
                                    
                                    YOUR GOAL: Answer the user's question, but YOU MUST SHOW THE PRODUCT CARD.
                                    
                                    INSTRUCTIONS:
                                    1. Identify if the content mentions a product.
                                    2. Manually map it to one of these IDs if possible:
                                       - "Nitrous Gas Removal" -> [PRODUCT:e1]
                                       - "Piedra Wind Farm" -> [PRODUCT:e2]
                                       - "SantaClara" -> [PRODUCT:e3]
                                       - "Xinjiang" -> [PRODUCT:e4]
                                       - "Piedra II" -> [PRODUCT:e5]
                                       - "Solar Cooker" -> [PRODUCT:e6]
                                       - "PACAJAI" -> [PRODUCT:e7]
                                       - "KARIBA" -> [PRODUCT:e8]
                                       - "VALPARAISO" -> [PRODUCT:e9]
                                       - "Siviru" -> [PRODUCT:e10]
                                       - "Seima" -> [PRODUCT:e11]
                                       - "REC Certificate" -> [PRODUCT:e12]
                                    
                                    3. Construct a natural response.
                                    4. CRITICAL: Append the [PRODUCT:id] tag to your response.
                                    
                                    Respond ONLY with the natural chat text containing the tag.
                                    """
                                    format_res = self.llm.invoke([HumanMessage(content=format_prompt)])
                                    final_response = {"type": "text", "message": format_res.content, "data": None}
                                else:
                                    final_response = {
                                        "type": "text",
                                        "message": "I couldn't find those products in the store or our records.",
                                        "data": None
                                    }
                        elif tool_name == 'get_eco_impact_summary':
                            final_response = {
                                "type": "impact_stats",
                                "message": "Here is your sustainability impact summary.",
                                "data": tool_result
                            }
                        elif tool_name in ['search_knowledge_base', 'search_faq']:
                            # Use the LLM to format the KB result into a conversation response with [PRODUCT:id] tags
                            format_prompt = f"""
                            You are the expert EcoStance Ambassador.
                            User Query: {message}
                            Knowledge Base Content: {tool_result}
                            
                            YOUR GOAL: Answer the user's question, but YOU MUST SHOW THE PRODUCT CARD.
                            
                            INSTRUCTIONS:
                            1. Identify if the content mentions a product (e.g., "Gas Removal", "Wind Farm", "Cooker").
                            2. Manually map it to one of these IDs if possible:
                               - "Nitrous Gas Removal" -> [PRODUCT:e1]
                               - "Piedra Wind Farm" -> [PRODUCT:e2]
                               - "SantaClara" -> [PRODUCT:e3]
                               - "Xinjiang" -> [PRODUCT:e4]
                               - "Piedra II" -> [PRODUCT:e5]
                               - "Solar Cooker" -> [PRODUCT:e6]
                               - "PACAJAI" -> [PRODUCT:e7]
                               - "KARIBA" -> [PRODUCT:e8]
                               - "VALPARAISO" -> [PRODUCT:e9]
                               - "Siviru" -> [PRODUCT:e10]
                               - "Seima" -> [PRODUCT:e11]
                               - "REC Certificate" -> [PRODUCT:e12]
                            
                            3. Construct a natural response that answers the specific question (like price).
                            4. CRITICAL: Append the [PRODUCT:id] tag to your response.
                            
                            Example: "The price for Nitrous Gas Removal is $540. [PRODUCT:e1]"
                            
                            Respond ONLY with the natural chat text containing the tag.
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

            self.conversations[session_id].append({"role": "assistant", "content": json.dumps(final_response)})
            
            return {
                "response": final_response,
                "session_id": session_id,
                "language": preferred_lang,
                "success": True
            }

        except Exception as e:
            logger.error(f"EcoStance Agent Error: {e}", exc_info=True)
            return {
                "response": {"type": "text", "message": "I'm having a bit of trouble, please try again."},
                "session_id": session_id,
                "success": False
            }
