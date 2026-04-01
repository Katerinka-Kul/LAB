from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import uvicorn

from database.connection import init_db
from routes.users import user_router
from routes.events import event_router
from semantic import setup_semantic_routes

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")
    
    yield
    
    # Shutdown
    print("Shutting down...")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Soulmate API",
    description="API for Soulmate - Find Your Match application",
    version="1.0.0",
    lifespan=lifespan  # Use lifespan instead of on_event
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Root endpoint
@app.get("/")
async def root():
    """Serve the main HTML page"""
    return FileResponse("static/index.html")

# Include routers
app.include_router(user_router)  # All user-related endpoints (including admin and notifications)
app.include_router(event_router, prefix="/event")

# Setup semantic search routes (НОВАЯ СТРОЧКА)
setup_semantic_routes(app)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Soulmate API",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
