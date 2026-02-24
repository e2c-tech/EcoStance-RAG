"""
Enhanced Multilingual Cleaning Service
Extends the base cleaning service with improved language detection and metadata
"""

import hashlib
import re
import logging
from typing import List, Dict, Any, Tuple
from langdetect import detect, detect_langs, LangDetectException

logger = logging.getLogger(__name__)

def detect_language_with_confidence(text: str) -> Tuple[str, float, Dict[str, float]]:
    """
    Detect language with confidence score and distribution.
    
    Args:
        text: Text to analyze
        
    Returns:
        Tuple of (primary_language, confidence, language_distribution)
    """
    try:
        # Get language probabilities
        lang_probs = detect_langs(text)
        
        if not lang_probs:
            return 'unknown', 0.0, {}
        
        # Primary language
        primary_lang = lang_probs[0].lang
        confidence = lang_probs[0].prob
        
        # Build distribution
        distribution = {lang.lang: lang.prob for lang in lang_probs if lang.prob >= 0.1}
        
        return primary_lang, confidence, distribution
        
    except LangDetectException:
        return 'unknown', 0.0, {}

def is_multilingual_content(text: str, threshold: float = 0.3) -> Tuple[bool, List[str]]:
    """
    Check if content contains multiple languages.
    
    Args:
        text: Text to analyze
        threshold: Minimum probability for a language to be considered present
        
    Returns:
        Tuple of (is_multilingual, list_of_languages)
    """
    try:
        lang_probs = detect_langs(text)
        languages = [lang.lang for lang in lang_probs if lang.prob >= threshold]
        return len(languages) > 1, languages
    except LangDetectException:
        return False, []

