import time
import copy
import nltk
from typing import List, Dict, Any

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
    final_chunks = []
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
            # If adding the next sentence doesn't exceed the target, add it.
            if current_word_count + sentence_word_count <= target_chunk_words:
                current_group.append(sentence)
                current_word_count += sentence_word_count
            # Otherwise, finalize the current group and start a new one.
            else:
                sentence_groups.append(current_group)
                current_group = [sentence]
                current_word_count = sentence_word_count
        # Add the last remaining group.
        if current_group:
            sentence_groups.append(current_group)

        # 3. Create final chunks with sentence-based overlap.
        for i, group in enumerate(sentence_groups):
            chunk_text = " ".join(group)
            
            # a. Determine the overlap from the previous chunk.
            # For any chunk after the first one, prepend the last few sentences
            # from the *previous* group to create a contextual overlap.
            if i > 0 and overlap_sentences > 0:
                # Get the last `overlap_sentences` from the previous group.
                overlap_text = " ".join(sentence_groups[i-1][-overlap_sentences:])
                chunk_text = overlap_text + " " + chunk_text

            # b. Create a new record for each chunk, preserving all metadata.
            chunk_metadata = copy.deepcopy(block['metadata'])
            
            # c. Add final, chunk-specific metadata.
            chunk_metadata['chunk_index'] = len(final_chunks)
            chunk_metadata['ingest_timestamp'] = time.time()

            final_chunks.append({
                "text": chunk_text,
                "metadata": chunk_metadata
            })
            
    return final_chunks
