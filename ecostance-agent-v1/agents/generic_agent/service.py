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
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from .config import (
    AGENT_MODEL, GOOGLE_API_KEY, GROQ_API_KEY, 
    LLM_PROVIDER, AGENT_TEMPERATURE,
    GENERIC_MISSION_STATEMENT, GENERIC_OPERATIONAL_DIRECTIVES
)
from .tools.kb_tools import create_search_knowledge_base_tool, create_list_knowledge_bases_tool
from .tools.db_tools import create_db_query_tool, create_list_db_tables_tool

from app.services.multilingual_utils import MultilingualAgentMixin
from app.services.investigation_journal_service import log_investigation_step

logger = logging.getLogger(__name__)

# Strict whitelist of allowed tools for Generic agent
SAFE_GENERIC_TOOLS = {"knowledge_base", "database_query"}

class GenericAgentService(MultilingualAgentMixin):
    def __init__(self, tenant_id: str = None, company_name: str = "Assistant", allowed_tools: List[str] = None, custom_system_prompt: str = None, **kwargs):
        self.company_name = company_name
        self.mission_statement = (custom_system_prompt or GENERIC_MISSION_STATEMENT).format(company_name=company_name)
        
        super().__init__(system_prompts={"en": self.mission_statement})
        
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
        
        # Validate allowed tools
        requested_tools = allowed_tools if allowed_tools is not None else ["knowledge_base", "database_query"]
        self.allowed_tools = [t for t in requested_tools if t in SAFE_GENERIC_TOOLS]
        
        # Build tools list
        self.tools = []
        if "knowledge_base" in self.allowed_tools:
            self.tools.extend([
                create_search_knowledge_base_tool(tenant_id),
                create_list_knowledge_bases_tool(tenant_id)
            ])
        
        if "database_query" in self.allowed_tools:
            db_path = kwargs.get('database_connection')
            self.tools.extend([
                create_db_query_tool(db_path, tenant_id=tenant_id),
                create_list_db_tables_tool(db_path, tenant_id=tenant_id)
            ])
             
        self.tool_map = {tool.name: tool for tool in self.tools}
        self.conversations: Dict[str, List[Dict]] = {}
        
        # Bind tools once
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    def _get_dynamic_system_prompt(self, kb_name: str = None, db_name: str = None):
        sources = []
        if kb_name:
            sources.append(f"- **Knowledge Base**: '{kb_name}' active.")
        if db_name:
            sources.append(f"- **Database**: '{db_name}' active.")
        else:
            from app.routers import db_router
            if db_router.db_connector and db_router.db_connector.is_connected():
                 sources.append("- **Database**: Active global connection.")

        sources_section = f"### ACTIVE SOURCES:\n{chr(10).join(sources)}\n\n" if sources else ""
        return f"{self.mission_statement}\n\n{sources_section}{GENERIC_OPERATIONAL_DIRECTIVES}"

    def chat(self, session_id: str, message: str, user_language: str = None, chat_history: List[Dict] = None, **kwargs) -> Dict:
        try:
            detected_lang, preferred_lang, confidence = self.get_language_context(
                message, session_id, user_language
            )

            if session_id not in self.conversations:
                self.conversations[session_id] = []
                if chat_history:
                    self.conversations[session_id].extend(chat_history)
            
            self.conversations[session_id].append({"role": "user", "content": message})
            
            kb_name = kwargs.get('knowledge_base')
            db_conn_name = kwargs.get('database_connection')
            
            system_prompt = self._get_dynamic_system_prompt(kb_name=kb_name, db_name=db_conn_name)
            
            max_iterations = 5
            iteration = 0
            
            # Reconstruct Atomic History
            lc_messages = [SystemMessage(content=system_prompt)]
            full_history = self.conversations.get(session_id, [])
            recent_entries = full_history[-10:]
            
            if recent_entries and recent_entries[0].get("role") == "tool" and len(full_history) > 10:
                for i in range(len(full_history)-11, -1, -1):
                    if full_history[i].get("role") == "assistant":
                        recent_entries = full_history[i:]
                        break

            for msg_entry in recent_entries:
                role = msg_entry.get("role")
                content = msg_entry.get("content", "")
                if role == "user":
                    lc_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    tool_calls = msg_entry.get("tool_calls") or []
                    lc_messages.append(AIMessage(content=content, tool_calls=tool_calls))
                elif role == "tool":
                    lc_messages.append(ToolMessage(content=content, tool_call_id=msg_entry.get("tool_call_id")))
                elif role == "system":
                    lc_messages.append(SystemMessage(content=content))
            
            while iteration < max_iterations:
                iteration += 1
                logger.info(f"Generic Agent iteration {iteration} sending to LLM")
                
                response = self.llm_with_tools.invoke(lc_messages)
                
                self.conversations[session_id].append({
                    "role": "assistant",
                    "content": response.content,
                    "tool_calls": response.tool_calls
                })
                lc_messages.append(response)
                
                if not response.tool_calls:
                    return {
                        "response": response.content,
                        "session_id": session_id,
                        "language": preferred_lang,
                        "success": True
                    }
                
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call["id"]
                    
                    if tool_name not in self.tool_map:
                        tool_result = f"Error: Tool '{tool_name}' not found."
                    else:
                        try:
                            # Context enforcement
                            if tool_name == "search_knowledge_base" and kb_name:
                                tool_args["kb_name"] = kb_name
                                
                            result = self.tool_map[tool_name].invoke(tool_args)
                            tool_result = str(result)
                        except Exception as te:
                            logger.error(f"Tool error: {te}")
                            tool_result = f"Error executing {tool_name}: {str(te)}"
                    
                    self.conversations[session_id].append({
                        "role": "tool",
                        "content": tool_result,
                        "tool_call_id": tool_id
                    })
                    lc_messages.append(ToolMessage(content=tool_result, tool_call_id=tool_id))

                    # Journal Logging (Phase 3 objective)
                    log_investigation_step(
                        session_id=session_id,
                        agent_type="generic",
                        tenant_id=self.tenant_id,
                        thought=response.content,
                        tool_name=tool_name,
                        tool_args=tool_args,
                        tool_result=tool_result,
                        step_number=iteration
                    )
                
                import time
                time.sleep(1)
            
            timeout_msg = "I reached my maximum search depth. Please refine your question or try again."
            self.conversations[session_id].append({"role": "assistant", "content": timeout_msg})
            return {"response": timeout_msg, "session_id": session_id, "success": True}
            
        except Exception as e:
            logger.error(f"Generic Agent Critical Error: {e}", exc_info=True)
            return {"response": "An internal error occurred.", "session_id": session_id, "success": False}

    def get_conversation_history(self, session_id: str) -> List[Dict]:
        return self.conversations.get(session_id, [])

    def reset_conversation(self, session_id: str) -> bool:
        if session_id in self.conversations:
            del self.conversations[session_id]
            if hasattr(self, 'language_service'):
                self.language_service.clear_session_language(session_id)
            logger.info(f"Resetting generic conversation for session: {session_id}")
            return True
        return False
