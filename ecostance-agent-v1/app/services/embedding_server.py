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
        
        # Apply GPU VRAM Limit if on CUDA
        if device == 'cuda':
            try:
                # Hardcoded 8GB limit for the Tesla P40
                vram_limit_mb = 8192 
                
                # Get physical device memory
                total_memory = torch.cuda.get_device_properties(0).total_memory
                total_memory_mb = total_memory / (1024 * 1024)
                
                # Calculate required fraction (e.g., 8192 / 24576 = 0.333...)
                fraction = min(1.0, vram_limit_mb / total_memory_mb)
                
                torch.cuda.set_per_process_memory_fraction(fraction, 0)
                logger.info(f"✓ GPU VRAM limit hardcoded to {vram_limit_mb}MB ({fraction:.1%} of total {total_memory_mb:.0f}MB)")
            except Exception as e:
                logger.warning(f"Could not set GPU memory limit: {e}")

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
    
    # Get batch size from env, default to 128 to match hardware capabilities
    batch_size = int(os.getenv("BGE_M3_BATCH_SIZE", "128"))
    
    try:
        if isinstance(request.text, str):
            embedding = model.encode(request.text, batch_size=batch_size).tolist()
            return {"embedding": embedding}
        else:
            embeddings = model.encode(request.text, batch_size=batch_size).tolist()
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
