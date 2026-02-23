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
1. Search tools (`search_knowledge_base`, `query_database`) should ONLY be used if a Knowledge Base or Database is marked as 'Active' in your context.
2. **NO RAW DATA DUMPS**: Do not simply repeat database rows, long lists of IDs (e.g., 1, 2, 3), or document snippets. Summarize findings in a professional, human-friendly way.
3. **CATEGORIZE & ANALYZE**: If you find multiple items, group them by category or importance instead of listing them all. Highlight the top 2-3 most relevant results.
4. **HUMAN-FRIENDLY NAMES**: Always prefer using names or descriptions over internal database IDs.
5. If no Knowledge Base is active and the user asks a question requiring documents, explain that they need to select a Knowledge Base first.
6. Use `list_database_tables` (to see table and column names) and then `query_database` for structured data IF a database is active.
7. Be concise and professional.
8. If you don't know the answer, say so.

### EXAMPLE OF EXPERT RESPONSE:
**User**: Which sensors detected intrusions?
**Expert Analysis**: Our records indicate that intrusions were primarily detected by the **Finance Segment IDS** and the **HR Department Perimeter Sensor**. While several other sensors logged activity, these two captured the most significant intrusion attempts.
**Recommended Action**: Review the traffic logs for the Finance and HR segments specifically.
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

    def chat(self, session_id: str, message: str, user_language: str = None, chat_history: List[Dict] = None, **kwargs) -> Dict:
        try:
            # Language Detection
            detected_lang, preferred_lang, confidence = self.get_language_context(
                message, session_id, user_language
            )

            if session_id not in self.conversations:
                self.conversations[session_id] = []
                if chat_history:
                    self.conversations[session_id].extend(chat_history)
            
            self.conversations[session_id].append({"role": "user", "content": message})
            
            # Get language-specific system prompt
            system_prompt = self.get_system_prompt(preferred_lang)
            
            # Context about selected KB and DB
            kb_name = kwargs.get('knowledge_base')
            db_conn = kwargs.get('database_connection')
            
            context_info = ""
            if kb_name:
                context_info += f"\n- Active Knowledge Base: {kb_name}. (Use this as 'kb_name' when searching)"
            if db_conn:
                context_info += f"\n- Active Database Connection: {db_conn}. Use list_database_tables first to see schema."
            else:
                context_info += "\n- No database connected. Ask user to connect one if needed."

            tool_descriptions = "\n".join([f"- {t.name}: {t.description}" for t in self.tools])
            
            max_iterations = 5
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                
                # Build prompt for current iteration
                is_last_turn = (iteration == max_iterations)
                
                turn_prompt = f"""{system_prompt}

### TOOLS:
{tool_descriptions}

### ACTIVE CONTEXT:
{context_info}

### INSTRUCTIONS:
1. You MUST respond with EXACTLY ONE valid JSON object only.
2. DO NOT include any text outside the JSON block.
3. DO NOT simulate tool results or provide multiple JSON blocks.
4. **DATABASE DISCOVERY**: If you need to query the database, you MUST call `list_database_tables` first to see the schema. NEVER guess column names.
5. **FAILURE RECOVERY**: If a SQL query fails with "no such column", you MUST call `list_database_tables` immediately.
6. If you have the data, provide a helpful human-friendly summary.

FORMAT:
{{
    "tool": "tool_name",
    "args": {{...}},
    "reasoning": "Why I am taking this action"
}}
OR (if finished):
{{
    "tool": "none",
    "response": "Your human-friendly final answer here",
    "type": "text"
}}

{ "CRITICAL: This is your LAST turn. You MUST provide the final response now." if is_last_turn else f"Turn {iteration}/{max_iterations}." }
"""
                # Build message list for LangChain
                from langchain_core.messages import SystemMessage, AIMessage
                lc_messages = [SystemMessage(content=turn_prompt)]
                
                # Add history (last 8 turns)
                for msg in self.conversations[session_id][-8:]:
                    if msg["role"] == "user":
                        lc_messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        lc_messages.append(AIMessage(content=msg["content"]))
                    elif msg["role"] == "system":
                        lc_messages.append(SystemMessage(content=msg["content"]))

                result = self.llm.invoke(lc_messages)
                text = result.content
                
                # Robust JSON extraction
                match = re.search(r'\{.*\}', text, re.DOTALL)
                decision = None
                if match:
                    json_str = match.group(0)
                    try:
                        decision = json.loads(json_str)
                    except json.JSONDecodeError:
                        first_match = re.search(r'\{.*?\}', text, re.DOTALL)
                        if first_match:
                            try:
                                decision = json.loads(first_match.group(0))
                            except: pass

                if not decision:
                    self.conversations[session_id].append({"role": "assistant", "content": text})
                    return {"response": text, "session_id": session_id, "language": preferred_lang, "success": True}

                tool_name = decision.get('tool')
                
                if tool_name == 'none' or not tool_name or is_last_turn:
                    res_text = decision.get('response', decision.get('reasoning', text))
                    self.conversations[session_id].append({"role": "assistant", "content": res_text})
                    return {
                        "response": res_text, 
                        "session_id": session_id, 
                        "language": preferred_lang,
                        "success": True
                    }
                
                if tool_name in self.tool_map:
                    args = decision.get('args', {})
                    
                    # STRICT SELECTION ENFORCEMENT
                    if tool_name in ["query_database", "list_database_tables"]:
                         if not db_conn:
                              from app.routers import db_router
                              if not (db_router.db_connector and (db_router.db_connector.engine or db_router.db_connector.client)):
                                   err_msg = "A database tool was called but no Database is currently active. Please connect a database first."
                                   self.conversations[session_id].append({"role": "assistant", "content": err_msg})
                                   return {"response": err_msg, "session_id": session_id, "success": True}

                    # Intercept KB search if no active selection
                    if tool_name == 'search_knowledge_base':
                        if kb_name:
                             if args.get("kb_name") != kb_name:
                                  args["kb_name"] = kb_name
                        elif not args.get('kb_name'):
                            res_text = "To search the knowledge base, please select a collection from the sidebar first."
                            self.conversations[session_id].append({"role": "assistant", "content": res_text})
                            return {"response": res_text, "session_id": session_id, "success": True}

                    # Add assistant's thought to history
                    self.conversations[session_id].append({"role": "assistant", "content": json.dumps(decision)})
                    
                    try:
                        tool_result = self.tool_map[tool_name].invoke(args)
                        # Add result to history and loop
                        self.conversations[session_id].append({
                            "role": "system", 
                            "content": f"TOOL_RESULT ({tool_name}): {str(tool_result)}"
                        })
                    except Exception as te:
                        self.conversations[session_id].append({
                            "role": "system", 
                            "content": f"Error executing {tool_name}: {str(te)}"
                        })
                else:
                    self.conversations[session_id].append({
                        "role": "system", 
                        "content": f"Error: Tool {tool_name} is not available."
                    })

            return {
                "response": "I tried to process your request but reached the maximum number of steps. Please try being more specific.", 
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
