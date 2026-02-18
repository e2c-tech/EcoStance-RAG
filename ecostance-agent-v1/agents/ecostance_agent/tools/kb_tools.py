"""
Knowledge Base Tools for EcoStance Agent
"""
import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

def create_ecostance_kb_tools(tenant_id: str):
    """Factory to create KB tools with tenant scoping."""
    
    @tool
    def search_faq(query: str, kb_name: str = "ecostance-faq"):
        """
        Search for answers to EcoStance sustainability questions, policies, and FAQs.
        """
        try:
            from app.services.query_service import execute_query
            from app.services.qdrant_service import get_qdrant_client
            from app.services.tenant_service import get_tenant_service
            
            qdrant_client = get_qdrant_client()
            tenant_service = get_tenant_service(qdrant_client)
            collection_name = tenant_service.get_collection_name(tenant_id, kb_name)
            
            answer = execute_query(collection_name, query, chat_history=[])
            return answer
        except Exception as e:
            logger.error(f"KB Search error: {e}")
            return f"I couldn't find specific info on that. Try checking our website or asking about certificates."

    return [search_faq]
