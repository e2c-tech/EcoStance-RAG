from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_qdrant import Qdrant
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_groq import ChatGroq
import logging
import time

from app.config import GOOGLE_API_KEY, QDRANT_URL, QDRANT_API_KEY, EMBEDDING_MODEL_NAME
from .langsmith_service import trace_rag, trace_llm
from .language_service import get_language_service
from .multilingual_embedding_service import create_multilingual_embeddings
from app.config.multilingual_app_config import (
    CROSS_LANGUAGE_ENABLED,
    SAME_LANGUAGE_BOOST,
    CROSS_LANGUAGE_MIN_SIMILARITY
)

# Import LangSmith traceable for proper hierarchy
from langsmith import traceable

# === BEGIN: branch error handling ===
from ..core.logging import get_logger, log_error_with_context, log_operation_start, log_operation_success, log_operation_failure
from ..core.exceptions import ExternalServiceError, ValidationError, ResourceNotFoundError
# === END: branch error handling ===

# Configure logging for this module
logger = get_logger(__name__)
logging.basicConfig(level=logging.INFO) # Ensure basic config is set if not already

# --- Service Initialization ---

@trace_llm
def get_llm(provider: str = None, model: str = None, temperature: float = 0.3):
    """
    Returns an LLM instance based on the specified provider and model.
    """
    from app.config import LLM_PROVIDER as DEFAULT_PROVIDER
    from app.config import AGENT_MODEL as DEFAULT_MODEL
    from app.config import GOOGLE_API_KEY, GROQ_API_KEY
    
    provider = (provider or DEFAULT_PROVIDER or "gemini").lower()
    model = model or DEFAULT_MODEL or ("gemini-2.5-flash-lite" if provider == "gemini" else "llama-3.1-8b-instant")
    
    try:
        if provider == "gemini":
            if not GOOGLE_API_KEY:
                raise ValidationError("GOOGLE_API_KEY is not configured", "GOOGLE_API_KEY")
            return ChatGoogleGenerativeAI(
                model=model,
                google_api_key=GOOGLE_API_KEY,
                temperature=temperature
            )
        elif provider == "groq":
            if not GROQ_API_KEY:
                raise ValidationError("GROQ_API_KEY is not configured", "GROQ_API_KEY")
            return ChatGroq(
                model=model,
                groq_api_key=GROQ_API_KEY,
                temperature=temperature
            )
        else:
            raise ValidationError(f"Unsupported provider: {provider}", "provider")
    except Exception as e:
        log_error_with_context(logger, f"Failed to initialize {provider} LLM", e)
        raise ExternalServiceError(provider, "initialization", str(e))

