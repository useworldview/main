"""
UseWorldview Backend — FastAPI Application

Supports unified mode (API + worker in one process) for Cloud Run deployment.
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

# Fix for Windows: Playwright needs ProactorEventLoop for subprocess support.
# Uvicorn defaults to SelectorEventLoop on Windows, which causes NotImplementedError.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

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
    logger.info(f"UseWorldview Backend starting (env={settings.env}, mode={settings.run_mode})")
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

    # In unified mode, check for any orphaned pending jobs on startup
    if settings.run_mode == "unified":
        try:
            from app.jobs.queue import has_pending_or_running_jobs
            if has_pending_or_running_jobs():
                logger.info("[UNIFIED] Found pending jobs on startup, waking worker...")
                from app.jobs.worker import wake_worker
                wake_worker()
        except Exception as e:
            logger.warning(f"[UNIFIED] Startup job check failed: {e}")

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
_settings_for_cors = get_settings()
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
]
if _settings_for_cors.frontend_url:
    allowed_origins.append(_settings_for_cors.frontend_url)
# Allow any *.vercel.app subdomain
allowed_origins.append("https://*.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(studies_router)


# ============================================================================
# Internal endpoints (not for external clients)
# ============================================================================

@app.post("/internal/wake-worker")
async def internal_wake_worker():
    """
    Wake the background worker to process pending jobs.
    This is called automatically by enqueue_job() in unified mode,
    but can also be called manually to force a wake-up.
    """
    settings = get_settings()
    if settings.run_mode != "unified":
        return {"status": "skipped", "reason": "not in unified mode"}

    from app.jobs.worker import wake_worker, is_worker_running
    wake_worker()
    return {
        "status": "ok",
        "worker_running": is_worker_running(),
    }


@app.get("/internal/worker-status")
async def internal_worker_status():
    """Check the background worker status."""
    settings = get_settings()
    if settings.run_mode != "unified":
        return {"status": "not_applicable", "run_mode": settings.run_mode}

    from app.jobs.worker import is_worker_running
    from app.jobs.queue import has_pending_or_running_jobs

    return {
        "worker_running": is_worker_running(),
        "has_pending_jobs": has_pending_or_running_jobs(),
        "run_mode": settings.run_mode,
    }


@app.post("/internal/webhook/process-job")
async def internal_webhook_process_job(
    request: Request,
    authorization: str = Header(None)
):
    """
    Supabase Database Webhook handler.
    Called when a new job is inserted into `agent_jobs`.
    Runs the job synchronously to ensure Cloud Run CPU remains allocated.
    """
    settings = get_settings()
    
    if settings.run_mode != "webhook":
        return {"status": "skipped", "reason": "not in webhook mode"}

    if not settings.webhook_secret:
        logger.error("Webhook secret is not configured")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    # Verify authorization header (Bearer token)
    expected_header = f"Bearer {settings.webhook_secret}"
    if authorization != expected_header:
        raise HTTPException(status_code=401, detail="Unauthorized")

    payload = await request.json()
    
    if payload.get("type") != "INSERT":
        return {"status": "skipped", "reason": "not an insert event"}

    # We use claim_jobs to safely pick up the next pending job.
    # This avoids race conditions if multiple webhooks fire concurrently.
    from app.jobs.queue import claim_jobs
    from app.jobs.worker import dispatch_job
    import uuid
    
    worker_id = f"webhook-{uuid.uuid4().hex[:8]}"
    
    # Claim 1 job from the queue
    jobs = claim_jobs(worker_id=worker_id, limit=1)
    
    if not jobs:
        return {"status": "skipped", "reason": "no pending jobs found"}
        
    job = jobs[0]
    
    # Run the job synchronously in the HTTP request to keep Cloud Run alive
    await dispatch_job(job)
    
    return {"status": "ok", "job_id": job["id"]}
