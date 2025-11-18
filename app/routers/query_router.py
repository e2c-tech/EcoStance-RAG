from fastapi import APIRouter, Form, HTTPException
from typing import List
from langchain_core.messages import HumanMessage, AIMessage
import logging

from app.services.query_service import execute_query

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/query/")
async def query_collection(
    collection_name: str = Form(...),
    query: str = Form(...),
    chat_history: List[str] = Form([])
):
    """
    API endpoint to ask a question to a specified Qdrant collection.
    """
    try:
        logger.info(f"Received query for collection: {collection_name}")
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
        answer = execute_query(collection_name, query, processed_chat_history)
        logger.info(f"Query executed successfully. Answer: {answer}")
        
        return {"answer": answer}
    except ValueError as e:
        logger.error(f"ValueError in query_collection: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"An unexpected error occurred in query_collection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred while processing the query: {e}")
