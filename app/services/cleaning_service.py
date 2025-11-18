import hashlib
import re
from typing import List, Dict, Any
from langdetect import detect, LangDetectException

def clean_and_enrich_blocks(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Cleans the text within each block and enriches the block with system and quality metadata.
    This includes normalizing whitespace, detecting language, and identifying duplicates within the batch.

    Args:
        blocks (List[Dict[str, Any]]): A list of data blocks from the extraction stage.

    Returns:
        The list of enriched and cleaned data blocks.
    """
    enriched_blocks = []
    seen_hashes = set() # Used for in-batch deduplication

    for block in blocks:
        # --- 1. Clean and Normalize Text ---
        # Start with the raw text from the block.
        text = block.get('text', '')
        
        # Normalize all whitespace (spaces, tabs, newlines) to a single space,
        # and strip leading/trailing whitespace. This is crucial for consistent
        # language detection, hashing, and processing by language models.
        cleaned_text = re.sub(r'\s+', ' ', text).strip()

        # If a block has no content after cleaning, skip it.
        if not cleaned_text:
            continue

        # --- 2. Attach Enriched Metadata ---
        metadata = block.get('metadata', {})
        
        # a. Generate a SHA256 hash of the cleaned text. This hash serves as a unique
        # identifier for the content, useful for deduplication and version tracking.
        text_hash = hashlib.sha256(cleaned_text.encode('utf-8')).hexdigest()
        metadata['normalized_text_hash'] = text_hash
        
        # b. Detect the language of the text. If the text is too short or ambiguous,
        # langdetect might throw an error, in which case we mark it as 'unknown'.
        try:
            metadata['language'] = detect(cleaned_text)
        except LangDetectException:
            metadata['language'] = 'unknown'
        
        # c. Add a version for the cleaning process itself. If you change the cleaning
        # logic in the future, you can increment this version to re-process documents.
        metadata['cleaning_version'] = '1.1' # Incremented to reflect new logic
        
        # d. Calculate text length and a simple token count. The token count is an
        # estimate; a more accurate count would use a tokenizer from a specific model.
        metadata['text_length'] = len(cleaned_text)
        metadata['token_count'] = len(cleaned_text.split())

        # e. Calculate a combined confidence score. This starts with the OCR confidence
        # (if available, defaulting to 1.0 for digital text) and could be adjusted
        # by other quality metrics in the future.
        metadata['confidence'] = metadata.get('ocr_confidence', 1.0) 

        # f. Perform in-batch deduplication. Check if we have seen this exact text
        # (as identified by its hash) before in this same processing batch.
        if text_hash in seen_hashes:
            metadata['is_duplicate'] = True
        else:
            metadata['is_duplicate'] = False
            seen_hashes.add(text_hash)

        # Update the block with the cleaned text and the newly enriched metadata
        block['text'] = cleaned_text
        block['metadata'] = metadata
        enriched_blocks.append(block)

    return enriched_blocks
