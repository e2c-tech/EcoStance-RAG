"""
Multilingual RAG Service
Parallel implementation of RAG with multilingual capabilities using BGE-M3
"""

import logging
from typing import List, Dict, Optional, Tuple, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_qdrant import Qdrant

from .embedding_factory import get_embedding_service
from app.services.language_service import get_language_service
from app.config.multilingual_app_config import (
    CROSS_LANGUAGE_ENABLED,
    SAME_LANGUAGE_BOOST,
    CROSS_LANGUAGE_MIN_SIMILARITY,
    MAX_CROSS_LANGUAGE_RESULTS,
    LOG_CROSS_LANGUAGE_RETRIEVAL,
    get_multilingual_collection_name
)
from ..config import (
    QDRANT_URL,
    QDRANT_API_KEY,
    GOOGLE_API_KEY,
    GROQ_API_KEY,
    AGENT_MODEL,
    LLM_PROVIDER,
    GEMINI_MODELS,
    GROQ_MODELS
)

logger = logging.getLogger(__name__)


class MultilingualRAGService:
    """Multilingual RAG service with language-aware retrieval."""
    
    def __init__(self):
        self.embedding_service = get_embedding_service("bge-m3")
        self.language_service = get_language_service()
        
        # Initialize LLM based on provider configuration
        self.llm = self._initialize_llm()
        
        logger.info(f"Initialized multilingual RAG service with BGE-M3 and {LLM_PROVIDER} LLM")
    
    def _initialize_llm(self):
        """Initialize the appropriate LLM based on configuration."""
        if LLM_PROVIDER == "groq":
            if not GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY must be set for Groq LLM provider")
            
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=AGENT_MODEL,
                groq_api_key=GROQ_API_KEY,
                temperature=0.1
            )
        
        elif LLM_PROVIDER == "gemini":
            if not GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY must be set for Gemini LLM provider")
            
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=AGENT_MODEL,
                google_api_key=GOOGLE_API_KEY,
                temperature=0.1
            )
        
        else:
            raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}. Supported providers: groq, gemini")
    
    def get_multilingual_retriever(self, collection_name: str, k: int = 5):
        """
        Create a multilingual-aware retriever for a collection.
        
        Args:
            collection_name: Qdrant collection name
            k: Number of results to retrieve
            
        Returns:
            Qdrant retriever configured for multilingual search
        """
        try:
            # Create Qdrant store with BGE-M3 embeddings
            from qdrant_client import QdrantClient
            client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
            
            qdrant_store = Qdrant.from_existing_collection(
                collection_name=collection_name,
                embedding=self.embedding_service,
                content_payload_key="text",
                client=client,
            )
            
            return qdrant_store.as_retriever(
                search_kwargs={
                    "k": k,
                    "score_threshold": CROSS_LANGUAGE_MIN_SIMILARITY
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to create multilingual retriever for {collection_name}: {e}")
            raise
    
    def language_aware_retrieve(self, query: str, collection_name: str, 
                               user_language: Optional[str] = None, k: int = 5) -> List[Document]:
        """
        Perform language-aware retrieval with cross-language capabilities.
        Uses direct QdrantClient query to avoid compatibility issues.
        """
        try:
            # Detect query language
            query_language, confidence = self.language_service.detect_language(
                query, return_confidence=True
            )
            
            if LOG_CROSS_LANGUAGE_RETRIEVAL:
                logger.info(f"Query language: {query_language} (confidence: {confidence:.2f})")
            
            # 1. Embed the query
            # self.embedding_service is a LangChain Embeddings interface (HuggingFaceBgeEmbeddings)
            query_vector = self.embedding_service.embed_query(query)
            
            # 2. Query Qdrant directly
            from qdrant_client import QdrantClient
            client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
            
            # Use query_points which is available in newer clients
            search_result = client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=k * 2, # Get more for reranking
                with_payload=True
            ).points
            
            # 3. Convert to Documents
            documents = []
            for point in search_result:
                metadata = point.payload
                content = metadata.pop("text", "") if metadata else ""
                
                # Add score to metadata for debugging/reranking
                docs_metadata = metadata.copy() if metadata else {}
                docs_metadata['score'] = point.score
                
                # Create doc
                doc = Document(page_content=content, metadata=docs_metadata)
                documents.append(doc)
            
            if not documents:
                logger.warning(f"No documents retrieved for query: {query[:50]}...")
                return []
            
            # Apply language-aware ranking
            ranked_documents = self._rerank_by_language(
                documents, query_language, user_language
            )
            
            # Limit results
            final_documents = ranked_documents[:k]
            
            if LOG_CROSS_LANGUAGE_RETRIEVAL:
                self._log_retrieval_results(final_documents, query_language)
            
            return final_documents
            
        except Exception as e:
            logger.error(f"Error in language-aware retrieval: {e}")
            return []
    
    def _rerank_by_language(self, documents: List[Document], query_language: str, 
                           user_language: Optional[str] = None) -> List[Document]:
        """
        Rerank documents based on language preferences.
        """
        if not CROSS_LANGUAGE_ENABLED:
            return documents
        
        scored_documents = []
        
        for doc in documents:
            # Get document language from metadata
            doc_language = doc.metadata.get('language', 'unknown')
            
            # Calculate language score
            language_score = self._calculate_language_score(
                doc_language, query_language, user_language
            )
            
            # Get original similarity score from metadata
            original_score = doc.metadata.get('score', 1.0)
            
            # Apply language boost
            final_score = original_score * language_score
            
            scored_documents.append((doc, final_score, doc_language))
        
        # Sort by final score (descending)
        scored_documents.sort(key=lambda x: x[1], reverse=True)
        
        # Return documents only
        return [doc for doc, score, lang in scored_documents]
    
    def _calculate_language_score(self, doc_language: str, query_language: str, 
                                 user_language: Optional[str] = None) -> float:
        """
        Calculate language preference score for a document.
        
        Args:
            doc_language: Document language
            query_language: Query language
            user_language: User's preferred language
            
        Returns:
            Language score multiplier
        """
        # Same language as query gets boost
        if doc_language == query_language:
            return SAME_LANGUAGE_BOOST
        
        # Same language as user preference gets moderate boost
        if user_language and doc_language == user_language:
            return 1.2
        
        # English gets slight boost as fallback
        if doc_language == 'en':
            return 1.1
        
        # Other languages get normal score
        return 1.0
    
    def _log_retrieval_results(self, documents: List[Document], query_language: str):
        """Log retrieval results for debugging."""
        if not documents:
            return
        
        language_counts = {}
        for doc in documents:
            doc_lang = doc.metadata.get('language', 'unknown')
            language_counts[doc_lang] = language_counts.get(doc_lang, 0) + 1
        
        logger.info(f"Retrieved {len(documents)} documents for query language '{query_language}'")
        logger.info(f"Language distribution: {language_counts}")
    
    def format_multilingual_docs(self, docs: List[Document]) -> str:
        """
        Format documents with language information.
        
        Args:
            docs: List of documents
            
        Returns:
            Formatted document string
        """
        if not docs:
            return "No relevant documents found."
        
        formatted_parts = []
        
        for i, doc in enumerate(docs, 1):
            doc_language = doc.metadata.get('language', 'unknown')
            language_name = self.language_service.get_language_name(doc_language)
            
            # Add language indicator
            header = f"Document {i} ({language_name}):"
            content = doc.page_content
            
            formatted_parts.append(f"{header}\n{content}")
        
        return "\n\n".join(formatted_parts)
    
    def create_multilingual_rag_chain(self, collection_name: str):
        """
        Create a multilingual RAG chain with language awareness.
        
        Args:
            collection_name: Qdrant collection name
            
        Returns:
            Configured RAG chain
        """
        # Multilingual QA prompt
        qa_prompt = ChatPromptTemplate.from_messages([
            ("human", """You are a helpful multilingual assistant. Based on the company documents provided below, answer the user's question.

The documents may be in different languages. Use the information from all relevant documents regardless of language.

Context from documents:
{context}

User's question: {question}
Detected question language: {question_language}

Instructions:
- Answer in the same language as the user's question
- Use information from all relevant documents
- If documents are in different languages, synthesize the information
- If you cannot find relevant information, say "I don't have enough information to answer that question"
- Be clear and concise

Answer:""")
        ])
        
        def retrieve_and_format(inputs):
            """Retrieve and format documents with language awareness."""
            question = inputs["question"]
            user_language = inputs.get("user_language")
            
            # Detect question language
            question_language = self.language_service.detect_language(question)
            
            # Retrieve documents
            docs = self.language_aware_retrieve(
                question, collection_name, user_language
            )
            
            # Format documents
            formatted_context = self.format_multilingual_docs(docs)
            
            # Return all inputs plus new context and question_language
            return {
                **inputs,  # Pass through original inputs
                "context": formatted_context,
                "question_language": question_language
            }
        
        # Create the chain
        rag_chain = (
            RunnableLambda(retrieve_and_format)
            | qa_prompt
            | self.llm
            | StrOutputParser()
        )
        
        return rag_chain
    
    def execute_multilingual_query(self, collection_name: str, query: str, 
                                  user_language: Optional[str] = None, 
                                  chat_history: List = None) -> str:
        """
        Execute a multilingual query against the knowledge base.
        
        Args:
            collection_name: Qdrant collection name
            query: User's question
            user_language: User's preferred language
            chat_history: Conversation history (for future use)
            
        Returns:
            Answer from the multilingual RAG system
        """
        try:
            # Create RAG chain
            rag_chain = self.create_multilingual_rag_chain(collection_name)
            
            # Execute query
            answer = rag_chain.invoke({
                "question": query,
                "user_language": user_language,
                "chat_history": chat_history or []
            })
            
            return answer
            
        except Exception as e:
            logger.error(f"Error in multilingual query execution: {e}")
            return f"I apologize, but I encountered an error while searching for information: {str(e)}"
    
    def check_collection_exists(self, collection_name: str) -> bool:
        """
        Check if a multilingual collection exists.
        
        Args:
            collection_name: Collection name to check
            
        Returns:
            True if collection exists, False otherwise
        """
        try:
            from qdrant_client import QdrantClient
            
            client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
            collections = client.get_collections()
            
            collection_names = [col.name for col in collections.collections]
            return collection_name in collection_names
            
        except Exception as e:
            logger.error(f"Error checking collection existence: {e}")
            return False
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Get information about a multilingual collection.
        
        Args:
            collection_name: Collection name
            
        Returns:
            Collection information dictionary
        """
        try:
            from qdrant_client import QdrantClient
            
            client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
            
            if not self.check_collection_exists(collection_name):
                return {"exists": False}
            
            collection_info = client.get_collection(collection_name)
            
            return {
                "exists": True,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status,
                "optimizer_status": collection_info.optimizer_status,
            }
            
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {"exists": False, "error": str(e)}


# Global multilingual RAG service instance
_multilingual_rag_service = None

def get_multilingual_rag_service() -> MultilingualRAGService:
    """Get or create the global multilingual RAG service instance."""
    global _multilingual_rag_service
    if _multilingual_rag_service is None:
        _multilingual_rag_service = MultilingualRAGService()
    return _multilingual_rag_service
