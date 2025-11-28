from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .routers import upload, qdrant_upload, query_router, management_router, db_router, auth_router, file_router, tenant_router, admin_router, api_key_router, usage_router, quota_router, metrics_router, public_chat_router, public_agent_router
from .services.cleanup_service import cleanup_service
from .services.scheduler_service import start_scheduler, stop_scheduler
from .middleware.auth_middleware import AuthMiddleware
from .middleware.rate_limiter import RateLimitMiddleware
from .middleware.validation_middleware import ValidationMiddleware
from .middleware.usage_tracking_middleware import UsageTrackingMiddleware

# Import QuickShip AI Agent
from quickship_agent.router import router as agent_router

# Configure logging
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
    # Startup
    await cleanup_service.start()
    start_scheduler()  # Start background scheduler
    yield
    # Shutdown
    stop_scheduler()  # Stop background scheduler
    await cleanup_service.stop()

app = FastAPI(lifespan=lifespan)

# Configure CORS - MUST be added before other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React default
        "http://localhost:3001",
        "http://localhost:5173",  # Vite default
        "http://localhost:8501",  # Streamlit default
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8501",
        # For development, you can also use:
        # "*"  # Allow all origins (NOT recommended for production)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Add middleware (order matters: validation -> rate limiter -> auth -> usage tracking)
app.add_middleware(UsageTrackingMiddleware)  # Last (logs after response)
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(ValidationMiddleware)  # First (validates before processing)

app.include_router(auth_router.router, prefix="/api/v1", tags=["0. Authentication"])
app.include_router(tenant_router.router, prefix="/api/v1", tags=["1. Tenant Management"])
app.include_router(api_key_router.router, tags=["2. API Keys"])
app.include_router(usage_router.router, tags=["3. Usage Analytics"])
app.include_router(quota_router.router, tags=["4. Quotas & Limits"])
app.include_router(metrics_router.router, tags=["5. Metrics & Monitoring"])
app.include_router(upload.router, prefix="/api/v1", tags=["6. File Upload"])
app.include_router(qdrant_upload.router, prefix="/api/v1", tags=["7. Processing & Upload"])
app.include_router(query_router.router, prefix="/api/v1", tags=["8. RAG Query"])
app.include_router(management_router.router, prefix="/api/v1/manage", tags=["9. KB Management"])
app.include_router(db_router.router, prefix="/api/v1", tags=["10. Database Interaction"])
app.include_router(file_router.router, prefix="/api/v1", tags=["11. File Management"])
app.include_router(admin_router.router, tags=["12. Admin"])
app.include_router(agent_router, prefix="/api/v1/beta", tags=["13. AI Agent (Beta)"])
app.include_router(public_chat_router.router, tags=["14. Public Chat"])
app.include_router(public_agent_router.router, tags=["15. Public Agent"])


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