@trace_rag
def get_retriever(collection_name: str, top_k: int = 5):
    """
    Initializes and returns a Qdrant retriever for a specific collection.
    
    Args:
        collection_name: Name of the Qdrant collection
        top_k: Number of chunks to retrieve (default: 5, increased for better coverage)
    
    Returns:
        Qdrant retriever instance
    """
    # === BEGIN: branch error handling ===
    try:
        from .qdrant_service import get_qdrant_client
        from .embedding_service import load_embedding_model
        from langchain_qdrant import QdrantVectorStore

        if not collection_name or not collection_name.strip():
            raise ValidationError(
                message="Collection name cannot be empty",
                field="collection_name"
            )
        
        if top_k <= 0:
            raise ValidationError(
                message="top_k must be a positive integer",
                field="top_k"
            )
        
        log_operation_start(
            logger, 
            "initialize_retriever", 
            collection_name=collection_name, 
            top_k=top_k
        )
        
        # Use singletons
        from .embedding_service import get_langchain_embeddings
        embeddings = get_langchain_embeddings()
        
        client = get_qdrant_client()
        
        qdrant_store = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=embeddings,
            content_payload_key="text",
        )
        
        # 1. Initial Retrieval Configuration
        # Fetch more candidates to give reranker enough choices
        # Initial threshold is lower (0.35) to cast a wider net
        initial_k = max(10, top_k * 3)
        
        search_params = {
            "k": initial_k,
            "score_threshold": 0.35
        }
        
        base_retriever = qdrant_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs=search_params
        )
        
        # 2. Define the reranking retrieval function
        from .reranker_service import get_reranker_service
        
        def retrieve_and_rerank(query: str) -> list[Document]:
            try:
                # A. Vector Search
                logger.info(f"Initial retrieval (k={initial_k}) for: '{query[:50]}...'")
                candidate_docs = base_retriever.invoke(query)
                
                if not candidate_docs:
                    logger.info("No candidates found in vector search")
                    return []
                
                # B. Reranking
                doc_texts = [d.page_content for d in candidate_docs]
                
                try:
                    reranker = get_reranker_service()
                    # Get (text, score) tuples
                    ranked_results = reranker.rerank(query, doc_texts, top_k=top_k)
                except Exception as re:
                     logger.error(f"Reranker service failed: {re}. Returning top candidates directly.")
                     return candidate_docs[:top_k]

                final_docs = []
                logger.info(f"--- Reranker Scores (Top {top_k}) ---")
                
                for text, score in ranked_results:
                    # Find original document to preserve metadata
                    # Note: text content must match exactly
                    original_doc = next((d for d in candidate_docs if d.page_content == text), None)
                    
                    if original_doc:
                        # Add score to metadata and log it
                        original_doc.metadata["reranker_score"] = float(score)
                        final_docs.append(original_doc)
                        logger.info(f"Score: {score:.4f} | Source: {original_doc.metadata.get('source', 'unknown')}")
                
                return final_docs
                
            except Exception as e:
                logger.error(f"Reranking/Retrieval Process Failed: {e}", exc_info=True)
                return []

        # Return a simple object with invoke() method to mimic a Retriever
        class RerankRetriever:
            def invoke(self, query):
                return retrieve_and_rerank(query)
                
        retriever = RerankRetriever()
        
        log_operation_success(
            logger, 
            "initialize_retriever_with_reranker", 
            collection_name=collection_name
        )
        return retriever
        
    except ValidationError:
        raise
    except Exception as e:
        error_str = str(e)
        if "404" in error_str or "Not found" in error_str or "doesn't exist" in error_str:
            raise ResourceNotFoundError(
                resource_type="Knowledge Base Collection",
                resource_id=collection_name,
                remediation="Please use list_available_knowledge_bases to find the correct collection name."
            )
            
        log_error_with_context(
            logger=logger,
            message=f"Failed to initialize retriever for collection '{collection_name}'",
            error=e,
            extra_context={"collection_name": collection_name, "top_k": top_k},
            remediation="Check Qdrant connection and verify collection exists"
        )
        raise ExternalServiceError(
            service_name="Qdrant",
            operation="retriever_initialization",
            original_error=error_str
        )
    # === END: branch error handling ===

def format_docs(docs: list[Document]) -> str:
    """Formats a list of Documents into a single string."""
    return "\n\n".join(doc.page_content for doc in docs)

def create_rag_chain(collection_name: str):
    """Creates a stateful RAG chain with conversation memory using LCEL."""
    retriever = get_retriever(collection_name)
    llm = get_llm()

    # Improved Answering Prompt - reduces "I don't know" responses
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", """You are an expert assistant helping users find information from a knowledge base. Your goal is to provide helpful, accurate answers based on the provided context.

RESPONSE GUIDELINES:

1. PRIMARY GOAL: Answer the question using information from the context
   - Extract and synthesize relevant information
   - Connect related pieces of information logically
   - Provide complete, helpful answers

2. WHEN INFORMATION IS PARTIAL:
   - Answer what you CAN from the context
   - Be specific about what information is available
   - Example: "Based on the context, I can tell you that [answer]. However, I don't have information about [missing part]."

3. WHEN INFORMATION IS MISSING:
   - Only say "I don't have information" if the context is completely unrelated
   - Try to provide related information that might be helpful
   - Suggest what the user might want to ask instead

4. ANSWER QUALITY:
   - Be conversational and natural
   - Provide context and explanations
   - Use examples from the context when helpful
   - Structure longer answers with bullet points or paragraphs

5. ACCURACY:
   - Base answers on the context provided
   - Don't invent information not in the context
   - If making logical connections, make them clear
   - Cite specific details from the context

Remember: Your job is to be HELPFUL while staying ACCURATE. Provide the best answer possible with the information available."""),
            ("human", """Context from knowledge base:
{context}

User question: {question}

