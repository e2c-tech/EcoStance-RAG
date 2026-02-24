import time
import copy
import nltk
import concurrent.futures
import math
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# --- NLTK Setup ---
# Download the sentence tokenizer model from NLTK. This is a one-time download.
# In a production environment, this should be handled during the application's setup or in the Dockerfile.
try:
    nltk.data.find('tokenizers/punkt')
except nltk.downloader.DownloadError:
    print("Downloading NLTK's 'punkt' model for sentence tokenization...")
    nltk.download('punkt')

def chunk_blocks(
    blocks: List[Dict[str, Any]], 
    target_chunk_words: int = 500, 
    overlap_sentences: int = 1
) -> List[Dict[str, Any]]:
    """
    Chunks the text content of each block using a semantic, sentence-aware strategy.

    This function first splits the text into sentences, then groups those sentences
    into chunks of a target word count, ensuring that no sentence is broken mid-way.
    It also adds a configurable number of overlapping sentences between chunks to
    preserve context for retrieval.

    Args:
        blocks (List[Dict[str, Any]]): A list of enriched data blocks from the cleaning stage.
        target_chunk_words (int): The desired number of words per chunk (approximate).
        overlap_sentences (int): The number of sentences from the previous chunk to include
                                 at the beginning of the next chunk.

    Returns:
        A list of final, semantically chunked data blocks ready for embedding.
    """
def _chunk_segment(args) -> List[Dict[str, Any]]:
    """Helper function to chunk a segment of blocks, safe for multiprocessing."""
    blocks, target_chunk_words, overlap_sentences = args
    segment_chunks = []
    
    for block in blocks:
        text = block.get('text', '')
        if not text:
            continue

        # 1. Split the text into sentences using NLTK's sentence tokenizer.
        sentences = nltk.sent_tokenize(text)
        if not sentences:
            continue

        # 2. Group sentences into chunks based on the target word count.
        sentence_groups = []
        current_group = []
        current_word_count = 0
        for sentence in sentences:
            sentence_word_count = len(sentence.split())
            if current_word_count + sentence_word_count <= target_chunk_words:
                current_group.append(sentence)
                current_word_count += sentence_word_count
            else:
                sentence_groups.append(current_group)
                current_group = [sentence]
                current_word_count = sentence_word_count
        
        if current_group:
            sentence_groups.append(current_group)

        # 3. Create final chunks with sentence-based overlap.
        for i, group in enumerate(sentence_groups):
            chunk_text = " ".join(group)
            
            if i > 0 and overlap_sentences > 0:
                overlap_text = " ".join(sentence_groups[i-1][-overlap_sentences:])
                chunk_text = overlap_text + " " + chunk_text

            chunk_metadata = copy.deepcopy(block['metadata'])
            chunk_metadata['ingest_timestamp'] = time.time()

            segment_chunks.append({
                "text": chunk_text,
                "metadata": chunk_metadata
            })
            
    return segment_chunks

def chunk_blocks(
    blocks: List[Dict[str, Any]], 
    target_chunk_words: int = 500, 
    overlap_sentences: int = 1
) -> List[Dict[str, Any]]:
    """
    Chunks the text content using multi-core parallel processing.
    """
    if not blocks:
        return []

    num_blocks = len(blocks)
    max_workers = 4
    
    if num_blocks < 200:
        # Small document: Single process
        final_chunks = _chunk_segment((blocks, target_chunk_words, overlap_sentences))
    else:
        # Large document: Spin up ProcessPoolExecutor
        chunk_size = math.ceil(num_blocks / max_workers)
        block_chunks = [blocks[i:i + chunk_size] for i in range(0, num_blocks, chunk_size)]
        
        # We need to pass the arguments as tuples since max_workers handles 1 arg iterables cleanly
        tasks = [(chunk, target_chunk_words, overlap_sentences) for chunk in block_chunks]
        
        final_chunks = []
        logger.info(f"Parallelizing chunking across {max_workers} processes...")
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            # map preserves order
            for result_segment in executor.map(_chunk_segment, tasks):
                final_chunks.extend(result_segment)
    
    # Final pass to assign a clean sequential chunk_index globally
    for idx, chunk in enumerate(final_chunks):
        chunk['metadata']['chunk_index'] = idx

    return final_chunks
