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
    "en": """You are an Expert Senior Security Analyst (SOC Assistant). 
Your goal is to provide intelligent, summarized, and actionable security insights. 

### DATA SOURCE SELECTION RULES:
1. **Database (SQL)**: USE FOR: "Top", "Count", "Sum", "List of Assets", "Frequency", or "Analytics".
2. **Knowledge Base (RAG)**: USE FOR: "How to", "Policy", "SOP", or searching raw text/logs.
3. **ONLY USE SEARCH TOOLS** if a source is listed as 'Active' in your context.

### INTELLIGENCE & FORMATTING RULES:
1. **NO RAW DATA DUMPS**: NEVER just list raw database rows, IP lists, or long strings of IDs. 
2. **SUMMARIZE & ANALYZE**: 
   - Instead of "Found 10 alerts", say "A total of 10 high-severity alerts were identified, primarily originating from the DMZ."
   - Categorize findings (e.g., "The top 3 attack types are SQL Injection, Brute Force, and XSS").
3. **EXPERT CONTEXT**: Provide a security-focused explanation. If you see Tor exit nodes or failed logins, explain the risk.
4. **ACTIONABLE RECOMMENDATIONS**: Always conclude with a brief "Recommended Action" (e.g., "Immediate endpoint isolation recommended for infected hosts").
5. **HUMAN-FRIENDLY NAMES**: If you find IDs in a database, try to cross-reference or describe them by their types or names if available. Avoid strings like "Sensors with ids 1, 3, 5". Say "Sensors in the Finance and HR segments" if possible.
6. **BE PROFESSIONAL**: Use an analytical, objective, and authoritative tone.

### EXAMPLE OF EXPERT RESPONSE:
**User**: Show critical alerts in last 24 hours
**Expert Analysis**: In the last 24 hours, **7 critical alerts** were detected across the network. The most significant threats include multiple **SQL injection attempts** targeting the primary web gateway and three instances of **suspicious PowerShell execution** on endpoint EDR-WIN-22. 
**Recommended Action**: Immediate review of web application logs and endpoint isolation of EDR-WIN-22 for deeper forensic analysis.
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
            tool_details.append("- search_knowledge_base: ACCESS DOCS & LOG FILES. Use for policies, SOPs, and raw document searches.")
        if "list_available_knowledge_bases" in self.tool_map:
            tool_details.append("- list_available_knowledge_bases: List the names of available document collections.")
        if "list_database_tables" in self.tool_map:
             tool_details.append("- list_database_tables: DISCOVER DATA SCHEMA. List all tables in the SQL database. CALL THIS FIRST if you need to perform quantitative analysis.")
        if "query_database" in self.tool_map:
            tool_details.append("- query_database: SQL ANALYSIS. Run SELECT queries for analytics, counts, and asset lookups.")

        active_sources = []
        if kb_name:
            active_sources.append(f"- **Active Knowledge Base**: '{kb_name}'. Use for documentation search.")
        if db_name:
            active_sources.append(f"- **Active Database**: '{db_name}'. **PRIORITIZE THIS** for analytics, top counts, and structured data.")
        else:
            from app.routers import db_router
            if db_router.db_connector and (db_router.db_connector.engine or db_router.db_connector.client):
                 active_sources.append("- **Active Database**: [CONNECTED]. **PRIORITIZE THIS** for analytical queries like 'top IPs' or 'count'. Check tables via list_database_tables first.")

        sources_section = f"### CURRENTLY SELECTED SOURCES:\n{chr(10).join(active_sources)}\n\n" if active_sources else ""

        return f"""{base_prompt}

{sources_section}### AVAILABLE TOOLS:
{chr(10).join(tool_details)}

### INVESTIGATION STRATEGY:
- **STEP 1**: If the query involves "Top", "Count", "Summary", "Analytics", or "Listing" of any assets, you **MUST** call `list_database_tables` (to see the tables AND their column names) and then `query_database`.
- **STEP 2**: If the query involves "Policy", "Procedure", "SOP", or "Raw Logs", call `search_knowledge_base`.
- **STEP 3**: If you search the Knowledge Base and see results that look like structured log entries, check if those logs are also available in the Database for better analytical querying.
- **CRITICAL**: Do NOT guess table or column names. The metadata provided in `list_database_tables` is the ONLY source of truth for the schema.
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
DO NOT simulate tool results or "TOOL_RESULT" blocks.
DO NOT provide multiple JSON blocks.

### CRITICAL JSON FORMATTING RULE:
Your response MUST be valid JSON that can be parsed by json.loads().
- ALL string values MUST be on a SINGLE LINE. 
- Use \\n for newlines within strings, NEVER use actual line breaks inside a JSON string value.
- CORRECT: "response": "Top companies:\\n1. Apple\\n2. Google\\n3. Microsoft"
- WRONG:   "response": "Top companies:
1. Apple
2. Google"

1. ANALYZE PREVIOUS TOOL RESULTS:
   - If a tool result contains an error like "No such column" or "Invalid column", you MUST call `list_database_tables` immediately to find the correct schema.
   - If the previous tool result contains the answer, output the final answer using the 'none' tool immediately.
   - Do NOT search again for the same thing.

### DATABASE DISCOVERY RULE:
- If a Database is connected and you need to query it:
  1. You MUST call `list_database_tables` first to see the schema (unless you did so in this session).
  2. NEVER guess column names. Use the exact names from `list_database_tables`.

2. CHOOSE YOUR ACTION:
   - If you need more data (e.g. searching logs):
     {{
         "tool": "tool_name",
         "args": {{"kb_name": "...", "query": "..."}},
         "reasoning": "What specific new information I need."
     }}
   
   - If you have the answer OR if the search failed multiple times:
     {{
         "tool": "none",
         "response": "Final Expert Analysis: Your human-friendly final answer here. DO NOT list raw IDs (like 1, 2, 3), use sensor names or categories instead. Include a 'Recommended Action'. Use \\n for line breaks, NOT actual newlines.",
         "type": "text"
     }}

{ "CRITICAL: This is your LAST turn of 8. You MUST provide the final response in the 'none' tool now." if is_last_turn else f"Turn {iteration}/{max_iterations}." }
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
