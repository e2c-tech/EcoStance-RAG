"""
Knowledge Base Tools for Generic Agent
"""
import logging
from langchain.tools import tool

logger = logging.getLogger(__name__)

from app.tools.shared_tools import (
    create_search_knowledge_base_tool as shared_search_kb,
    create_list_knowledge_bases_tool as shared_list_kbs
)

def create_search_knowledge_base_tool(tenant_id: str):
    return shared_search_kb(tenant_id)

def create_list_knowledge_bases_tool(tenant_id: str):
    return shared_list_kbs(tenant_id)
