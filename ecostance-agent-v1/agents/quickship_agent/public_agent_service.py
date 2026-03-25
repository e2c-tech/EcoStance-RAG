import logging
import json
import re
from typing import List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from .config import GOOGLE_API_KEY, GROQ_API_KEY, AGENT_MODEL, AGENT_TEMPERATURE, LLM_PROVIDER
from .tools.database_tools import TOOL_CATEGORIES
from .tools.knowledge_base_tools import (
    create_search_knowledge_base_tool,
    create_list_knowledge_bases_tool
)
from app.services.multilingual_utils import MultilingualAgentMixin

logger = logging.getLogger(__name__)

# Multilingual system prompts for Logistics Agent
LOGISTICS_SYSTEM_PROMPTS = {
    "en": """You are a helpful customer service agent for QuickShip logistics.

Your role:
- Help customers track their shipments
- Provide delivery information
- Answer questions about payments
- Check complaint status
- Always be polite, professional, and empathetic

Guidelines:
1. If customer doesn't provide shipment ID, politely ask for phone number, email, or tracking number
2. Use the available tools to get accurate information from the database
3. NEVER make up information - only use data returned by the tools
4. Always respond in the same language as the customer.

Available Tools:
{tool_descriptions}

Remember:
- Shipment IDs: QS250XXX
- Tracking numbers: TRKXXXXXXXXX
- Always end with: "Is there anything else I can help you with?"
""",
    "es": """Eres un agente de servicio al cliente útil para la logística de QuickShip.

Tu función:
- Ayudar a los clientes a rastrear sus envíos
- Proporcionar información de entrega
- Responder preguntas sobre pagos
- Verificar el estado de las quejas
- Siempre ser cortés, profesional y empático

Pautas:
1. Si el cliente no proporciona el ID del envío, pida cortésmente el número de teléfono, correo electrónico o número de seguimiento.
2. Use las herramientas disponibles para obtener información precisa de la base de datos.
3. NUNCA invente información - use solo los datos devueltos por las herramientas.
4. Responda siempre en el mismo idioma que el cliente.
""",
    "fr": """Vous êtes un agent de service client serviable pour la logistique QuickShip.

Votre rôle:
- Aider les clients à suivre leurs expéditions
- Fournir des informations de livraison
- Répondre aux questions sur les paiements
- Vérifier le statut des plaintes
- Soyez toujours poli, professionnel et empathique

Directives:
1. Si le client ne fournit pas d'ID d'expédition, demandez poliment le numéro de téléphone, l'e-mail ou le numéro de suivi.
2. Utilisez les outils disponibles pour obtenir des informations précises à partir de la base de données.
3. Ne JAMAIS inventer d'informations - utilisez uniquement les données renvoyées par les outils.
4. Répondez toujours dans la même langue que le client.
"""
}

# Strict whitelist of allowed tool categories for runtime validation
SAFE_TOOL_CATEGORIES = {"tracking", "payments", "complaints", "delivery_estimates", "knowledge_base"}

