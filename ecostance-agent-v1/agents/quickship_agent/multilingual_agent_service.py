"""
Multilingual Agent Service for QuickShip Logistics
Parallel implementation with language-aware conversational AI
"""

import re
import json
import logging
import time
from typing import List, Dict, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.config.multilingual_app_config import (
    should_use_multilingual_service,
    is_tenant_multilingual_enabled
)
from app.services.language_service import get_language_service
from .services.multilingual_rag_service import get_multilingual_rag_service
from .config import LLM_PROVIDER, AGENT_MODEL, AGENT_TEMPERATURE, GROQ_MODELS, GEMINI_MODELS
from app.services.query_service import get_llm

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
from .tools.multilingual_kb_tools import (
    create_multilingual_search_tool,
    create_multilingual_list_tool,
    create_language_detection_tool,
    create_cross_language_search_tool
)

logger = logging.getLogger(__name__)

# Multilingual system prompts
MULTILINGUAL_SYSTEM_PROMPTS = {
    "en": """You are QuickShip's helpful and professional customer service agent with multilingual capabilities.

Your role:
- Help customers track their shipments in their preferred language
- Provide delivery estimates and payment information
- Answer questions about policies and procedures using multilingual knowledge base
- Always respond in the same language as the customer's question
- Be polite, professional, and culturally appropriate

Guidelines:
1. Detect the customer's language and respond in the same language
2. If customer doesn't provide shipment ID, politely ask for phone number, email, or tracking number
3. Use multilingual knowledge base search for policies, rates, and procedures
4. NEVER make up information - only use data returned by the tools
5. For cross-language information, synthesize content from multiple languages appropriately
6. Maintain cultural sensitivity in responses
7. **NO RAW DATA**: Do not just repeat raw database rows or tracking logs. Summarize the shipment status and information in a helpful, conversational way.

Available Tools:
**Shipment & Database Tools:** (same as before)
**Multilingual Knowledge Base Tools:**
- search_multilingual_knowledge_base(kb_name, query, user_language): Search with cross-language capabilities
- list_multilingual_knowledge_bases(): List available knowledge bases
- detect_text_language(text): Detect language of text
- cross_language_search(kb_name, query): Search across multiple languages

Remember: Always respond in the customer's language and end with appropriate closing in that language.""",

    "es": """Eres el agente de servicio al cliente útil y profesional de QuickShip con capacidades multilingües.

Tu función:
- Ayudar a los clientes a rastrear sus envíos en su idioma preferido
- Proporcionar estimaciones de entrega e información de pagos
- Responder preguntas sobre políticas y procedimientos usando la base de conocimientos multilingüe
- Siempre responder en el mismo idioma que la pregunta del cliente
- Ser cortés, profesional y culturalmente apropiado

Pautas:
1. Detecta el idioma del cliente y responde en el mismo idioma
2. Si el cliente no proporciona ID de envío, pregunta cortésmente por teléfono, email o número de seguimiento
3. Usa la búsqueda multilingüe para políticas, tarifas y procedimientos
4. NUNCA inventes información - solo usa datos devueltos por las herramientas
5. Para información en varios idiomas, sintetiza el contenido apropiadamente
6. Mantén sensibilidad cultural en las respuestas

Recuerda: Siempre responde en el idioma del cliente y termina con un cierre apropiado en ese idioma.""",

    "fr": """Vous êtes l'agent de service client utile et professionnel de QuickShip avec des capacités multilingues.

Votre rôle:
- Aider les clients à suivre leurs expéditions dans leur langue préférée
- Fournir des estimations de livraison et des informations de paiement
- Répondre aux questions sur les politiques et procédures en utilisant la base de connaissances multilingue
- Toujours répondre dans la même langue que la question du client
- Être poli, professionnel et culturellement approprié

Directives:
1. Détectez la langue du client et répondez dans la même langue
2. Si le client ne fournit pas d'ID d'expédition, demandez poliment le téléphone, l'email ou le numéro de suivi
3. Utilisez la recherche multilingue pour les politiques, tarifs et procédures
4. NE JAMAIS inventer d'informations - utilisez seulement les données retournées par les outils
5. Pour les informations multi-langues, synthétisez le contenu de manière appropriée
6. Maintenez la sensibilité culturelle dans les réponses

Rappelez-vous: Répondez toujours dans la langue du client et terminez par une conclusion appropriée dans cette langue."""
}

