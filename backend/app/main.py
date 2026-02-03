"""FastAPI application entry point."""
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Add backend directory to path for imports
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.config import settings
from app.routers import search, businesses, research, seo


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - runs on startup and shutdown."""
    # Startup
    init_db()
    
    # Validate configuration
    errors = settings.validate()
    if errors:
        print("⚠️  Configuration warnings:")
        for error in errors:
            print(f"   - {error}")
    else:
        print("✅ Configuration validated")
    
    print(f"📊 Monthly API limit: {settings.MONTHLY_API_LIMIT} calls")
    
    yield  # Application runs here
    
    # Shutdown (cleanup if needed)


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Lead Generation Tool",
    description="Find local businesses using Google Places API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - explicit origins for security
# Add your production URL(s) to this list
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",  # If running frontend separately
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include routers
app.include_router(search.router)
app.include_router(businesses.router)
app.include_router(research.router)
app.include_router(seo.router)

# Serve frontend static files
frontend_path = Path(__file__).parent.parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    errors = settings.validate()
    return {
        "status": "healthy" if not errors else "degraded",
        "config_errors": errors,
        "api_key_configured": bool(settings.GOOGLE_MAPS_API_KEY)
    }