Provide a helpful, accurate answer based on the context above:"""),
        ]
    )

    # Define the retrieval function
    def retrieve_and_format(inputs):
        question = inputs["question"]
        docs = retriever.invoke(question)
        formatted_context = format_docs(docs)
        logger.info(f"Context being passed to LLM: {formatted_context}")
        return formatted_context
    
    # Define the chat history formatting function
    def format_chat_history(inputs):
        chat_history = inputs.get("chat_history", [])
        if not chat_history:
            return "No previous conversation."
        
        formatted_history = []
        for i, message in enumerate(chat_history):
            if i % 2 == 0:
                formatted_history.append(f"Human: {message.content}")
            else:
                formatted_history.append(f"Assistant: {message.content}")
        
        return "\n".join(formatted_history)

    # Define the stateful RAG chain
    rag_chain = (
        RunnablePassthrough.assign(
            context=RunnableLambda(retrieve_and_format),
            chat_history=RunnableLambda(format_chat_history)
        )
        | RunnableLambda(lambda x: logger.info(f"Final inputs to prompt: question={x.get('question')}, has_history={bool(x.get('chat_history'))}") or x)
        | qa_prompt
        | llm
        | StrOutputParser()
    )
    
    return rag_chain

@traceable(name="rag_pipeline", tags=["rag", "pipeline"])
def execute_query(collection_name: str, query: str, chat_history: list = None, tenant_id: str = None) -> str:
    """
    Executes a query against the stateful RAG chain with conversation history.
    
    Args:
        collection_name: Qdrant collection name
        query: User query
        chat_history: Previous conversation messages
        tenant_id: Tenant identifier for filtering (optional, for future use)
    """
    # === BEGIN: branch error handling ===
    start_time = time.time()
    
    try:
        # Input validation
        if not query or not query.strip():
            raise ValidationError(
                message="Query cannot be empty",
                field="query"
            )
        
        if not collection_name or not collection_name.strip():
            raise ValidationError(
                message="Collection name cannot be empty",
                field="collection_name"
            )
        
        if chat_history is None:
            chat_history = []
        
        log_operation_start(
            logger, 
            "execute_rag_query", 
            collection_name=collection_name,
            query_length=len(query),
            chat_history_length=len(chat_history),
            tenant_id=tenant_id
        )
        
        # Create RAG chain with error handling
        try:
            rag_chain = create_rag_chain(collection_name)
        except (ValidationError, ResourceNotFoundError, ExternalServiceError):
            raise
        except Exception as e:
            raise ExternalServiceError(
                service_name="RAG Chain",
                operation="creation",
                original_error=str(e)
            )
        
        # Log the retrieval for debugging with error handling
        try:
            retriever = get_retriever(collection_name)
            retrieved_docs = retriever.invoke(query)
            formatted_context = format_docs(retrieved_docs)
            logger.info(
                f"Retrieved context for tenant {tenant_id}",
                extra={
                    "context_length": len(formatted_context),
                    "num_docs": len(retrieved_docs),
                    "tenant_id": tenant_id
                }
            )
        except Exception as e:
            log_error_with_context(
                logger=logger,
                message="Failed to retrieve context documents",
                error=e,
                extra_context={"collection_name": collection_name, "query": query[:100]},
                remediation="Check Qdrant collection and embedding service"
            )
            # Continue with RAG chain execution even if retrieval logging fails
        
        # Invoke the rag_chain with the query and chat history
        try:
            answer = rag_chain.invoke({
                "question": query,
                "chat_history": chat_history
            })
        except Exception as e:
            raise ExternalServiceError(
                service_name="RAG Chain",
                operation="query_execution",
                original_error=str(e)
            )
        
        duration_ms = int((time.time() - start_time) * 1000)
        log_operation_success(
            logger, 
            "execute_rag_query", 
            duration_ms=duration_ms,
            answer_length=len(answer) if answer else 0,
            tenant_id=tenant_id
        )
        
        return answer
        
    except (ValidationError, ResourceNotFoundError, ExternalServiceError) as e:
        # Re-raise known exceptions
        duration_ms = int((time.time() - start_time) * 1000)
        log_operation_failure(
            logger,
            "execute_rag_query",
            error=e,
            duration_ms=duration_ms,
            tenant_id=tenant_id
        )
        raise
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        log_operation_failure(
            logger,
            "execute_rag_query",
            error=e,
            duration_ms=duration_ms,
            remediation="Check all service dependencies and try again",
            tenant_id=tenant_id
        )
        raise ExternalServiceError(
            service_name="RAG System",
            operation="query_execution",
            original_error=str(e)
        )
    # === END: branch error handling ===