class PublicAgentService(MultilingualAgentMixin):
    """Service for managing public agent conversations with restricted tool access"""
    
    def __init__(self, tenant_id: str = None, allowed_tools: List[str] = None, **kwargs):
        super().__init__(system_prompts=LOGISTICS_SYSTEM_PROMPTS)
        
        if LLM_PROVIDER == "groq":
            from langchain_groq import ChatGroq
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
        
        # Validate allowed_tools against whitelist
        requested_tools = allowed_tools if allowed_tools is not None else ["tracking", "payments", "complaints", "delivery_estimates"]
        self.allowed_tools = [t for t in requested_tools if t in SAFE_TOOL_CATEGORIES]
        
        if not self.allowed_tools:
             logger.warning(f"No safe tools found in requested list: {requested_tools}. Falling back to defaults.")
             self.allowed_tools = ["tracking", "payments", "complaints", "delivery_estimates"]
        
        # Build tool list based on allowed categories
        self.tools = self._build_tool_list()
        
        # Create a tool map for easy lookup
        self.tool_map = {tool.name: tool for tool in self.tools}
        
        # Store conversations by session_id
        self.conversations: Dict[str, List[Dict]] = {}
    
    def _build_tool_list(self) -> List:
        """Build list of tools based on allowed categories with strict validation"""
        tools = []
        
        # Add database tools based on validated categories
        for category in self.allowed_tools:
            if category in TOOL_CATEGORIES and category in SAFE_TOOL_CATEGORIES:
                tools.extend(TOOL_CATEGORIES[category])
        
        # Add KB tools if white-listed and tenant_id is provided
        if "knowledge_base" in self.allowed_tools and self.tenant_id:
            kb_tools = [
                create_search_knowledge_base_tool(self.tenant_id),
                create_list_knowledge_bases_tool(self.tenant_id)
            ]
            tools.extend(kb_tools)
        
        logger.info(f"Built validated tool list with {len(tools)} tools for categories: {self.allowed_tools}")
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
            
            # Add user message to history
            self.conversations[session_id].append({
                "role": "user",
                "content": message
            })
            
            # Check if query is out of scope
            if self._is_out_of_scope(message):
                out_of_scope_msg = self._get_out_of_scope_message(preferred_lang)
                
                self.conversations[session_id].append({
                    "role": "assistant",
                    "content": out_of_scope_msg
                })
                
                return {
                    "response": out_of_scope_msg,
                    "session_id": session_id,
                    "language": preferred_lang,
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
            system_prompt = self.get_system_prompt(preferred_lang).format(tool_descriptions=tool_descriptions)
            
            analysis_prompt = f"""{system_prompt}

Query: "{message}"{context_info}
Detected Language: {detected_lang}
Preferred Response Language: {preferred_lang}

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

IMPORTANT: ALWAYS respond in {preferred_lang}."""
            
            logger.info(f"Asking LLM to analyze query: {message}")
            analysis_response = self.llm.invoke([HumanMessage(content=analysis_prompt)])
            analysis_text = analysis_response.content if hasattr(analysis_response, 'content') else str(analysis_response)
            
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
                    response_text = decision.get('response', "I'm here to help!")
                    
                    self.conversations[session_id].append({
                        "role": "assistant",
                        "content": response_text
                    })
                    
                    return {
                        "response": response_text,
                        "session_id": session_id,
                        "language": preferred_lang,
                        "success": True
                    }
                
                # Check if tool is allowed
                if tool_name not in self.tool_map:
                    error_msg = f"I cannot access that tool right now."
                    self.conversations[session_id].append({
                        "role": "assistant",
                        "content": error_msg
                    })
                    return {"response": error_msg, "session_id": session_id, "language": preferred_lang, "success": False}
                
                # Execute the tool
                tool = self.tool_map[tool_name]
                tool_args = decision.get('args', {})
                
                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                result = tool.invoke(tool_args)
                
                self.conversations[session_id].append({
                    "role": "assistant",
                    "content": result
                })
                
                return {
                    "response": result,
                    "session_id": session_id,
                    "language": preferred_lang,
                    "success": True,
                    "tool_used": tool_name
                }
                    
            except json.JSONDecodeError:
                fallback_msg = "I'm sorry, I process your request. Could you rephrase it?"
                return {"response": fallback_msg, "session_id": session_id, "language": preferred_lang, "success": True}
            
        except Exception as e:
            logger.error(f"Public Agent Error: {e}")
            return {"response": "An error occurred.", "session_id": session_id, "success": False, "error": str(e)}

    def _get_out_of_scope_message(self, language: str) -> str:
        messages = {
            "en": "I'm sorry, I can only help with logistics and shipments.",
            "es": "Lo siento, solo puedo ayudar con logística y envíos.",
            "fr": "Désolé, je ne peux aider qu'avec la logistique et les expéditions."
        }
        return messages.get(language, messages["en"])

    def get_conversation_history(self, session_id: str) -> List[Dict]:
        return self.conversations.get(session_id, [])

    def reset_conversation(self, session_id: str) -> bool:
        if session_id in self.conversations:
            del self.conversations[session_id]
            self.language_service.clear_session_language(session_id)
            return True
        return False
