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

    def chat(self, session_id: str, message: str, user_id: str = None, user_language: str = None) -> Dict:
        """
        Process a chat message with multilingual support.
        """
        try:
            # Language Detection
            detected_lang, preferred_lang, confidence = self.get_language_context(
                message, session_id, user_language
            )
            
            # Init history
            if session_id not in self.conversations:
                self.conversations[session_id] = []
                
            # Add user message
            self.conversations[session_id].append({"role": "user", "content": message})
            
            # Get language-specific system prompt
            system_prompt = self.get_system_prompt(preferred_lang)
            
            # Construct Prompt
            tool_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])
            context_info = f"\nUser ID: {user_id if user_id else 'Not Logged In'}\nDetected Language: {detected_lang}\nPreferred Response Language: {preferred_lang}"
            
            full_prompt = f"""{system_prompt}

Tools Available:
{tool_descriptions}

Context:
{context_info}

Current Query: "{message}"

Respond with ONLY the JSON object for tool selection:
{{
    "tool": "tool_name",
    "args": {{...}},
    "reasoning": "..."
}}
OR if no tool is needed:
{{
    "tool": "none",
    "response": {{
        "type": "text",
        "message": "...",
        "data": null
    }}
}}

IMPORTANT: ALWAYS respond in {preferred_lang}.
"""
            # Ask LLM to Decide
            result = self.llm.invoke([HumanMessage(content=full_prompt)])
            decision_text = result.content
            
            # Clean up cleanup code blocks
            match = re.search(r'```json\s*(\{.*?\})\s*```', decision_text, re.DOTALL)
            if match:
                decision_text = match.group(1)
            else:
                match = re.search(r'\{.*\}', decision_text, re.DOTALL)
                if match:
                    decision_text = match.group(0)

            decision = json.loads(decision_text)
            
            # Execute logic
            final_response = {}
            
            if decision['tool'] == 'none':
                final_response = decision['response']
            else:
                tool_name = decision['tool']
                if tool_name in self.tool_map:
                    tool_args = decision.get('args', {})
                    if tool_name == 'get_my_orders' and user_id:
                         tool_args['user_id'] = user_id
                         
                    # Run Tool
                    tool_result = self.tool_map[tool_name].invoke(tool_args)
                    
                    if isinstance(tool_result, (list, dict)):
                        final_response = {
                            "type": "product_list" if tool_name == "find_products" else "data_view",
                            "message": f"Here is what I found for you." if preferred_lang == 'en' else "Esto es lo que encontré por usted." if preferred_lang == 'es' else "Voici ce que j'ai trouvé pour vous.",
                            "data": tool_result
                        }
                        if tool_name == "find_products":
                             final_response["data"] = {"items": tool_result}
                    else:
                        final_response = {
                            "type": "text",
                            "message": str(tool_result),
                            "data": None
                        }
                else:
                    final_response = {
                        "type": "text",
                        "message": "Sorry, I tried to use a tool I don't have." if preferred_lang == 'en' else "Lo siento, intenté usar una herramienta que no tengo.",
                        "data": None
                    }

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
