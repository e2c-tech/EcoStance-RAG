"""
Configuration for QuickShip AI Agent
Load settings from environment variables
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Google Gemini API Configuration ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Qdrant Configuration (for knowledge base features) ---
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# --- Embedding Model Configuration ---
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
EMBEDDING_VECTOR_SIZE = int(os.getenv("EMBEDDING_VECTOR_SIZE", "384"))
DISTANCE_METRIC = os.getenv("DISTANCE_METRIC", "Cosine")

# --- Database Configuration ---
QUICKSHIP_DB_PATH = os.getenv("QUICKSHIP_DB_PATH", "QuickShip.db")

# --- Agent Configuration ---
AGENT_MODEL = os.getenv("AGENT_MODEL", "gemini-2.5-flash-lite")
AGENT_TEMPERATURE = float(os.getenv("AGENT_TEMPERATURE", "0.3"))
