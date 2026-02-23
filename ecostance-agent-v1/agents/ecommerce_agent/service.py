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

from app.services.multilingual_utils import MultilingualAgentMixin

logger = logging.getLogger(__name__)

ECOMMERCE_SYSTEM_PROMPTS = {
    "en": """You are the E-Commerce Shopping Assistant.
Your goal is to help customers find products and check their orders.
Respond in the same language as the customer's question.

### RESPONSE FORMAT RULES
1. **Normal Chat**: If you are just talking, greeting, or explaining, answer normally.
2. **Data Found**: If you use a tool (like `find_products`) and get results, you MUST return a JSON object strictly following this format:
   ```json
   {
     "type": "product_list",
     "message": "Brief text introduction here",
     "data": { "items": [ ...raw tool results... ] }
   }
   ```
3. **Links/Actions**: If the user needs a specific page (like login), return:
   ```json
   {
     "type": "url_action",
     "message": "Please log in first",
     "data": { "url": "/login", "button_text": "Log In" }
   }
   ```

### AVAILABLE TOOLS:
1. `find_products(search, category_slug)`: Returns list of products.
2. `get_all_categories()`: Returns list of categories.
3. `get_my_orders(user_id)`: Returns order history.
""",
    "es": """Eres el Asistente de Compras de Comercio Electrónico.
Tu objetivo es ayudar a los clientes a encontrar productos y revisar sus pedidos.
Responde en el mismo idioma que la pregunta del cliente.

### REGLAS DE FORMATO DE RESPUESTA
1. **Chat Normal**: Si solo estás hablando, saludando o explicando, responde normalmente.
2. **Datos Encontrados**: Si usas una herramienta y obtienes resultados, DEBES devolver un objeto JSON siguiendo este formato:
   ```json
   {
     "type": "product_list",
     "message": "Breve introducción de texto aquí",
     "data": { "items": [ ...resultados de la herramienta... ] }
   }
   ```
""",
    "fr": """Vous êtes l'Assistant d'Achat E-Commerce.
Votre objectif est d'aider les clients à trouver des produits et à vérifier leurs commandes.
Répondez dans la même langue que la question du client.

### RÈGLES DE FORMAT DE RÉPONSE
1. **Chat Normal**: Si vous ne faites que parler, saluer ou expliquer, répondez normalement.
2. **Données Trouvées**: Si vous utilisez un outil et obtenez des résultats, vous DEVEZ retourner un objet JSON suivant ce format :
   ```json
   {
     "type": "product_list",
     "message": "Brève introduction textuelle ici",
     "data": { "items": [ ...résultats de l'outil... ] }
   }
   ```
"""
}

# Strict whitelist of allowed tools for E-Commerce agent
SAFE_TOOL_WHITELIST = {"product_search", "categories", "orders"}

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
- If you have tool results, ANALYZE THEM and provide a human-friendly response. DO NOT just repeat raw data.
- If finding products, highlight the top 2-3 matches.

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
                    final_msg = {"type": "text", "message": text, "data": None}
                    self.conversations[session_id].append({"role": "assistant", "content": text})
                    return {"content": text, "session_id": session_id, "success": True}

                tool_name = decision.get('tool')
                
                if tool_name == 'none' or not tool_name or is_last_turn:
                    final_response = decision.get('response', text)
                    if isinstance(final_response, dict):
                        content = final_response.get('message', str(final_response))
                    else:
                        content = str(final_response)
                        
                    self.conversations[session_id].append({"role": "assistant", "content": content})
                    return {
                        "content": content,
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
            self.conversations[session_id].append({"role": "assistant", "content": json.dumps(final_response)})
            
            return {
                "response": final_response,
                "session_id": session_id,
                "language": preferred_lang,
                "success": True
            }

        except Exception as e:
            logger.error(f"Ecommerce Agent Error: {e}", exc_info=True)
            return {
                "response": {"type": "text", "message": "An error occurred.", "data": None},
                "session_id": session_id,
                "success": False,
                "error": str(e)
            }
