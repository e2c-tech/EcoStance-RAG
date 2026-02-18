import os
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists.
# This is great for local development.
load_dotenv()

# --- Qdrant Configuration ---
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# --- Google Gemini API Configuration ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Groq API Configuration ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# --- LLM Provider Configuration ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google")
AGENT_MODEL = os.getenv("AGENT_MODEL", "gemini-2.5-flash-lite")
AGENT_TEMPERATURE = float(os.getenv("AGENT_TEMPERATURE", "0.3"))

# --- Embedding Model Configuration ---
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME")
EMBEDDING_VECTOR_SIZE = int(os.getenv("EMBEDDING_VECTOR_SIZE"))
DISTANCE_METRIC = os.getenv("DISTANCE_METRIC")

# --- LangSmith Configuration ---
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "ecostance-agent-v1")
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
