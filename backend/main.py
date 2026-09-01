"""RecoverAI — AI Revenue Recovery Agent.

Entry point for the FastAPI backend.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api.router import api_router
from app.schemas.schemas import HealthResponse, ConfigResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables. Shutdown: nothing special."""
    init_db()
    yield


app = FastAPI(
    title="RecoverAI",
    description="AI Revenue Recovery Agent — Detect, Diagnose, Decide, Act, Observe, Recover",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend and Vercel preview deployments
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["health"])
def root():
    """Root endpoint for deployment health checks."""
    return {
        "name": "RecoverAI API",
        "status": "online",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health",
    }

# ── Health & Config ──
@app.get("/api/health", response_model=HealthResponse, tags=["health"])
def health():
    """Health check endpoint."""
    return HealthResponse(
        mode=settings.recovery_mode,
        demo_mode=settings.demo_mode,
    )


@app.get("/api/config", response_model=ConfigResponse, tags=["health"])
def config():
    """Non-secret configuration."""
    return ConfigResponse(
        recovery_mode=settings.recovery_mode,
        demo_mode=settings.demo_mode,
        recovery_probability_threshold=settings.recovery_probability_threshold,
        scorer_confidence_threshold=settings.scorer_confidence_threshold,
        auto_recovery_amount_limit=settings.auto_recovery_amount_limit,
        max_retries=settings.max_retries,
    )


# ── Sub-routers ──
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
