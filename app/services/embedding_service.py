from sentence_transformers import SentenceTransformer
import torch
from typing import List, Dict, Any

# --- Model Loading ---
def load_embedding_model():
    """
    Loads the sentence-transformer model from HuggingFace and moves it to the
    appropriate device (GPU if available, otherwise CPU).

    Returns:
        The loaded SentenceTransformer model.
    """
    # Check if a CUDA-enabled GPU is available, otherwise use CPU
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Embedding service: Using device '{device}'")
    
    # Load a pre-trained model. 'all-MiniLM-L6-v2' is a great all-rounder.
    model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
    return model

# --- Embedding Creation ---
def create_embeddings(chunks: List[Dict[str, Any]], model: SentenceTransformer) -> List[Dict[str, Any]]:
    """
    Generates vector embeddings for a list of text chunks and attaches them.

    Args:
        chunks (List[Dict[str, Any]]): The list of processed data chunks.
        model (SentenceTransformer): The loaded sentence-transformer model.

    Returns:
        The list of chunks, now with an 'embedding' key in each one.
    """
    # Extract the text content from each chunk to be embedded.
    texts_to_embed = [chunk['text'] for chunk in chunks]

    # Generate embeddings for all texts in a single batch.
    # The `encode` method returns a list of numpy arrays.
    embeddings = model.encode(texts_to_embed, show_progress_bar=False)

    # Attach the generated embedding to its corresponding chunk.
    # We convert the numpy array to a list to ensure it's easily serializable (e.g., for JSON).
    for chunk, embedding in zip(chunks, embeddings):
        chunk['embedding'] = embedding.tolist()

    return chunks