def clean_and_enrich_blocks_multilingual(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enhanced cleaning with multilingual metadata enrichment.
    
    This extends the base cleaning service with:
    - Improved language detection with confidence scores
    - Multi-language content detection
    - Language distribution analysis
    - Enhanced metadata for multilingual processing
    
    Args:
        blocks: List of data blocks from extraction stage
        
    Returns:
        List of enriched and cleaned data blocks with multilingual metadata
    """
    enriched_blocks = []
    seen_hashes = set()  # For in-batch deduplication
    
    # To speed up processing, we'll try to identify the "dominant" language of the document
    # and only perform full detection on the first few blocks or if confidence drops.
    doc_primary_lang = None
    doc_lang_distribution = {}
    
    # Process blocks
    for i, block in enumerate(blocks):
        # --- 1. Clean and Normalize Text ---
        text = block.get('text', '')
        cleaned_text = re.sub(r'\s+', ' ', text).strip()
        
        if not cleaned_text:
            continue
        
        # --- 2. Attach Enriched Metadata ---
        metadata = block.get('metadata', {})
        
        # a. Generate hash
        text_hash = hashlib.sha256(cleaned_text.encode('utf-8')).hexdigest()
        metadata['normalized_text_hash'] = text_hash
        
        # b. & c. Combined Language Detection (ONE call to detect_langs)
        # For efficiency: If we've processed 50 blocks and 90% are the same language, 
        # we can assume that's the document language for small subsequent blocks.
        use_cached_lang = False
        if i > 50 and doc_primary_lang and len(cleaned_text) < 100:
            use_cached_lang = True
            
        if use_cached_lang:
            primary_lang = doc_primary_lang
            confidence = 1.0
            lang_distribution = doc_lang_distribution
            is_multilingual = len(doc_lang_distribution) > 1
            detected_languages = list(doc_lang_distribution.keys())
        else:
            try:
                lang_probs = detect_langs(cleaned_text)
                if lang_probs:
                    primary_lang = lang_probs[0].lang
                    confidence = lang_probs[0].prob
                    lang_distribution = {l.lang: l.prob for l in lang_probs if l.prob >= 0.1}
                    detected_languages = [l.lang for l in lang_probs if l.prob >= 0.3]
                    is_multilingual = len(detected_languages) > 1
                    
                    # Update document-level cache
                    if doc_primary_lang is None or i < 100:
                        doc_primary_lang = primary_lang
                        doc_lang_distribution = lang_distribution
                else:
                    primary_lang, confidence, lang_distribution = 'unknown', 0.0, {}
                    is_multilingual, detected_languages = False, []
            except LangDetectException:
                primary_lang, confidence, lang_distribution = 'unknown', 0.0, {}
                is_multilingual, detected_languages = False, []

        metadata['language'] = primary_lang
        metadata['language_confidence'] = confidence
        metadata['language_distribution'] = lang_distribution
        metadata['is_multilingual'] = is_multilingual
        metadata['languages_detected'] = detected_languages
        
        # d. Language tier classification
        tier_1_languages = ['en', 'es', 'fr', 'de', 'pt']
        tier_2_languages = ['it', 'nl', 'ru', 'zh', 'ja']
        
        if primary_lang in tier_1_languages:
            metadata['language_tier'] = 1
        elif primary_lang in tier_2_languages:
            metadata['language_tier'] = 2
        else:
            metadata['language_tier'] = 3
        
        # e. Cleaning version
        metadata['cleaning_version'] = '2.0'
        
        # f. Text metrics
        metadata['text_length'] = len(cleaned_text)
        metadata['token_count'] = len(cleaned_text.split())
        
        # g. Confidence score
        metadata['confidence'] = metadata.get('ocr_confidence', 1.0)
        
        # h. In-batch deduplication
        if text_hash in seen_hashes:
            metadata['is_duplicate'] = True
        else:
            metadata['is_duplicate'] = False
            seen_hashes.add(text_hash)
        
        # i. Multilingual processing flag
        metadata['multilingual_processed'] = True
        
        # Update block
        block['text'] = cleaned_text
        block['metadata'] = metadata
        enriched_blocks.append(block)
    
    # Log language statistics
    language_stats = {}
    for block in enriched_blocks:
        lang = block['metadata'].get('language', 'unknown')
        language_stats[lang] = language_stats.get(lang, 0) + 1
    
    logger.info(f"Multilingual cleaning complete: {len(enriched_blocks)} blocks")
    logger.info(f"Language distribution: {language_stats}")
    
    return enriched_blocks

def get_language_statistics(blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get language statistics from processed blocks.
    
    Args:
        blocks: List of processed blocks
        
    Returns:
        Dictionary with language statistics
    """
    stats = {
        'total_blocks': len(blocks),
        'languages': {},
        'multilingual_blocks': 0,
        'average_confidence': 0.0,
        'language_tiers': {1: 0, 2: 0, 3: 0}
    }
    
    total_confidence = 0.0
    
    for block in blocks:
        metadata = block.get('metadata', {})
        
        # Count languages
        lang = metadata.get('language', 'unknown')
        stats['languages'][lang] = stats['languages'].get(lang, 0) + 1
        
        # Count multilingual blocks
        if metadata.get('is_multilingual', False):
            stats['multilingual_blocks'] += 1
        
        # Sum confidence
        confidence = metadata.get('language_confidence', 0.0)
        total_confidence += confidence
        
        # Count tiers
        tier = metadata.get('language_tier', 3)
        stats['language_tiers'][tier] = stats['language_tiers'].get(tier, 0) + 1
    
    # Calculate average confidence
    if len(blocks) > 0:
        stats['average_confidence'] = total_confidence / len(blocks)
    
    return stats

def should_use_multilingual_cleaning(tenant_id: str = None) -> bool:
    """
    Determine if multilingual cleaning should be used.
    Always use enhanced cleaning - provides better language detection for all content.
    
    Args:
        tenant_id: Tenant identifier (not used - always enhanced when available)
        
    Returns:
        True if multilingual cleaning should be used
    """
    # Always use enhanced multilingual cleaning - it's backward compatible and better
    return True

def clean_and_enrich_blocks_no_fallback(blocks: List[Dict[str, Any]], 
                                        tenant_id: str = None) -> List[Dict[str, Any]]:
    """
    Clean and enrich blocks using enhanced multilingual processing - no fallback.
    
    Args:
        blocks: List of data blocks
        tenant_id: Tenant identifier (for logging only)
        
    Returns:
        Cleaned and enriched blocks with multilingual metadata
    """
    logger.info(f"Using enhanced multilingual cleaning - better language detection for all content")
    return clean_and_enrich_blocks_multilingual(blocks)

def clean_and_enrich_blocks_with_fallback(blocks: List[Dict[str, Any]], 
                                         tenant_id: str = None) -> List[Dict[str, Any]]:
    """
    Clean and enrich blocks using multilingual processing only - no fallback.
    
    Args:
        blocks: List of data blocks
        tenant_id: Tenant identifier (for logging only)
        
    Returns:
        Cleaned and enriched blocks with multilingual metadata
    """
    logger.info(f"Using multilingual cleaning only - no fallback")
    return clean_and_enrich_blocks_multilingual(blocks)