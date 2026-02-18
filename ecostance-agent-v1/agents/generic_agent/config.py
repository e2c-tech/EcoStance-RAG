"""
Configuration for Generic AI Agent
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM Provider Configuration ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google") # google or groq

# --- Agent Configuration ---
AGENT_MODEL = os.getenv("AGENT_MODEL", "gemini-2.5-flash-lite")
AGENT_TEMPERATURE = float(os.getenv("AGENT_TEMPERATURE", "0.3"))
