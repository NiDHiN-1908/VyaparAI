# backend/main.py
import uvicorn
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.routers import business, marketing, lead, sales, analytics

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("vyaparai.main")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Policy configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production environments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount media static directory to serve generated MP3s and MP4s
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

# Register modular routers
app.include_router(business.router)
app.include_router(marketing.router)
app.include_router(lead.router)
app.include_router(sales.router)
app.include_router(analytics.router)

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global server error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "An unexpected error occurred on the server.", "details": str(exc)}
    )

@app.get("/")
async def root_health_check():
    """Health check endpoint confirming API status and active database/agent configurations."""
    from backend.database.connection import db_conn
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "database_mode": "Mock (In-Memory)" if db_conn.is_mock else "Supabase Real-Time Connected",
        "ollama_host": settings.OLLAMA_BASE_URL,
        "ollama_model": settings.OLLAMA_MODEL
    }

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
