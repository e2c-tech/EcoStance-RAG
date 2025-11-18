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

# --- Embedding Model Configuration ---
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
EMBEDDING_VECTOR_SIZE = 384 # Vector size for the chosen model
DISTANCE_METRIC = 'Cosine' # Distance metric for Qdrant

# --- Beta Features ---
ENABLE_REACT_AGENT = os.getenv("ENABLE_REACT_AGENT", "false").lower() == "true"

# --- Database Configuration ---
QUICKSHIP_DB_PATH = os.getenv("QUICKSHIP_DB_PATH", "QuickShip.db")
