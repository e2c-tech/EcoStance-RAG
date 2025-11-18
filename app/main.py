from fastapi import FastAPI
from contextlib import asynccontextmanager

from .routers import upload, qdrant_upload, query_router, management_router, db_router
from .services.cleanup_service import cleanup_service
from .config import ENABLE_REACT_AGENT

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await cleanup_service.start()
    yield
    # Shutdown
    await cleanup_service.stop()

app = FastAPI(lifespan=lifespan)

app.include_router(upload.router, prefix="/api/v1", tags=["1. File Upload"])
app.include_router(qdrant_upload.router, prefix="/api/v1", tags=["2. Processing & Upload"])
app.include_router(query_router.router, prefix="/api/v1", tags=["3. RAG Query"])
app.include_router(management_router.router, prefix="/api/v1/manage", tags=["4. Management"])
app.include_router(db_router.router, prefix="/api/v1", tags=["5. Database Interaction"])

# Beta Feature: ReAct Agent
if ENABLE_REACT_AGENT:
    from .routers import agent_router_beta
    app.include_router(agent_router_beta.router, prefix="/api/v1/beta", tags=["🧪 Beta: AI Agent"])


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
