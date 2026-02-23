"""
Multilingual Configuration for App Services
Centralized configuration for multilingual features in the app layer
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Multilingual Feature Flags ---
MULTILINGUAL_ENABLED = os.getenv("MULTILINGUAL_ENABLED", "false").lower() == "true"
EMBEDDING_MODEL_TYPE = os.getenv("EMBEDDING_MODEL_TYPE", "huggingface")  # huggingface or bge-m3
FALLBACK_TO_LEGACY = os.getenv("FALLBACK_TO_LEGACY", "true").lower() == "true"

# Note: Individual tenant control is now managed via the 'multilingual' feature 
# flag in the tenant.settings JSON in the database.

# --- BGE-M3 Configuration ---
BGE_M3_MODEL_NAME = "BAAI/bge-m3"
BGE_M3_EMBEDDING_DIMENSION = 1024
BGE_M3_MAX_SEQUENCE_LENGTH = 8192
BGE_M3_BATCH_SIZE = int(os.getenv("BGE_M3_BATCH_SIZE", "128"))
BGE_M3_NORMALIZE = os.getenv("BGE_M3_NORMALIZE", "true").lower() == "true"
BGE_M3_DEVICE = os.getenv("BGE_M3_DEVICE", "auto")  # auto, cpu, cuda

# --- Language Detection Configuration ---
LANGUAGE_DETECTION_ENABLED = os.getenv("LANGUAGE_DETECTION_ENABLED", "true").lower() == "true"
LANGUAGE_DETECTION_MIN_CONFIDENCE = float(os.getenv("LANGUAGE_DETECTION_MIN_CONFIDENCE", "0.7"))
LANGUAGE_DETECTION_MIN_TEXT_LENGTH = int(os.getenv("LANGUAGE_DETECTION_MIN_TEXT_LENGTH", "10"))

# --- Processing Configuration ---
MULTILINGUAL_PROCESSING_ENABLED = os.getenv("MULTILINGUAL_PROCESSING_ENABLED", "true").lower() == "true"
AUTO_DETECT_MULTILINGUAL_CONTENT = os.getenv("AUTO_DETECT_MULTILINGUAL_CONTENT", "true").lower() == "true"

# --- RAG & Search Configuration ---
CROSS_LANGUAGE_ENABLED = os.getenv("CROSS_LANGUAGE_ENABLED", "true").lower() == "true"
SAME_LANGUAGE_BOOST = float(os.getenv("SAME_LANGUAGE_BOOST", "1.5"))
CROSS_LANGUAGE_MIN_SIMILARITY = float(os.getenv("CROSS_LANGUAGE_MIN_SIMILARITY", "0.5"))
MAX_CROSS_LANGUAGE_RESULTS = int(os.getenv("MAX_CROSS_LANGUAGE_RESULTS", "10"))
LOG_CROSS_LANGUAGE_RETRIEVAL = os.getenv("LOG_CROSS_LANGUAGE_RETRIEVAL", "true").lower() == "true"

# --- Collection Naming ---
MULTILINGUAL_COLLECTION_SUFFIX = "_ml"
LEGACY_COLLECTION_SUFFIX = ""

# --- Language Support with BGE-M3 ---
# BGE-M3 supports 100+ languages with high quality embeddings
# All languages are supported equally - no artificial tiers needed

# Common languages for reference (BGE-M3 supports many more)
COMMON_LANGUAGES = [
    "en", "es", "fr", "de", "pt", "it", "nl", "ru", "zh", "ja", 
    "ko", "ar", "hi", "th", "vi", "tr", "pl", "cs", "hu", "ro",
    "bg", "hr", "sk", "sl", "et", "lv", "lt", "fi", "sv", "da",
    "no", "is", "ga", "mt", "cy", "eu", "ca", "gl", "ast", "an",
    "oc", "co", "sc", "rm", "fur", "lld", "vec", "lmo", "pms",
    "lij", "nap", "scn", "srd", "el", "mk", "sr", "bs", "me",
    "sq", "be", "uk", "kk", "ky", "uz", "tg", "mn", "hy", "ka",
    "az", "fa", "ps", "ur", "sd", "ne", "si", "my", "km", "lo",
    "ka", "am", "ti", "om", "so", "sw", "zu", "xh", "af", "st",
    "tn", "ts", "ve", "nr", "ss", "nso", "yo", "ig", "ha", "ff",
    "wo", "bm", "ln", "kg", "lua", "rw", "rn", "ny", "sn", "mg"
]

# Legacy tier definitions (kept for backward compatibility but not used for BGE-M3)
TIER_1_LANGUAGES = COMMON_LANGUAGES[:20]  # First 20 for compatibility
TIER_2_LANGUAGES = COMMON_LANGUAGES[20:40]  # Next 20 for compatibility  
TIER_3_LANGUAGES = []  # BGE-M3 handles all languages equally

# --- Performance Configuration ---
MULTILINGUAL_CACHE_ENABLED = os.getenv("MULTILINGUAL_CACHE_ENABLED", "true").lower() == "true"
MULTILINGUAL_CACHE_TTL = int(os.getenv("MULTILINGUAL_CACHE_TTL", "3600"))  # 1 hour
EMBEDDING_CACHE_SIZE = int(os.getenv("EMBEDDING_CACHE_SIZE", "1000"))

# --- Logging Configuration ---
MULTILINGUAL_LOG_LEVEL = os.getenv("MULTILINGUAL_LOG_LEVEL", "INFO")
LOG_LANGUAGE_DETECTION = os.getenv("LOG_LANGUAGE_DETECTION", "true").lower() == "true"
LOG_EMBEDDING_PERFORMANCE = os.getenv("LOG_EMBEDDING_PERFORMANCE", "true").lower() == "true"

def initialize_multilingual_config():
    """Initialize multilingual configuration in app services."""
    if MULTILINGUAL_ENABLED:
        # Configure multilingual embedding service
        from ..services.multilingual_embedding_service import set_multilingual_config
        set_multilingual_config(
            enabled=True,
            model_name=BGE_M3_MODEL_NAME,
            batch_size=BGE_M3_BATCH_SIZE
        )
        
        print(f"✓ Multilingual features initialized")
        print(f"  - Model: {BGE_M3_MODEL_NAME}")
        print(f"  - Dimension: {BGE_M3_EMBEDDING_DIMENSION}")
        print(f"  - Batch size: {BGE_M3_BATCH_SIZE}")
        print(f"  - Supported languages: Tier 1: {TIER_1_LANGUAGES}")
    else:
        print("ℹ Multilingual features disabled")

def is_tenant_multilingual_enabled(tenant_id: str, db=None) -> bool:
    """
    Check if multilingual features are enabled for a specific tenant.
    
    This replaces the dual control (global flag + whitelist) with 
    global flag + specific tenant feature level check.
    """
    if not MULTILINGUAL_ENABLED:
        return False
    
    if not tenant_id:
        return False
        
    # Use provided session or create a temporary one
    close_session = False
    if db is None:
        try:
            from ..db.database import SessionLocal
            db = SessionLocal()
            close_session = True
        except ImportError:
            logger.error("Could not import SessionLocal for multilingual check")
            return False

    try:
        from ..models.tenant import Tenant
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            return False
            
        settings = tenant.settings or {}
        features = settings.get("features", [])
        return "multilingual" in features
    except Exception as e:
        logger.error(f"Error checking multilingual status for tenant {tenant_id}: {e}")
        return False
    finally:
        if close_session:
            db.close()

def get_multilingual_collection_name(tenant_id: str, kb_name: str) -> str:
    """Generate multilingual collection name for a tenant and knowledge base."""
    # Import here to avoid circular imports
    try:
        from ..services.tenant_service import TenantService
        base_name = f"{TenantService._sanitize_name(tenant_id)}_{TenantService._sanitize_name(kb_name)}"
    except ImportError:
        # Fallback if tenant service not available
        base_name = f"{tenant_id}_{kb_name}".replace("-", "_").lower()
    
    return f"{base_name}{MULTILINGUAL_COLLECTION_SUFFIX}"

def should_use_multilingual_service(tenant_id: str = None) -> bool:
    """Check if multilingual service should be used for a tenant."""
    return is_tenant_multilingual_enabled(tenant_id)

def should_use_multilingual_processing(tenant_id: str = None) -> bool:
    """Determine if multilingual processing should be used."""
    if not MULTILINGUAL_ENABLED or not MULTILINGUAL_PROCESSING_ENABLED:
        return False
    
    if tenant_id and not is_tenant_multilingual_enabled(tenant_id):
        return False
    
    return True

def get_embedding_dimension(use_multilingual: bool = None) -> int:
    """Get the appropriate embedding dimension."""
    if use_multilingual is None:
        use_multilingual = MULTILINGUAL_ENABLED
    
    if use_multilingual:
        return BGE_M3_EMBEDDING_DIMENSION
    else:
        return 384  # Default for all-MiniLM-L6-v2

def get_language_tier(language: str) -> int:
    """
    Get the support tier for a language.
    With BGE-M3, all languages are supported equally (tier 1).
    """
    # BGE-M3 provides high-quality embeddings for all languages
    return 1  # All languages are tier 1 with BGE-M3

def get_multilingual_config_info() -> dict:
    """Get current multilingual configuration information."""
    return {
        "multilingual_enabled": MULTILINGUAL_ENABLED,
        "processing_enabled": MULTILINGUAL_PROCESSING_ENABLED,
        "embedding_model_type": EMBEDDING_MODEL_TYPE,
        "bge_m3_config": {
            "model_name": BGE_M3_MODEL_NAME,
            "dimension": BGE_M3_EMBEDDING_DIMENSION,
            "max_length": BGE_M3_MAX_SEQUENCE_LENGTH,
            "batch_size": BGE_M3_BATCH_SIZE,
            "normalize": BGE_M3_NORMALIZE,
            "device": BGE_M3_DEVICE
        },
        "language_support": {
            "tier_1": TIER_1_LANGUAGES,
            "tier_2": TIER_2_LANGUAGES,
            "detection_enabled": LANGUAGE_DETECTION_ENABLED,
            "min_confidence": LANGUAGE_DETECTION_MIN_CONFIDENCE
        },
        "collection_suffix": MULTILINGUAL_COLLECTION_SUFFIX,
        "fallback_enabled": FALLBACK_TO_LEGACY
    }