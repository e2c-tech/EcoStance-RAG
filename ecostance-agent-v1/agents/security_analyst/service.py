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
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .config import (
    AGENT_MODEL, GOOGLE_API_KEY, GROQ_API_KEY, 
    LLM_PROVIDER, AGENT_TEMPERATURE
)

# Reuse existing generic tools
from agents.generic_agent.tools.kb_tools import (
    create_search_knowledge_base_tool,
    create_list_knowledge_bases_tool
)
from agents.generic_agent.tools.db_tools import create_db_query_tool, create_list_db_tables_tool

# Use SIEM Discovery tools
from .tools.siem_tools import (
    search_siem_logs, get_log_volume_stats
)

from app.services.multilingual_utils import MultilingualAgentMixin

logger = logging.getLogger(__name__)

SECURITY_SYSTEM_PROMPTS = {
    "en": """You are an Autonomous Senior Security Analyst and Threat Hunter (SOC Tier-3).
Your mission is to perform deep-dive investigations, identify root causes of security incidents, and provide actionable remediation strategies.

### MISSION PHILOSOPHY:
1. **Analytical Integrity**: Do not simply dump data. Interpret search results, correlate findings across different sources, and hypothesize potential threat vectors.
2. **Professional Judgement**: You have full agency. Choose your tools based on the investigation's needs. If a Knowledge Base contains policies and a Database contains logs, use both to determine if an action violated policy.
3. **Concise Brilliance**: Your final reports must be authoritative, objective, and clear. Use specific names and data points found during your research.
4. **Action-Oriented**: Every investigation must conclude with specific, high-impact recommendations.
"""
}

