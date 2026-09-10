"""
UseWorldview Backend — FastAPI Application
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.routes.studies import router as studies_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    settings = get_settings()
    logger.info(f"UseWorldview Backend starting (env={settings.env})")
    logger.info(f"LLM fallback order: {settings.llm_providers}")

    # Install Playwright browsers on first run (dev only)
    if settings.env == "development":
        try:
            import subprocess
            subprocess.run(
                ["python", "-m", "playwright", "install", "chromium"],
                check=False,
                capture_output=True,
            )
            logger.info("Playwright Chromium installed/verified")
        except Exception as e:
            logger.warning(f"Playwright install check failed: {e}")

    # Ensure screenshots bucket exists and is public
    try:
        from app.core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        buckets = [b.name for b in sb.storage.list_buckets()]
        if "screenshots" not in buckets:
            sb.storage.create_bucket("screenshots", options={"public": True})
            logger.info("Created 'screenshots' storage bucket (public=True)")
        else:
            sb.storage.update_bucket("screenshots", {"public": True})
    except Exception as e:
        logger.warning(f"Storage bucket check: {e}")

    yield
    logger.info("UseWorldview Backend shutting down")


# Create FastAPI app
app = FastAPI(
    title="UseWorldview API",
    description="AI-powered synthetic user research platform — backend orchestration layer",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the frontend to call us
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(studies_router)
