from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from .routers import upload, qdrant_upload, query_router, management_router, db_router, auth_router, file_router, tenant_router, admin_router, usage_router, quota_router, metrics_router, public_chat_router, public_agent_router, llm_usage_router, cache_router, system_router, tenant_roles, permissions, admin, tenant_users, gmail_router, dynamics_router, custom_crm_router, billing_router
from .services.cleanup_service import cleanup_service
from .services.scheduler_service import start_scheduler, stop_scheduler
from .middleware.auth_middleware import AuthMiddleware
from .middleware.rate_limiter import RateLimitMiddleware
from .middleware.validation_middleware import ValidationMiddleware
from .middleware.usage_tracking_middleware import UsageTrackingMiddleware
# LangSmith middleware removed - limiting tracing to embedding, RAG, and agent only

# Import QuickShip AI Agent
from .routers.beta_agent_router import router as agent_router

# === BEGIN: branch error handling ===
# Import new error handling infrastructure
from .core.logging import setup_structured_logging, get_logger
from .core.error_handlers import (
    base_app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler
)
from .core.exceptions import BaseAppException
from .middleware.request_id_middleware import RequestIDMiddleware
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Setup structured logging
setup_structured_logging(
    log_level="INFO",
    enable_console=True,
    enable_file=True,
    error_file="errorlog.txt"
)

# Get structured logger
logger = get_logger(__name__)
# === END: branch error handling ===

# Legacy logging configuration (kept for backward compatibility)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

file_handler = logging.FileHandler('errorlog.txt', mode='a')
file_handler.setLevel(logging.ERROR)  # Only log ERROR and above to file

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[console_handler, file_handler]
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # === BEGIN: branch error handling ===
    # Startup with enhanced error handling
    logger.info("🚀 Starting application...")
    
    # Initialize singletons with graceful error handling
    from .services.qdrant_service import get_qdrant_client
    from .services.embedding_service import load_embedding_model
    from .services.langsmith_service import langsmith_service
    from .core.logging import log_error_with_context
    
    try:
        # Initialize LangSmith tracing
        if langsmith_service.is_enabled():
            logger.info("✓ LangSmith tracing enabled")
        else:
            logger.info("ℹ LangSmith tracing disabled")
    except Exception as e:
        log_error_with_context(
            logger=logger,
            message="Failed to initialize LangSmith service",
            error=e,
            remediation="Check LangSmith API key and configuration"
        )
    
    try:
        # Pre-load Qdrant client
        get_qdrant_client()
        logger.info("✓ Qdrant client initialized")
    except Exception as e:
        log_error_with_context(
            logger=logger,
            message="Failed to initialize Qdrant client",
            error=e,
            remediation="Check Qdrant connection settings and ensure service is running"
        )
    
    try:
        # Pre-load embedding model
        load_embedding_model()
        logger.info("✓ Embedding model loaded")
    except Exception as e:
        log_error_with_context(
            logger=logger,
            message="Failed to load embedding model",
            error=e,
            remediation="Check model configuration and available memory"
        )
    
    # Start services with error handling
    try:
        await cleanup_service.start()
        logger.info("✓ Cleanup service started")
    except Exception as e:
        log_error_with_context(
            logger=logger,
            message="Failed to start cleanup service",
            error=e,
            remediation="Check database connectivity and permissions"
        )
    
    try:
        start_scheduler()
        logger.info("✓ Scheduler started")
    except Exception as e:
        log_error_with_context(
            logger=logger,
            message="Failed to start scheduler",
            error=e,
            remediation="Check system resources and permissions"
        )
    
    logger.info("✓ Application started successfully")
    # === END: branch error handling ===
    
    yield
    
    # === BEGIN: branch error handling ===
    # Shutdown with enhanced error handling
    logger.info("🛑 Shutting down application...")
    
    try:
        stop_scheduler()
        logger.info("✓ Scheduler stopped")
    except Exception as e:
        log_error_with_context(
            logger=logger,
            message="Error stopping scheduler",
            error=e
        )
    
    try:
        await cleanup_service.stop()
        logger.info("✓ Cleanup service stopped")
    except Exception as e:
        log_error_with_context(
            logger=logger,
            message="Error stopping cleanup service",
            error=e
        )
    
    # Close connections with error handling
    from .services.qdrant_service import close_qdrant_client
    from .services.embedding_service import unload_embedding_model
    from .db.database import close_db_connections
    
    try:
        close_qdrant_client()
        logger.info("✓ Qdrant client closed")
    except Exception as e:
        log_error_with_context(
            logger=logger,
            message="Error closing Qdrant client",
            error=e
        )
    
    try:
        unload_embedding_model()
        logger.info("✓ Embedding model unloaded")
    except Exception as e:
        log_error_with_context(
            logger=logger,
            message="Error unloading embedding model",
            error=e
        )
    
    try:
        close_db_connections()
        logger.info("✓ Database connections closed")
    except Exception as e:
        log_error_with_context(
            logger=logger,
            message="Error closing database connections",
            error=e
        )
    
    logger.info("✓ Application shutdown complete")
    # === END: branch error handling ===

