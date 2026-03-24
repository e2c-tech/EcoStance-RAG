"""
Multilingual Knowledge Base Tools for QuickShip Logistics
Enhanced tools with cross-language search capabilities
"""

import logging
from langchain.tools import tool
from typing import Optional

from ..services.multilingual_rag_service import get_multilingual_rag_service
from app.services.language_service import get_language_service
from app.config.multilingual_app_config import (
    get_multilingual_collection_name,
    should_use_multilingual_service
)
from app.services.tenant_service import TenantService

logger = logging.getLogger(__name__)


def create_multilingual_search_tool(tenant_id: str):
    """
    Create a tenant-specific multilingual knowledge base search tool.
    
    Args:
        tenant_id: The tenant ID to scope the search to
    
    Returns:
        A tool function that searches the tenant's knowledge bases with multilingual support
    """
    @tool
    def search_multilingual_knowledge_base(kb_name: str, query: str, user_language: Optional[str] = None) -> str:
        """
        Search through company knowledge base documents with multilingual support.
        This tool can find relevant information across different languages and respond in the user's language.
        
        Use this when customer asks about policies, procedures, FAQs, or general information
        that is not in the shipment database.
        
        Args:
            kb_name: The knowledge base to search (e.g., 'policies', 'faq', 'procedures')
            query: The question or search query in any supported language
            user_language: Optional user's preferred language (auto-detected if not provided)
        
        Returns:
            Relevant information from the knowledge base documents in the appropriate language
        """
        try:
            # Check if multilingual service should be used
            if not should_use_multilingual_service(tenant_id):
                # Fall back to legacy tool
                from .knowledge_base_tools import create_search_knowledge_base_tool
                legacy_tool = create_search_knowledge_base_tool(tenant_id)
                return legacy_tool.invoke({"kb_name": kb_name, "query": query})
            
            # Get services
            rag_service = get_multilingual_rag_service()
            language_service = get_language_service()
            
            # Get multilingual collection name
            collection_name = get_multilingual_collection_name(tenant_id, kb_name)
            
            logger.info(f"Searching multilingual KB '{kb_name}' for tenant {tenant_id}")
            logger.info(f"Collection: {collection_name}, Query: {query[:50]}...")
            
            # Check if multilingual collection exists
            if not rag_service.check_collection_exists(collection_name):
                # Try legacy collection as fallback
                from ..services.qdrant_service import get_qdrant_client
                from app.services.tenant_service import get_tenant_service
                
                client = get_qdrant_client()
                tenant_service = get_tenant_service(client)
                legacy_collection = tenant_service.get_collection_name(tenant_id, kb_name)
                
                if rag_service.check_collection_exists(legacy_collection):
                    logger.warning(f"Multilingual collection not found, using legacy: {legacy_collection}")
                    # Use legacy RAG service
                    from ..services.rag_service import execute_query
                    answer = execute_query(legacy_collection, query, chat_history=[])
                    return f"Knowledge Base ({kb_name}):\n{answer}"
                else:
                    return f"Knowledge base '{kb_name}' is not available. Please check the name or contact support."
            
            # Detect user language if not provided
            if not user_language:
                user_language = language_service.detect_language(query)
            
            # Execute multilingual query
            answer = rag_service.execute_multilingual_query(
                collection_name=collection_name,
                query=query,
                user_language=user_language
            )
            
            # Format response with language info
            detected_lang = language_service.detect_language(query)
            lang_name = language_service.get_language_name(detected_lang)
            
            return f"Knowledge Base ({kb_name}) - {lang_name}:\n{answer}"
            
        except Exception as e:
            logger.error(f"Error in multilingual knowledge base search: {e}")
            return f"I couldn't search the knowledge base. Error: {str(e)}"
    
    return search_multilingual_knowledge_base


