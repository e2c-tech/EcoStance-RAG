from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_qdrant import Qdrant
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document # Import Document for type hinting if needed
import logging

from app.config import GOOGLE_API_KEY, QDRANT_URL, QDRANT_API_KEY, EMBEDDING_MODEL_NAME

# Configure logging for this module
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Ensure basic config is set if not already

# --- Service Initialization ---

def get_llm():
    """Initializes and returns the Gemini LLM."""
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY must be set in environment variables.")
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", google_api_key=GOOGLE_API_KEY, temperature=0.1)

def get_retriever(collection_name: str):
    """Initializes and returns a Qdrant retriever for a specific collection."""
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    qdrant_store = Qdrant.from_existing_collection(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        collection_name=collection_name,
        embedding=embeddings,
        content_payload_key="text",
    )
    return qdrant_store.as_retriever(search_kwargs={"k": 3})

def format_docs(docs: list[Document]) -> str:
    """Formats a list of Documents into a single string."""
    return "\n\n".join(doc.page_content for doc in docs)

def create_rag_chain(collection_name: str):
    """Creates a stateful RAG chain with conversation memory using LCEL."""
    retriever = get_retriever(collection_name)
    llm = get_llm()

    # Stateful Answering Prompt with chat history
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("human", """You are a helpful assistant. Based on the meeting transcript provided in the context below, answer the user's question.

Context from meeting transcript:
{context}

Question: {question}

Instructions:
- Read through the meeting transcript carefully
- Extract relevant information to answer the question
- If you can find information related to the question in the transcript, provide a clear answer
- If the transcript doesn't contain information to answer the question, say "I don't know"

Answer:"""),
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

def execute_query(collection_name: str, query: str, chat_history: list = None) -> str:
    """
    Executes a query against the stateful RAG chain with conversation history.
    """
    if chat_history is None:
        chat_history = []
    
    rag_chain = create_rag_chain(collection_name)
    
    # Log the retrieval for debugging
    retriever = get_retriever(collection_name)
    retrieved_docs = retriever.invoke(query)
    formatted_context = format_docs(retrieved_docs)
    logger.info(f"Retrieved Context: {formatted_context}")

    # Invoke the rag_chain with the query and chat history
    answer = rag_chain.invoke({
        "question": query,
        "chat_history": chat_history
    })
    
    return answer