# Strict whitelist for multilingual agent tools
SAFE_MULTILINGUAL_CATEGORIES = {
    "tracking", "customer_search", "payments", "complaints", "delivery_estimates", 
    "knowledge_base", "language_detection"
}

class MultilingualAgentService:
    """Multilingual agent service with language-aware capabilities."""
    
    def __init__(self, tenant_id: str = None, db_session=None, llm_provider: str = None, 
                 model: str = None, allowed_tools: List[str] = None):
        self.tenant_id = tenant_id
        self.db_session = db_session
        
        # Validate allowed tools
        requested_tools = allowed_tools if allowed_tools is not None else list(SAFE_MULTILINGUAL_CATEGORIES)
        self.allowed_tools = [t for t in requested_tools if t in SAFE_MULTILINGUAL_CATEGORIES]
        
        if not self.allowed_tools:
            logger.warning(f"No safe tools found for Multilingual agent: {requested_tools}. Using default set.")
            self.allowed_tools = ["tracking", "knowledge_base", "language_detection"]

        # Check if multilingual features should be used
        self.use_multilingual = should_use_multilingual_service(tenant_id)
        
        if not self.use_multilingual:
            logger.info(f"Multilingual features not enabled for tenant {tenant_id}, using legacy service")
            # Could fall back to legacy agent service here
            raise ValueError("Multilingual features not enabled for this tenant")
        
        # Initialize services
        self.language_service = get_language_service()
        self.rag_service = get_multilingual_rag_service()
        
        # Create LLM using shared utility
        try:
            self.llm = get_llm(
                provider=llm_provider,
                model=model,
                temperature=AGENT_TEMPERATURE
            )
            self.current_provider = llm_provider or LLM_PROVIDER
            self.current_model = model or AGENT_MODEL
            logger.info(f"Initialized MultilingualAgentService with {self.current_provider} provider, model: {self.current_model}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            # Fallback to Gemini if available
            try:
                self.llm = get_llm(provider="gemini")
                self.current_provider = "gemini"
                self.current_model = AGENT_MODEL
                logger.warning("Fell back to Gemini provider")
            except Exception as fallback_error:
                logger.error(f"Fallback to Gemini also failed: {fallback_error}")
                raise ValueError("No LLM provider could be initialized. Please check your API keys.")
        
        # Build validated tool list
        self.tools = []
        
        # Shipment/DB Tools
        if "tracking" in self.allowed_tools:
            self.tools.extend([get_shipment_status, track_by_tracking_number])
        if "customer_search" in self.allowed_tools:
            self.tools.append(search_shipments_by_customer)
        if "delivery_estimates" in self.allowed_tools:
            self.tools.append(get_delivery_estimate)
        if "payments" in self.allowed_tools:
            self.tools.append(check_cod_payment_status)
        if "complaints" in self.allowed_tools:
            self.tools.append(get_complaint_status)
            
        # Multilingual Tools
        if tenant_id:
            if "knowledge_base" in self.allowed_tools:
                self.tools.extend([
                    create_multilingual_search_tool(tenant_id),
                    create_multilingual_list_tool(tenant_id),
                    create_cross_language_search_tool(tenant_id)
                ])
            if "language_detection" in self.allowed_tools:
                self.tools.append(create_language_detection_tool())
        
        # Create a tool map for easy lookup
        self.tool_map = {tool.name: tool for tool in self.tools}
        
        # Store conversations by session_id with language info
        self.conversations: Dict[str, Dict] = {}  # session_id -> {messages: [], language: str}
    
    def _get_system_prompt(self, language: str) -> str:
        """Get system prompt in the appropriate language."""
        # Use language-specific prompt if available, otherwise use English
        return MULTILINGUAL_SYSTEM_PROMPTS.get(language, MULTILINGUAL_SYSTEM_PROMPTS["en"])
    
    def _get_tool_descriptions(self, language: str = "en") -> str:
        """Generate tool descriptions for the LLM in the appropriate language."""
        descriptions = []
        for tool in self.tools:
            desc = f"- {tool.name}: {tool.description}"
            descriptions.append(desc)
        return "\n".join(descriptions)
    
    def _is_out_of_scope(self, message: str, language: str = "en") -> bool:
        """Check if query is out of scope (not related to logistics)."""
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
        
        # Add language-specific indicators
        if language == "es":
            out_of_scope_indicators.extend([
                'escribir código', 'código python', 'programar', 'función',
                'clima', 'noticias', 'receta', 'película', 'canción',
                'chiste', 'historia', 'poema', 'traducir', 'calcular'
            ])
        elif language == "fr":
            out_of_scope_indicators.extend([
                'écrire du code', 'code python', 'programmer', 'fonction',
                'météo', 'nouvelles', 'recette', 'film', 'chanson',
                'blague', 'histoire', 'poème', 'traduire', 'calculer'
            ])
        
        return any(indicator in message_lower for indicator in out_of_scope_indicators)
    
    def _get_out_of_scope_message(self, language: str) -> str:
        """Get out-of-scope message in the appropriate language."""
        messages = {
            "en": """I'm sorry, but I can't help with that. I'm a QuickShip logistics assistant specialized in:

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

Is there anything related to shipments or logistics I can help you with?""",

            "es": """Lo siento, pero no puedo ayudar con eso. Soy un asistente de logística de QuickShip especializado en:

📦 **Seguimiento de Envíos:**
- Rastrear envíos por ID (ej., "Rastrear QS250001")
- Verificar estado de entrega y estimaciones
- Ver estado de pagos y COD
- Verificar quejas

📚 **Información de la Empresa:**
- Tarifas y costos de envío
- Tiempos de entrega
- Servicios de recogida
- Políticas y procedimientos

**Intenta preguntar:**
- "¿Cuáles son sus tarifas de envío?"
- "Rastrear QS250001"
- "¿Cuánto tiempo toma la entrega?"
- "Mi teléfono es 9224217802, muestra mis pedidos"

¿Hay algo relacionado con envíos o logística en lo que pueda ayudarte?""",

            "fr": """Je suis désolé, mais je ne peux pas aider avec cela. Je suis un assistant logistique QuickShip spécialisé dans:

📦 **Suivi des Expéditions:**
- Suivre les expéditions par ID (ex., "Suivre QS250001")
- Vérifier le statut de livraison et les estimations
- Voir le statut des paiements et COD
- Vérifier les plaintes

📚 **Informations de l'Entreprise:**
- Tarifs et coûts d'expédition
- Délais de livraison
- Services de collecte
- Politiques et procédures

**Essayez de demander:**
- "Quels sont vos tarifs d'expédition?"
- "Suivre QS250001"
- "Combien de temps prend la livraison?"
- "Mon téléphone est 9224217802, montrez mes commandes"

Y a-t-il quelque chose lié aux expéditions ou à la logistique avec lequel je peux vous aider?"""
        }
        
        return messages.get(language, messages["en"])
    
    @traceable(name="multilingual_llm_call")
    def _invoke_llm_with_tracing(self, prompt: str, session_id: str, language: str):
        """Invoke LLM with LangSmith tracing and language context."""
        # Add language-specific tags
        tags = ["multilingual_llm", self.current_provider, f"lang_{language}"]
        return self.llm.invoke([HumanMessage(content=prompt)])
    
    @traceable(name="multilingual_agent_conversation", tags=["multilingual_agent", "conversation"])
    def chat(self, session_id: str, message: str, knowledge_base: str = None, 
             database_connection: str = None, user_language: str = None) -> Dict:
        """
        Process a chat message using multilingual ReAct pattern.
        
        Args:
            session_id: Unique session identifier
            message: User message
            knowledge_base: Optional knowledge base name to search
            database_connection: Optional database connection name
            user_language: Optional user's preferred language
            
        Returns:
            Dict with response and metadata including language information
        """
        try:
            # Detect message language
            detected_language, confidence = self.language_service.detect_language(
                message, return_confidence=True
            )
            
            # Determine preferred language
            preferred_language = self.language_service.get_preferred_language(
                session_id=session_id,
                detected_language=detected_language
            )
            
            # Use user-specified language if provided
            if user_language:
                preferred_language = user_language
            
            # Store language preference for session
            self.language_service.set_session_language(session_id, preferred_language)
            
            logger.info(f"Multilingual chat - Session: {session_id}, "
                       f"Detected: {detected_language} ({confidence:.2f}), "
                       f"Preferred: {preferred_language}")
            
            # Initialize conversation history if new session
            if session_id not in self.conversations:
                self.conversations[session_id] = {
                    "messages": [],
                    "language": preferred_language
                }
            
            # Update session language if changed
            self.conversations[session_id]["language"] = preferred_language
            
            # Store selected knowledge base and database for this session
            if not hasattr(self, 'session_kb'):
                self.session_kb = {}
            if knowledge_base:
                self.session_kb[session_id] = knowledge_base
            
            if not hasattr(self, 'session_db'):
                self.session_db = {}
            if database_connection:
                self.session_db[session_id] = database_connection
            
            # Add user message to history
            self.conversations[session_id]["messages"].append({
                "role": "user",
                "content": message,
                "language": detected_language,
                "confidence": confidence
            })
            
            # Check if query is out of scope
            if self._is_out_of_scope(message, preferred_language):
                out_of_scope_msg = self._get_out_of_scope_message(preferred_language)
                
                self.conversations[session_id]["messages"].append({
                    "role": "assistant",
                    "content": out_of_scope_msg,
                    "language": preferred_language
                })
                
                return {
                    "response": out_of_scope_msg,
                    "session_id": session_id,
                    "language": preferred_language,
                    "detected_language": detected_language,
                    "confidence": confidence,
                    "success": True
                }
            
            # Build context about selected KB and DB
            context_info = ""
            if session_id in self.session_kb:
                context_info += f"\n\nIMPORTANT: User has selected knowledge base '{self.session_kb[session_id]}'. If you need to search knowledge base, you MUST use kb_name='{self.session_kb[session_id]}'."
            if session_id in self.session_db:
                context_info += f"\n\nDatabase connection: {self.session_db[session_id]}"
            
            # Get language-appropriate system prompt
            system_prompt = self._get_system_prompt(preferred_language)
            
            max_iterations = 5
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                is_last_turn = (iteration == max_iterations)
                
                # Use LLM to analyze query and decide which tool to use
                analysis_prompt = f"""{system_prompt}

Analyze the customer query and previous tool results to determine your next action.

### CONTEXT:
Query: "{message}"
Detected Language: {detected_language}
Preferred Response Language: {preferred_language}{context_info}
Turn: {iteration}/{max_iterations}

### AVAILABLE TOOLS:
{self._get_tool_descriptions(preferred_language)}

### INSTRUCTIONS:
1. Respond with ONLY a JSON object.
2. DO NOT include any text outside the JSON.
3. DO NOT simulate tool results or "TOOL_RESULT" blocks.
4. If you need data (shipment status, policies), call the appropriate tool.
5. If you have the tool result, explain it politely to the customer in {preferred_language}.
6. Do NOT just return the raw tool result. Provide a helpful, human-friendly summary.
7. If the user asks about something out of scope, explain what you CAN do.

FORMAT:
{{
    "tool": "tool_name",
    "args": {{...}},
    "reasoning": "why this tool",
    "response_language": "{preferred_language}"
}}
OR (if finished):
{{
    "tool": "none",
    "response": "your human-friendly final response in {preferred_language}",
    "response_language": "{preferred_language}"
}}

{ "CRITICAL: This is your LAST turn. You MUST provide the final response now." if is_last_turn else "" }
"""
                
                logger.info(f"Asking Multilingual LLM turn {iteration}: {message[:50]}...")
                
                # Build message list for history-aware reasoning (optional but good)
                # For now keeping it simple like the previous implementation but in a loop
                
                # Track LLM call
                start_time = time.time()
                analysis_response = self._invoke_llm_with_tracing(analysis_prompt, session_id, preferred_language)
                latency_ms = int((time.time() - start_time) * 1000)
                
                analysis_text = analysis_response.content if hasattr(analysis_response, 'content') else str(analysis_response)
                
                # Robust JSON extraction
                json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
                decision = None
                if json_match:
                    json_str = json_match.group(0)
                    try:
                        decision = json.loads(json_str)
                    except json.JSONDecodeError:
                        first_match = re.search(r'\{.*?\}', analysis_text, re.DOTALL)
                        if first_match:
                            try:
                                decision = json.loads(first_match.group(0))
                            except: pass

                if not decision:
                     # Non-JSON response: treating as final
                    self.conversations[session_id]["messages"].append({
                        "role": "assistant",
                        "content": analysis_text,
                        "language": preferred_language
                    })
                    return {
                        "response": analysis_text,
                        "session_id": session_id,
                        "language": preferred_language,
                        "success": True
                    }

                tool_name = decision.get('tool')
                response_language = decision.get('response_language', preferred_language)
                
                # If no tool needed, or last turn, return direct response
                if tool_name == 'none' or not tool_name or is_last_turn:
                    response_text = decision.get('response', decision.get('reasoning', analysis_text))
                    
                    self.conversations[session_id]["messages"].append({
                        "role": "assistant",
                        "content": response_text,
                        "language": response_language
                    })
                    
                    return {
                        "response": response_text,
                        "session_id": session_id,
                        "language": response_language,
                        "detected_language": detected_language,
                        "confidence": confidence,
                        "success": True
                    }
                
                # Execute the tool
                if tool_name in self.tool_map:
                    tool = self.tool_map[tool_name]
                    tool_args = decision.get('args', {})
                    
                    # Add language context to multilingual tools
                    if 'multilingual' in tool_name or 'language' in tool_name:
                        if 'user_language' not in tool_args:
                            tool_args['user_language'] = preferred_language
                    
                    # Handle KB selection logic
                    if tool_name == 'search_multilingual_knowledge_base':
                        ui_selected_kb = self.session_kb.get(session_id)
                        if ui_selected_kb:
                            tool_args['kb_name'] = ui_selected_kb
                        elif not tool_args.get('kb_name'):
                            kb_msg = self._get_kb_selection_message(preferred_language)
                            self.conversations[session_id]["messages"].append({
                                "role": "assistant", "content": kb_msg, "language": preferred_language
                            })
                            return {"response": kb_msg, "session_id": session_id, "success": True}

                    logger.info(f"Executing multilingual tool: {tool_name}")
                    
                    # Add assistant's thought to message list so next iteration sees it
                    self.conversations[session_id]["messages"].append({
                        "role": "assistant",
                        "content": json.dumps(decision),
                        "language": response_language
                    })

                    try:
                        result = tool.invoke(tool_args)
                        # Add tool result to context for next iteration
                        context_info += f"\n\nTOOL_RESULT ({tool_name}): {str(result)}"
                        
                        self.conversations[session_id]["messages"].append({
                            "role": "system",
                            "content": f"TOOL_RESULT ({tool_name}): {str(result)}",
                            "tool_used": tool_name
                        })
                    except Exception as e:
                        error_msg = f"Error executing tool {tool_name}: {str(e)}"
                        context_info += f"\n\n{error_msg}"
                        self.conversations[session_id]["messages"].append({
                            "role": "system", "content": error_msg
                        })
                else:
                    error_msg = f"Tool '{tool_name}' not found."
                    context_info += f"\n\n{error_msg}"
                    self.conversations[session_id]["messages"].append({
                        "role": "system", "content": error_msg
                    })
            
        except Exception as e:
            logger.error(f"Error in multilingual agent chat: {e}", exc_info=True)
            error_response = self._get_general_error_message(preferred_language if 'preferred_language' in locals() else "en")
            
            if session_id in self.conversations:
                self.conversations[session_id]["messages"].append({
                    "role": "assistant",
                    "content": error_response,
                    "language": preferred_language if 'preferred_language' in locals() else "en"
                })
            
            return {
                "response": error_response,
                "session_id": session_id,
                "language": preferred_language if 'preferred_language' in locals() else "en",
                "detected_language": detected_language if 'detected_language' in locals() else "unknown",
                "confidence": confidence if 'confidence' in locals() else 0.0,
                "success": False,
                "error": str(e)
            }
    
    def _get_kb_selection_message(self, language: str) -> str:
        """Get knowledge base selection message in appropriate language."""
        messages = {
            "en": "To search our knowledge base, please select a knowledge base from the sidebar first.",
            "es": "Para buscar en nuestra base de conocimientos, primero selecciona una base de conocimientos de la barra lateral.",
            "fr": "Pour rechercher dans notre base de connaissances, veuillez d'abord sélectionner une base de connaissances dans la barre latérale."
        }
        return messages.get(language, messages["en"])
    
    def _get_error_message(self, error: str, language: str) -> str:
        """Get error message in appropriate language."""
        messages = {
            "en": f"I encountered an error while processing your request: {error}",
            "es": f"Encontré un error al procesar tu solicitud: {error}",
            "fr": f"J'ai rencontré une erreur lors du traitement de votre demande: {error}"
        }
        return messages.get(language, messages["en"])
    
    def _get_tool_not_found_message(self, tool_name: str, language: str) -> str:
        """Get tool not found message in appropriate language."""
        messages = {
            "en": f"Tool '{tool_name}' not found",
            "es": f"Herramienta '{tool_name}' no encontrada",
            "fr": f"Outil '{tool_name}' non trouvé"
        }
        return messages.get(language, messages["en"])
    
    def _get_fallback_message(self, language: str) -> str:
        """Get fallback message in appropriate language."""
        messages = {
            "en": "I'm not sure how to help with that. Could you please rephrase your question?",
            "es": "No estoy seguro de cómo ayudar con eso. ¿Podrías reformular tu pregunta?",
            "fr": "Je ne suis pas sûr de pouvoir vous aider avec cela. Pourriez-vous reformuler votre question?"
        }
        return messages.get(language, messages["en"])
    
    def _get_general_error_message(self, language: str) -> str:
        """Get general error message in appropriate language."""
        messages = {
            "en": "I apologize, but I encountered an error. Please try again or contact support.",
            "es": "Me disculpo, pero encontré un error. Por favor intenta de nuevo o contacta soporte.",
            "fr": "Je m'excuse, mais j'ai rencontré une erreur. Veuillez réessayer ou contacter le support."
        }
        return messages.get(language, messages["en"])
    
    def get_conversation_history(self, session_id: str) -> List[Dict]:
        """Get conversation history for a session with language information."""
        session_data = self.conversations.get(session_id, {"messages": []})
        return session_data["messages"]
    
    def reset_conversation(self, session_id: str) -> bool:
        """Reset conversation history for a session."""
        if session_id in self.conversations:
            del self.conversations[session_id]
            self.language_service.clear_session_language(session_id)
            return True
        return False
    
    def get_session_language(self, session_id: str) -> Optional[str]:
        """Get the current language for a session."""
        session_data = self.conversations.get(session_id, {})
        return session_data.get("language")
    
    def switch_llm_provider(self, provider: str, model: str = None) -> Dict:
        """Switch to a different LLM provider (same as original but with multilingual context)."""
        try:
            is_valid, error_msg = LLMFactory.validate_provider_config(provider)
            if not is_valid:
                return {
                    "success": False,
                    "message": f"Cannot switch to {provider}: {error_msg}"
                }
            
            old_provider = self.current_provider
            old_model = self.current_model
            
            self.llm = LLMFactory.create_llm(
                provider=provider,
                model=model,
                temperature=AGENT_TEMPERATURE
            )
            
            self.current_provider = provider
            self.current_model = model or (GROQ_MODELS[0] if provider == "groq" else AGENT_MODEL)
            
            logger.info(f"Switched multilingual LLM from {old_provider}:{old_model} to {self.current_provider}:{self.current_model}")
            
            return {
                "success": True,
                "message": f"Successfully switched to {self.current_provider} with model {self.current_model}",
                "previous_provider": old_provider,
                "previous_model": old_model,
                "current_provider": self.current_provider,
                "current_model": self.current_model
            }
            
        except Exception as e:
            logger.error(f"Failed to switch multilingual LLM provider: {e}")
            return {
                "success": False,
                "message": f"Failed to switch to {provider}: {str(e)}"
            }
    
    def get_current_llm_info(self) -> Dict:
        """Get information about the current LLM configuration."""
        return {
            "provider": self.current_provider,
            "model": self.current_model,
            "temperature": AGENT_TEMPERATURE,
            "available_providers": LLMFactory.get_available_providers(),
            "multilingual_enabled": True,
            "supported_languages": ["en", "es", "fr", "de", "pt", "it", "nl", "ru", "zh", "ja"]
        }