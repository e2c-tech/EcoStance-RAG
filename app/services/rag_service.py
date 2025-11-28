"""
RAG Service - Wrapper for querying knowledge bases.
"""
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import logging

from ..models.tenant_knowledge_base import TenantKnowledgeBase
from ..services.query_service import execute_query, get_retriever, format_docs
from ..services.qdrant_service import get_qdrant_client
from ..services.tenant_service import get_tenant_service

logger = logging.getLogger(__name__)


class RAGService:
    """Service for querying knowledge bases using RAG."""

    def __init__(self, db: Session):
        self.db = db

    async def query_knowledge_base(
        self,
        tenant_id: str,
        kb_id: str,
        query: str,
        top_k: int = 3,
        chat_history: Optional[List] = None
    ) -> Dict:
        """
        Query a knowledge base and return answer with sources.
        
        Args:
            tenant_id: Tenant ID
            kb_id: Knowledge base ID (kb_name)
            query: User query
            top_k: Number of top results to return
            chat_history: Optional conversation history
            
        Returns:
            Dictionary with answer and sources
        """
        try:
            # Verify KB exists and belongs to tenant
            kb = self.db.query(TenantKnowledgeBase).filter(
                TenantKnowledgeBase.tenant_id == tenant_id,
                TenantKnowledgeBase.kb_id == kb_id
            ).first()

            if not kb:
                raise ValueError(f"Knowledge base {kb_id} not found for tenant {tenant_id}")

            # Generate tenant-specific collection name
            qdrant_client = get_qdrant_client()
            tenant_service = get_tenant_service(qdrant_client)
            collection_name = tenant_service.get_collection_name(tenant_id, kb.name)
            
            logger.info(f"Querying collection: {collection_name} for tenant: {tenant_id}, kb: {kb.name}")

            # Verify collection exists
            if not tenant_service.collection_exists(collection_name):
                raise ValueError(f"Collection {collection_name} not found in Qdrant")

            # Execute RAG query
            answer = execute_query(
                collection_name=collection_name,
                query=query,
                chat_history=chat_history or [],
                tenant_id=tenant_id
            )

            # Get source documents
            retriever = get_retriever(collection_name)
            docs = retriever.invoke(query)

            # Format sources
            sources = []
            for i, doc in enumerate(docs[:top_k]):
                source_info = {
                    "filename": doc.metadata.get("source", "Unknown"),
                    "chunk_number": i + 1,
                    "similarity": doc.metadata.get("score", 0.0),
                    "preview": doc.page_content[:200] if doc.page_content else ""
                }
                sources.append(source_info)

            return {
                "answer": answer,
                "sources": sources,
                "kb_id": kb_id
            }

        except Exception as e:
            logger.error(f"Error querying knowledge base: {str(e)}", exc_info=True)
            return {
                "answer": "I'm sorry, I encountered an error while processing your question. Please try again.",
                "sources": [],
                "error": str(e)
            }
