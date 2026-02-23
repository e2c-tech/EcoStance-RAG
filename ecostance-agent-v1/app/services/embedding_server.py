from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Union
import uvicorn
import logging
import os
import torch
from sentence_transformers import SentenceTransformer
from app.config import EMBEDDING_MODEL_NAME, EMBEDDING_SERVER_PORT

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EmbeddingServer")

app = FastAPI(title="EcoStance Shared Embedding Server")

# Global model instance
model = None

@app.on_event("startup")
def load_model():
    global model
    try:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"Loading embedding model on device: {device}")
        
        # Determine model name
        model_name = os.getenv('EMBEDDING_MODEL_NAME', EMBEDDING_MODEL_NAME or 'BAAI/bge-m3')
        logger.info(f"Model: {model_name}")
        
        model = SentenceTransformer(model_name, device=device)
        logger.info("✓ Model loaded successfully!")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise e

class EmbedRequest(BaseModel):
    text: Union[str, List[str]]

@app.post("/embed")
async def embed(request: EmbedRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        if isinstance(request.text, str):
            embedding = model.encode(request.text).tolist()
            return {"embedding": embedding}
        else:
            embeddings = model.encode(request.text).tolist()
            return {"embeddings": embeddings}
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": model is not None}

if __name__ == "__main__":
    # Use port from config
    port = int(os.getenv("EMBEDDING_SERVER_PORT", EMBEDDING_SERVER_PORT))
    uvicorn.run(app, host="0.0.0.0", port=port)
