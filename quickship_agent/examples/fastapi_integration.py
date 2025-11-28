"""
FastAPI Integration Example for QuickShip AI Agent
"""

from fastapi import FastAPI
from quickship_agent.router import router as agent_router

# Create FastAPI app
app = FastAPI(
    title="QuickShip AI Agent API",
    description="Conversational AI for logistics and customer service",
    version="1.0.0"
)

# Include the agent router
app.include_router(agent_router, prefix="/api/v1", tags=["Agent"])

# Add a health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "QuickShip AI Agent"}

# Run with: uvicorn fastapi_integration:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