app = FastAPI(lifespan=lifespan)

# # Add CORS middleware - set to '*' to let the infrastructure handle security/CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# === BEGIN: branch error handling ===
# Add global exception handlers
app.add_exception_handler(BaseAppException, base_app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)
# === END: branch error handling ===



# === BEGIN: branch error handling ===
# Add middleware (order matters: request ID -> langsmith -> validation -> rate limiter -> auth -> usage tracking)
app.add_middleware(UsageTrackingMiddleware)  # Last (logs after response)
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(ValidationMiddleware)
# LangSmith HTTP middleware removed - only tracing embedding, RAG, and agent
app.add_middleware(RequestIDMiddleware)  # First (sets up request context)
# === END: branch error handling ===

app.include_router(auth_router.router, prefix="/api/v1", tags=["0. Authentication"])
app.include_router(tenant_router.router, prefix="/api/v1", tags=["1. Tenant Management"])
app.include_router(tenant_roles.router, tags=["1a. Tenant Role Management"])
app.include_router(permissions.router, tags=["1b. Permission Management"])
app.include_router(usage_router.router, tags=["2. Usage Analytics"])
app.include_router(quota_router.router, tags=["3. Quotas & Limits"])
app.include_router(metrics_router.router, tags=["4. Metrics & Monitoring"])
app.include_router(upload.router, prefix="/api/v1", tags=["5. File Upload"])
app.include_router(qdrant_upload.router, prefix="/api/v1", tags=["6. Processing & Upload"])
app.include_router(query_router.router, prefix="/api/v1", tags=["7. RAG Query"])
app.include_router(management_router.router, prefix="/api/v1/manage", tags=["8. KB Management"])
app.include_router(db_router.router, prefix="/api/v1", tags=["9. Database Interaction"])
app.include_router(file_router.router, prefix="/api/v1", tags=["10. File Management"])
app.include_router(admin_router.router, tags=["11. Admin"])
app.include_router(admin.router, tags=["11a. System Administration (Enhanced)"])
app.include_router(agent_router, prefix="/api/v1/beta", tags=["12. AI Agent (Beta)"])
app.include_router(public_chat_router.router, tags=["13. Public Chat"])
app.include_router(public_agent_router.router, tags=["14. Public Agent"])
app.include_router(llm_usage_router.router, tags=["15. LLM Usage & Monitoring"])
app.include_router(cache_router.router, prefix="/api/v1", tags=["16. Cache Management"])
app.include_router(system_router.router, prefix="/api/v1", tags=["17. System Monitoring"])
app.include_router(tenant_users.router, tags=["18. Tenant User Management"])
app.include_router(gmail_router.router, tags=["19. Gmail Integration"])
app.include_router(dynamics_router.router, tags=["20. Dynamics Integration"])
app.include_router(custom_crm_router.router, tags=["21. Custom CRM Integration"])
app.include_router(billing_router.router, prefix="/api/v1", tags=["22. Billing & Payments"])


@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "RAG Processing API",
        "cleanup_service_running": cleanup_service._running
    }
