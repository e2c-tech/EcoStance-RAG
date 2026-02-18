"""
Knowledge Base Tools for QuickShip Logistics
These tools allow the ReAct agent to search through company documents using RAG.
"""

import logging
from langchain.tools import tool

logger = logging.getLogger(__name__)


def create_search_knowledge_base_tool(tenant_id: str):
    """
    Create a tenant-specific knowledge base search tool.
    
    Args:
        tenant_id: The tenant ID to scope the search to
    
    Returns:
        A tool function that searches the tenant's knowledge bases
    """
    @tool
    def search_knowledge_base(kb_name: str, query: str) -> str:
        """
        Search through company knowledge base documents for information.
        Use this when customer asks about policies, procedures, FAQs, or general information
        that is not in the shipment database.
        
        Args:
            kb_name: The knowledge base to search (e.g., 'policies', 'faq', 'procedures')
            query: The question or search query
        
        Returns:
            Relevant information from the knowledge base documents
        """
        try:
            # Import here to avoid circular dependencies
            from app.services.query_service import execute_query
            from app.services.qdrant_service import get_qdrant_client
            from app.services.tenant_service import get_tenant_service
            
            # Get tenant-specific collection name
            qdrant_client = get_qdrant_client()
            tenant_service = get_tenant_service(qdrant_client)
            collection_name = tenant_service.get_collection_name(tenant_id, kb_name)
            
            logger.info(f"Searching KB '{kb_name}' for tenant {tenant_id}, collection: {collection_name}")
            
            # Execute RAG query
            answer = execute_query(collection_name, query, chat_history=[])
            
            return f"Knowledge Base ({kb_name}):\n{answer}"
            
        except Exception as e:
            logger.error(f"Error in search_knowledge_base: {e}")
            return f"I couldn't search the knowledge base. Error: {str(e)}"
    
    return search_knowledge_base


def create_list_knowledge_bases_tool(tenant_id: str):
    """
    Create a tenant-specific knowledge base listing tool.
    
    Args:
        tenant_id: The tenant ID to scope the listing to
    
    Returns:
        A tool function that lists the tenant's knowledge bases
    """
    @tool
    def list_available_knowledge_bases() -> str:
        """
        List all available knowledge bases that can be searched.
        Use this when you need to know what knowledge bases are available.
        
        Returns:
            List of available knowledge base names
        """
        try:
            # Import here to avoid circular dependencies
            from app.services.qdrant_service import get_qdrant_client
            from app.services.tenant_service import get_tenant_service
            
            client = get_qdrant_client()
            tenant_service = get_tenant_service(client)
            
            # Get all collections
            collections = client.get_collections()
            
            if not collections.collections:
                return "No knowledge bases are currently available."
            
            # Filter for tenant-specific collections
            tenant_kbs = []
            sanitized_tenant = tenant_service._sanitize_name(tenant_id)
            
            for col in collections.collections:
                parsed = tenant_service.parse_collection_name(col.name)
                if parsed and parsed["tenant_id"] == sanitized_tenant:
                    tenant_kbs.append(parsed["kb_name"])
            
            if not tenant_kbs:
                return "No knowledge bases are currently available for your organization."
            
            return f"Available knowledge bases: {', '.join(tenant_kbs)}"
            
        except Exception as e:
            logger.error(f"Error in list_available_knowledge_bases: {e}")
            return f"Error listing knowledge bases: {str(e)}"
    
    return list_available_knowledge_bases