def create_multilingual_list_tool(tenant_id: str):
    """
    Create a tenant-specific multilingual knowledge base listing tool.
    
    Args:
        tenant_id: The tenant ID to scope the listing to
    
    Returns:
        A tool function that lists the tenant's available knowledge bases
    """
    @tool
    def list_multilingual_knowledge_bases() -> str:
        """
        List all available knowledge bases that can be searched with multilingual support.
        Shows both multilingual and legacy collections.
        
        Returns:
            List of available knowledge base names with language support info
        """
        try:
            # Check if multilingual service should be used
            if not should_use_multilingual_service(tenant_id):
                # Fall back to legacy tool
                from .knowledge_base_tools import create_list_knowledge_bases_tool
                legacy_tool = create_list_knowledge_bases_tool(tenant_id)
                return legacy_tool.invoke({})
            
            # Get services
            from ..services.qdrant_service import get_qdrant_client
            from app.services.tenant_service import get_tenant_service
            
            client = get_qdrant_client()
            tenant_service = get_tenant_service(client)
            
            # Get all collections
            collections = client.get_collections()
            
            if not collections.collections:
                return "No knowledge bases are currently available."
            
            # Filter for tenant-specific collections
            tenant_kbs = []
            multilingual_kbs = []
            sanitized_tenant = TenantService._sanitize_name(tenant_id)
            
            for col in collections.collections:
                # Check for multilingual collections
                if col.name.endswith("_ml"):
                    # Parse multilingual collection name
                    base_name = col.name[:-3]  # Remove _ml suffix
                    parsed = tenant_service.parse_collection_name(base_name)
                    if parsed and parsed["tenant_id"] == sanitized_tenant:
                        multilingual_kbs.append(parsed["kb_name"])
                else:
                    # Check for legacy collections
                    parsed = tenant_service.parse_collection_name(col.name)
                    if parsed and parsed["tenant_id"] == sanitized_tenant:
                        kb_name = parsed["kb_name"]
                        if kb_name not in multilingual_kbs:  # Avoid duplicates
                            tenant_kbs.append(kb_name)
            
            if not tenant_kbs and not multilingual_kbs:
                return "No knowledge bases are currently available for your organization."
            
            # Format response
            response_parts = []
            
            if multilingual_kbs:
                response_parts.append(f"Multilingual Knowledge Bases: {', '.join(multilingual_kbs)}")
            
            if tenant_kbs:
                legacy_kbs = [kb for kb in tenant_kbs if kb not in multilingual_kbs]
                if legacy_kbs:
                    response_parts.append(f"Legacy Knowledge Bases: {', '.join(legacy_kbs)}")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"Error in listing multilingual knowledge bases: {e}")
            return f"Error listing knowledge bases: {str(e)}"
    
    return list_multilingual_knowledge_bases


def create_language_detection_tool():
    """
    Create a language detection tool for debugging and user assistance.
    
    Returns:
        A tool function that detects the language of given text
    """
    @tool
    def detect_text_language(text: str) -> str:
        """
        Detect the language of the provided text.
        Useful for understanding what language the user is communicating in.
        
        Args:
            text: Text to analyze for language detection
        
        Returns:
            Detected language name and confidence information
        """
        try:
            language_service = get_language_service()
            
            # Detect language with confidence
            language, confidence = language_service.detect_language(text, return_confidence=True)
            language_name = language_service.get_language_name(language)
            
            # Check if multilingual
            is_multilingual, distribution = language_service.is_multilingual_text(text)
            
            if is_multilingual:
                lang_info = []
                for lang, prob in distribution.items():
                    lang_name = language_service.get_language_name(lang)
                    lang_info.append(f"{lang_name}: {prob:.1%}")
                
                return f"Multilingual text detected:\n" + "\n".join(lang_info)
            else:
                return f"Language: {language_name} ({language}) - Confidence: {confidence:.1%}"
                
        except Exception as e:
            logger.error(f"Error in language detection: {e}")
            return f"Error detecting language: {str(e)}"
    
    return detect_text_language


def create_cross_language_search_tool(tenant_id: str):
    """
    Create a cross-language search tool that can find content across different languages.
    
    Args:
        tenant_id: The tenant ID to scope the search to
    
    Returns:
        A tool function for cross-language search
    """
    @tool
    def cross_language_search(kb_name: str, query: str, target_languages: Optional[str] = None) -> str:
        """
        Search across multiple languages in the knowledge base.
        This tool specifically looks for information in different languages and provides a summary.
        
        Args:
            kb_name: The knowledge base to search
            query: The search query
            target_languages: Comma-separated list of target languages (e.g., "en,es,fr")
        
        Returns:
            Cross-language search results with language indicators
        """
        try:
            # Check if multilingual service should be used
            if not should_use_multilingual_service(tenant_id):
                return "Cross-language search requires multilingual features to be enabled."
            
            # Get services
            rag_service = get_multilingual_rag_service()
            language_service = get_language_service()
            
            # Get collection name
            collection_name = get_multilingual_collection_name(tenant_id, kb_name)
            
            # Check collection exists
            if not rag_service.check_collection_exists(collection_name):
                return f"Multilingual knowledge base '{kb_name}' is not available."
            
            logger.info(f"Cross-language search in '{kb_name}' for: {query[:50]}...")
            
            # Perform retrieval with more results for cross-language analysis
            documents = rag_service.language_aware_retrieve(
                query=query,
                collection_name=collection_name,
                user_language=None,  # Don't bias towards any language
                k=10  # Get more results for cross-language analysis
            )
            
            if not documents:
                return "No relevant information found across languages."
            
            # Group results by language
            language_results = {}
            for doc in documents:
                doc_lang = doc.metadata.get('language', 'unknown')
                lang_name = language_service.get_language_name(doc_lang)
                
                if lang_name not in language_results:
                    language_results[lang_name] = []
                
                language_results[lang_name].append(doc.page_content[:200] + "...")
            
            # Format cross-language results
            result_parts = [f"Cross-language search results for: {query}\n"]
            
            for lang_name, contents in language_results.items():
                result_parts.append(f"**{lang_name} Results:**")
                for i, content in enumerate(contents[:3], 1):  # Limit to 3 per language
                    result_parts.append(f"{i}. {content}")
                result_parts.append("")  # Empty line
            
            return "\n".join(result_parts)
            
        except Exception as e:
            logger.error(f"Error in cross-language search: {e}")
            return f"Error performing cross-language search: {str(e)}"
    
    return cross_language_search
