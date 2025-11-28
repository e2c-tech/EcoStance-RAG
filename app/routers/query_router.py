from fastapi import APIRouter, Form, HTTPException, Depends, Request
from typing import List
from langchain_core.messages import HumanMessage, AIMessage
import logging

from app.services.query_service import execute_query
from app.services.qdrant_service import get_qdrant_client
from app.services.tenant_service import get_tenant_service
from app.auth.dependencies import get_current_user
from app.auth.rbac import RBACService
from app.auth.permissions import Permission
from app.services.audit_service import AuditService
from app.db.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/query/")
async def query_collection(
    kb_name: str = Form(...),
    query: str = Form(...),
    chat_history: List[str] = Form([]),
    request: Request = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    API endpoint to ask a question to a tenant-specific knowledge base.
    The collection name is automatically resolved from tenant_id and kb_name.
    
    Requires: KB_QUERY permission
    """
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    
    # Check permission
    rbac = RBACService(db)
    rbac.require_permission(tenant_id, user_id, Permission.KB_QUERY)
    
    try:
        # Generate tenant-specific collection name
        qdrant_client = get_qdrant_client()
        tenant_service = get_tenant_service(qdrant_client)
        collection_name = tenant_service.get_collection_name(tenant_id, kb_name)
        
        # Verify collection exists
        if not tenant_service.collection_exists(collection_name):
            raise HTTPException(
                status_code=404,
                detail=f"Knowledge base '{kb_name}' not found for tenant"
            )
        
        logger.info(f"Received query for tenant {tenant_id}, kb: {kb_name}, collection: {collection_name}")
        logger.info(f"Query: {query}")
        logger.info(f"Chat history: {chat_history}")

        # Convert the flat list of strings into a list of HumanMessage and AIMessage objects
        processed_chat_history = []
        for i, message in enumerate(chat_history):
            if i % 2 == 0:
                processed_chat_history.append(HumanMessage(content=message))
            else:
                processed_chat_history.append(AIMessage(content=message))

        logger.info("Executing query...")
        answer = execute_query(collection_name, query, processed_chat_history, tenant_id=tenant_id)
        logger.info(f"Query executed successfully. Answer: {answer}")
        
        # Log successful query
        audit = AuditService(db)
        audit.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action="query_kb",
            resource_type="knowledge_base",
            resource_id=kb_name,
            details={
                "query": query[:100],  # Truncate long queries
                "collection_name": collection_name
            },
            status="success",
            request=request
        )
        
        return {
            "answer": answer,
            "tenant_id": tenant_id,
            "kb_name": kb_name
        }
    except ValueError as e:
        logger.error(f"ValueError in query_collection: {e}", exc_info=True)
        
        # Log failure
        audit = AuditService(db)
        audit.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action="query_kb",
            resource_type="knowledge_base",
            resource_id=kb_name,
            details={"query": query[:100]},
            status="failure",
            error_message=str(e),
            request=request
        )
        
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"An unexpected error occurred in query_collection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred while processing the query: {e}")