class SecurityAnalystService(MultilingualAgentMixin):
    def __init__(self, tenant_id: str = None, company_name: str = "SOC", allowed_tools: List[str] = None, **kwargs):
        super().__init__(system_prompts=SECURITY_SYSTEM_PROMPTS)
        
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
            search_siem_logs,
            get_log_volume_stats,
            create_db_query_tool(db_conn, tenant_id=tenant_id),
            create_list_db_tables_tool(db_conn, tenant_id=tenant_id)
        ]
            
        self.tool_map = {tool.name: tool for tool in self.tools}
        self.conversations: Dict[str, List[Dict]] = {}

    def _get_dynamic_system_prompt(self, lang: str = "en", kb_name: str = None, db_name: str = None):
        """Generate system prompt filtered by actually available tools."""
        base_prompt = SECURITY_SYSTEM_PROMPTS.get(lang, SECURITY_SYSTEM_PROMPTS["en"])
        
        tool_details = []
        if "search_knowledge_base" in self.tool_map:
            tool_details.append("- search_knowledge_base: Search uploaded documents, logs, and files for relevant information.")
        if "list_available_knowledge_bases" in self.tool_map:
            tool_details.append("- list_available_knowledge_bases: List available document collections.")
        if "list_database_tables" in self.tool_map:
             tool_details.append("- list_database_tables: See all tables and their columns in the connected database. Call this BEFORE writing any SQL query.")
        if "query_database" in self.tool_map:
            tool_details.append("- query_database: Run a SQL SELECT query against the connected database.")

        active_sources = []
        if kb_name:
            active_sources.append(f"- **Knowledge Base**: '{kb_name}' is selected and ready to search.")
        if db_name:
            active_sources.append(f"- **Database**: '{db_name}' is connected and ready to query.")
        else:
            from app.routers import db_router
            if db_router.db_connector and (db_router.db_connector.engine or db_router.db_connector.client):
                 active_sources.append("- **Database**: Connected and ready to query.")

        sources_section = f"### CURRENTLY SELECTED SOURCES:\n{chr(10).join(active_sources)}\n\n" if active_sources else ""

        return f"""{base_prompt}

{sources_section}### INVESTIGATION TOOLKIT:
{chr(10).join(tool_details)}

### OPERATIONAL DIRECTIVES:
1. Begin by identifying the core question. If the data is likely in a database (structured) or document (unstructured), select the appropriate tool.
2. If a Database is connected, always verify schema with `list_database_tables` before querying.
3. Correlate insights. If a log shows a suspicious IP, check the Knowledge Base for known indicators or blacklists if available.
4. If your initial hypothesis fails (no result), pivot to an alternative source.
"""

    def chat(self, session_id: str, message: str, user_language: str = None, chat_history: List[Dict] = None, **kwargs) -> Dict:
        try:
            detected_lang, preferred_lang, confidence = self.get_language_context(
                message, session_id, user_language
            )

            if session_id not in self.conversations:
                self.conversations[session_id] = []
                # Inject external history if provided (essential for persistence across requests)
                if chat_history:
                    self.conversations[session_id].extend(chat_history)
            
            self.conversations[session_id].append({"role": "user", "content": message})
            
            kb_name = kwargs.get('knowledge_base')
            db_name = kwargs.get('database_connection')
            
            system_prompt = self._get_dynamic_system_prompt(preferred_lang, kb_name=kb_name, db_name=db_name)
            tool_descriptions = "\n".join([f"- {t.name}: {t.description}" for t in self.tools])
            
            max_iterations = 8
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                
                # Build message list for LangChain
                lc_messages = [SystemMessage(content=system_prompt)]
                
                # Add history from self.conversations (cap at last 10 turns)
                for msg_entry in self.conversations[session_id][-10:]:
                    if msg_entry["role"] == "user":
                        lc_messages.append(HumanMessage(content=msg_entry["content"]))
                    elif msg_entry["role"] == "assistant":
                        lc_messages.append(AIMessage(content=msg_entry["content"]))
                    elif msg_entry["role"] == "system":
                        lc_messages.append(SystemMessage(content=msg_entry["content"]))
                import time
                time.sleep(1) # Add a small delay to respect rate limits
                # Add instructions for current turn
                is_last_turn = (iteration == max_iterations)
                instruction = f"""
### MANDATORY RESPONSE FORMAT:
You MUST respond with EXACTLY ONE valid JSON object only. 
DO NOT include any text outside the JSON. 

1. ANALYZE PREVIOUS TOOL RESULTS:
   - Interpret the findings. If a tool failed or returned no data, explain your next pivot in the 'reasoning' field.
   - If you have uncovered the root cause or sufficient information, output the final answer using the 'none' tool.

2. CHOOSE YOUR ACTION:
   - If you need more data (e.g. searching logs or checking policies):
     {{
         "tool": "tool_name",
         "args": {{"kb_name": "...", "query": "..."}},
         "reasoning": "What hypothesis am I testing and what new information do I expect?"
     }}
   
   - If you have reached a conclusion:
     {{
         "tool": "none",
         "response": "### Executive Summary\\n[Provide a comprehensive analysis here]\\n\\n### Key Findings\\n- [Finding 1]\\n- [Finding 2]\\n\\n### Recommended Action\\n[Explicit steps for mitigation]",
         "type": "text"
     }}

{ "CRITICAL: This is your LAST turn. You MUST provide your final report in the 'none' tool now." if is_last_turn else f"Turn {iteration}/{max_iterations}." }
"""
                lc_messages.append(SystemMessage(content=instruction))
                
                logger.info(f"Security Analyst iteration {iteration} sending to LLM")
                result = self.llm.invoke(lc_messages)
                text = result.content
                logger.info(f"LLM Response received ({len(text)} chars)")
                
                # Robust JSON extraction
                import re
                
                # Find all JSON-like blocks using bracket counting (handles nested objects)
                blocks = []
                brace_count = 0
                start_pos = -1
                for ci, ch in enumerate(text):
                    if ch == '{':
                        if brace_count == 0:
                            start_pos = ci
                        brace_count += 1
                    elif ch == '}':
                        brace_count -= 1
                        if brace_count == 0 and start_pos != -1:
                            blocks.append(text[start_pos:ci+1])
                
                decision = None
                
                for block in reversed(blocks): # Check most recent/deepest block first
                    try:
                        candidate = json.loads(block)
                        # If we find a 'none' tool or any valid tool structure, use it
                        if candidate.get('tool') == 'none' or 'tool' in candidate:
                            decision = candidate
                            break
                    except json.JSONDecodeError:
                        # json.loads failed — likely because LLM put literal newlines in string values
                        # Try sanitizing: escape newlines then re-parse
                        try:
                            sanitized = block.replace('\n', '\\n').replace('\r', '\\r')
                            candidate = json.loads(sanitized)
                            if candidate.get('tool') == 'none' or 'tool' in candidate:
                                decision = candidate
                                break
                        except:
                            pass
                        
                        # Last resort: regex extraction of "response" field
                        if '"tool"' in block and '"none"' in block and '"response"' in block:
                            resp_match = re.search(r'"response"\s*:\s*"([\s\S]*?)"\s*[,\n}]', block)
                            if resp_match:
                                decision = {"tool": "none", "response": resp_match.group(1)}
                                break
                        continue

                if not decision:
                    # Non-JSON response or parsing failed: treating as final if it looks like a message
                    final_text = text
                    # Try to clean up JSON artifacts if accidentally returned
                    final_text = re.sub(r'```json\s*', '', final_text)
                    final_text = re.sub(r'```\s*', '', final_text).strip()
                    
                    self.conversations[session_id].append({"role": "assistant", "content": final_text})
                    return {"content": final_text, "session_id": session_id, "language": preferred_lang, "success": True}

                tool_name = decision.get('tool')
                
                if tool_name == 'none' or not tool_name or is_last_turn:
                    final_text = decision.get('response', decision.get('reasoning', text))
                    self.conversations[session_id].append({"role": "assistant", "content": final_text})
                    return {"content": final_text, "session_id": session_id, "language": preferred_lang, "success": True}
                
                if tool_name in self.tool_map:
                    args = decision.get('args', {})
                    
                    # STRICT SELECTION ENFORCEMENT
                    if tool_name in ["query_database", "list_database_tables"]:
                         if not db_name:
                              from app.routers import db_router
                              if not (db_router.db_connector and (db_router.db_connector.engine or db_router.db_connector.client)):
                                   err_msg = "Database tool called but no Database is currently connected. Please connect a database from the sidebar."
                                   self.conversations[session_id].append({"role": "assistant", "content": err_msg})
                                   return {"response": err_msg, "session_id": session_id, "success": True}

                    if tool_name == "search_knowledge_base":
                        if kb_name:
                            if args.get("kb_name") != kb_name:
                                logger.info(f"Forcing knowledge base from '{args.get('kb_name')}' to '{kb_name}'")
                                args["kb_name"] = kb_name
                        elif not args.get("kb_name"):
                            kb_msg = "Please select a Knowledge Base from the sidebar before searching documents."
                            self.conversations[session_id].append({"role": "assistant", "content": kb_msg})
                            return {"response": kb_msg, "session_id": session_id, "success": True}

                    logger.info(f"Executing {tool_name} with {args}")
                    
                    # CRITICAL FIX: Add the assistant's thought/tool call to history so it knows it just asked for this
                    self.conversations[session_id].append({
                        "role": "assistant",
                        "content": json.dumps(decision)
                    })

                    try:
                        tool_result = self.tool_map[tool_name].invoke(args)
                        # Add tool result as system message and loop
                        result_content = str(tool_result)
                        if len(result_content) > 5000:
                            result_content = result_content[:5000] + "... [truncated]"
                        
                        self.conversations[session_id].append({
                            "role": "system", 
                            "content": f"TOOL_RESULT ({tool_name}): {result_content}"
                        })
                    except Exception as te:
                        logger.error(f"Tool error: {te}")
                        self.conversations[session_id].append({
                            "role": "system", 
                            "content": f"Error executing {tool_name}: {str(te)}"
                        })
                else:
                    self.conversations[session_id].append({
                        "role": "system", 
                        "content": f"Error: Tool {tool_name} is not available."
                    })

            # Exhausted iterations
            final_text = "I've analyzed the available sources but could not find a definitive answer. Please provide more clues or try a different query."
            self.conversations[session_id].append({"role": "assistant", "content": final_text})
            return {"content": final_text, "session_id": session_id, "language": preferred_lang, "success": True}
            
        except Exception as e:
            logger.error(f"Security Analyst Error: {e}")
            return {"content": "An internal error occurred during analysis.", "session_id": session_id, "success": False}

    def get_conversation_history(self, session_id: str) -> List[Dict]:
        return self.conversations.get(session_id, [])

    def reset_conversation(self, session_id: str) -> bool:
        """Reset the conversation history for a specific session."""
        if session_id in self.conversations:
            del self.conversations[session_id]
            logger.info(f"Resetting conversation for session: {session_id}")
            return True
        return False
