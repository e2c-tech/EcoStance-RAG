"""
Generic Agent Service
A simplified agent that only uses RAG and basic DB tools.
"""
import logging
import json
import re
from typing import List, Dict, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from .config import AGENT_MODEL, GOOGLE_API_KEY, GROQ_API_KEY, LLM_PROVIDER, AGENT_TEMPERATURE
from .tools.kb_tools import create_search_knowledge_base_tool, create_list_knowledge_bases_tool
from .tools.db_tools import create_db_query_tool, create_list_db_tables_tool

logger = logging.getLogger(__name__)

from app.services.multilingual_utils import MultilingualAgentMixin

logger = logging.getLogger(__name__)

GENERIC_SYSTEM_PROMPTS = {
    "en": """You are a helpful AI Assistant for {company_name}.
Your goal is to answer questions using the available knowledge base and database.
Respond in the same language as the customer's question.

GUIDELINES:
1. Use `search_knowledge_base` to find info in documents (FAQs, policies, etc.)
2. Use `list_database_tables` to see which tables are available in the SQL database.
3. Use `query_database` for structured data if you know the schema.
4. Be concise and professional.
5. If you don't know the answer, say so.
""",
    "es": """Eres un Asistente de IA servicial para {company_name}.
Tu objetivo es responder preguntas utilizando la base de conocimientos y la base de datos disponibles.
Responde en el mismo idioma que la pregunta del cliente.

PAUTAS:
1. Usa `search_knowledge_base` para buscar información en documentos.
2. Usa `query_database` para datos estructurados si conoces el esquema.
3. Sé conciso y profesional.
""",
    "fr": """Vous êtes un assistant IA serviable pour {company_name}.
Votre objectif est de répondre aux questions en utilisant la base de connaissances et la base de données disponibles.
Répondez dans la même langue que la question du client.

DIRECTIVES:
1. Utilisez `search_knowledge_base` pour trouver des informations dans les documents.
2. Utilisez `query_database` pour les données structurées si vous connaissez le schéma.
3. Soyez concis et professionnel.
"""
}

# Strict whitelist of allowed tools for Generic agent
SAFE_GENERIC_TOOLS = {"knowledge_base", "database_query"}

class GenericAgentService(MultilingualAgentMixin):
    def __init__(self, tenant_id: str = None, company_name: str = "Common Assistant", allowed_tools: List[str] = None, custom_system_prompt: str = None, **kwargs):
        # Use custom prompt if provided, otherwise default to neutral generic prompts
        system_prompts = GENERIC_SYSTEM_PROMPTS.copy()
        if custom_system_prompt:
            # For Enterprise: Use the custom prompt as the English default
            system_prompts["en"] = custom_system_prompt
        else:
            # Format generic prompts with company name
            for lang in system_prompts:
                system_prompts[lang] = system_prompts[lang].format(company_name=company_name)
            
        super().__init__(system_prompts=system_prompts)
        
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
        self.company_name = company_name
        
        # Validate allowed tools
        requested_tools = allowed_tools if allowed_tools is not None else ["knowledge_base", "database_query"]
        self.allowed_tools = [t for t in requested_tools if t in SAFE_GENERIC_TOOLS]
        
        if not self.allowed_tools:
            logger.warning(f"No safe tools found for Generic agent in: {requested_tools}. Using default tools.")
            self.allowed_tools = ["knowledge_base"] # Always fallback to KB at least

        # Build tools list with validation
        self.tools = []
        
        # Add KB tools if white-listed
        if "knowledge_base" in self.allowed_tools:
            self.tools.extend([
                create_search_knowledge_base_tool(tenant_id),
                create_list_knowledge_bases_tool(tenant_id)
            ])
        
        # Add DB tools if white-listed
        if "database_query" in self.allowed_tools:
            db_path = kwargs.get('database_connection')
            # Always add tools, they handle fallback to global active connection themselves
            self.tools.extend([
                create_db_query_tool(db_path, tenant_id=tenant_id),
                create_list_db_tables_tool(db_path, tenant_id=tenant_id)
            ])
             
        self.tool_map = {tool.name: tool for tool in self.tools}
        self.conversations: Dict[str, List[Dict]] = {}

    def chat(self, session_id: str, message: str, user_language: str = None, **kwargs) -> Dict:
        try:
            # Language Detection
            detected_lang, preferred_lang, confidence = self.get_language_context(
                message, session_id, user_language
            )

            if session_id not in self.conversations:
                self.conversations[session_id] = []
            
            self.conversations[session_id].append({"role": "user", "content": message})
            
            # Get language-specific system prompt
            system_prompt = self.get_system_prompt(preferred_lang)
            
            tool_descriptions = "\n".join([f"- {t.name}: {t.description}" for t in self.tools])
            
            full_prompt = f"""{system_prompt}

Tools:
{tool_descriptions}

Query: "{message}"
Detected Language: {detected_lang}
Preferred Response Language: {preferred_lang}

Respond with ONLY the JSON selection:
{{
    "tool": "tool_name",
    "args": {{...}},
    "reasoning": "..."
}}
OR:
{{
    "tool": "none",
    "response": "..."
}}

IMPORTANT: ALWAYS respond in {preferred_lang}.
"""
            result = self.llm.invoke([HumanMessage(content=full_prompt)])
            text = result.content
            
            # Parsing logic
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                decision = json.loads(match.group(0))
                tool_name = decision.get('tool')
                
                if tool_name == 'none':
                    res_text = decision.get('response', "Hello! How can I help?")
                    return {
                        "response": res_text, 
                        "session_id": session_id, 
                        "language": preferred_lang,
                        "success": True
                    }
                
                if tool_name in self.tool_map:
                    args = decision.get('args', {})
                    tool_result = self.tool_map[tool_name].invoke(args)
                    return {
                        "response": str(tool_result), 
                        "session_id": session_id, 
                        "language": preferred_lang,
                        "success": True, 
                        "tool_used": tool_name
                    }
            
            return {
                "response": text, 
                "session_id": session_id, 
                "language": preferred_lang,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Generic Agent Error: {e}")
            return {"response": "Sorry, an error occurred.", "session_id": session_id, "success": False, "error": str(e)}

    def get_conversation_history(self, session_id: str) -> List[Dict]:
        return self.conversations.get(session_id, [])

    def reset_conversation(self, session_id: str) -> bool:
        if session_id in self.conversations:
            del self.conversations[session_id]
            self.language_service.clear_session_language(session_id)
            return True
        return False
