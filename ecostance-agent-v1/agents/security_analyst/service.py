"""
Security Analyst Agent Service
Handles investigation logic using KB, DB, and SIEM Discovery tools.
"""
import logging
import json
import re
from typing import List, Dict, Optional
import os

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from .config import (
    AGENT_MODEL, GOOGLE_API_KEY, GROQ_API_KEY, 
    LLM_PROVIDER, AGENT_TEMPERATURE,
    SECURITY_MISSION_STATEMENT, SECURITY_OPERATIONAL_DIRECTIVES,
    ENABLE_SIEM_TOOLS
)

# Reuse existing generic tools
from agents.generic_agent.tools.kb_tools import (
    create_search_knowledge_base_tool,
    create_list_knowledge_bases_tool
)
from agents.generic_agent.tools.db_tools import create_db_query_tool, create_list_db_tables_tool

# Use SIEM Discovery & Response tools
from .tools.siem_tools import (
    search_siem_logs, 
    get_log_volume_stats,
    get_unique_field_values,
    list_siem_indices,
    list_security_alerts,
    list_security_findings,
    get_security_correlations,
    acknowledge_siem_alerts,
    update_ip_whitelist
)

from app.services.multilingual_utils import MultilingualAgentMixin
from app.services.investigation_journal_service import log_investigation_step

logger = logging.getLogger(__name__)

class SecurityAnalystService(MultilingualAgentMixin):
    def __init__(self, tenant_id: str = None, company_name: str = "SOC", allowed_tools: List[str] = None, **kwargs):
        # We handle system prompts dynamically via config
        super().__init__(system_prompts={"en": SECURITY_MISSION_STATEMENT})
        
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
        db_conn = kwargs.get('database_connection')
        
        # Initialize basic tools
        self.tools = [
            create_search_knowledge_base_tool(tenant_id),
            create_list_knowledge_bases_tool(tenant_id),
            create_db_query_tool(db_conn, tenant_id=tenant_id),
            create_list_db_tables_tool(db_conn, tenant_id=tenant_id)
        ]

        if ENABLE_SIEM_TOOLS:
            logger.info("SIEM Tools are ENABLED for Security Analyst")
            self.tools.extend([
                search_siem_logs,
                get_log_volume_stats,
                get_unique_field_values,
                list_siem_indices,
                list_security_alerts,
                list_security_findings,
                get_security_correlations,
                acknowledge_siem_alerts,
                update_ip_whitelist
            ])
        else:
            logger.info("SIEM Tools are currently DISABLED (config toggle)")
            
        self.tool_map = {tool.name: tool for tool in self.tools}
        self.conversations: Dict[str, List[Dict]] = {}
        
        # Bind tools to the LLM for native function calling
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    def _get_dynamic_system_prompt(self, lang: str = "en", kb_name: str = None, db_name: str = None):
        """Generate system prompt filtered by actually available tools."""
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

        return f"{SECURITY_MISSION_STATEMENT}\n\n{sources_section}{SECURITY_OPERATIONAL_DIRECTIVES}"


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
            db_name = kwargs.get('database_connection')
            
            system_prompt = self._get_dynamic_system_prompt(preferred_lang, kb_name=kb_name, db_name=db_name)
            
            max_iterations = 8
            iteration = 0
            
            # Prepare message list for LangChain
            lc_messages = [SystemMessage(content=system_prompt)]
            
            # --- ATOMIC HISTORY RECONSTRUCTION (Phase 4 Logic) ---
            # Ensure we don't break ToolMessage <-> AIMessage pairs during truncation
            full_history = self.conversations.get(session_id, [])
            logger.info(f"Reconstructing history for session {session_id}. Full history length: {len(full_history)}")
            recent_entries = full_history[-15:] # Take a slightly larger window
            
            # If the first entry in our window is a 'tool' message, include its parent 'assistant' message
            if recent_entries and recent_entries[0].get("role") == "tool" and len(full_history) > 15:
                # Find the index of the last assistant message before this tool result
                for i in range(len(full_history)-16, -1, -1):
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
                logger.info(f"Security Analyst iteration {iteration} sending to LLM")
                
                # Execute turn using native tool binding
                try:
                    response = self.llm_with_tools.invoke(lc_messages)
                except Exception as llme:
                    logger.error(f"LLM Invoke failed: {llme}")
                    return {"content": f"AI model error: {str(llme)}", "session_id": session_id, "success": False}
                
                # Add response to history
                self.conversations[session_id].append({
                    "role": "assistant",
                    "content": response.content,
                    "tool_calls": response.tool_calls
                })
                lc_messages.append(response)
                
                logger.debug(f"LLM Response: {response.content[:100]}... | Tool calls: {len(response.tool_calls or [])}")
                
                if not response.tool_calls:
                    # Final answer reached
                    return {
                        "content": response.content,
                        "session_id": session_id,
                        "language": preferred_lang,
                        "success": True
                    }
                
                # Execute one or more tool calls
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call["id"]
                    
                    logger.info(f"Executing native tool {tool_name} with args {tool_args}")
                    
                    if tool_name not in self.tool_map:
                        tool_result = f"Error: Tool '{tool_name}' not found."
                    else:
                        try:
                            # Contextual enforcement
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
                        agent_type="security_analyst",
                        tenant_id=self.tenant_id,
                        thought=response.content,
                        tool_name=tool_name,
                        tool_args=tool_args,
                        tool_result=tool_result,
                        step_number=iteration
                    )
                
                import time
                time.sleep(1) # Respect rate limits
            
            # Timeout
            final_text = "Investigation timeout: I've processed several discovery steps but couldn't reach a final conclusion. Please provide more specific parameters."
            self.conversations[session_id].append({"role": "assistant", "content": final_text})
            return {"content": final_text, "session_id": session_id, "language": preferred_lang, "success": True}
            
        except Exception as e:
            logger.error(f"Security Analyst critical error in session {session_id}: {str(e)}", exc_info=True)
            # Try to provide a slightly more helpful message if we know what happened
            error_msg = f"An internal investigation error occurred: {str(e)}"
            return {"content": error_msg, "session_id": session_id, "success": False}

    def get_conversation_history(self, session_id: str) -> List[Dict]:
        return self.conversations.get(session_id, [])

    def reset_conversation(self, session_id: str) -> bool:
        """Reset the conversation history for a specific session."""
        if session_id in self.conversations:
            del self.conversations[session_id]
            logger.info(f"Resetting conversation for session: {session_id}")
            return True
        return False
