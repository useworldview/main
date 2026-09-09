"""
Worker poll loop — the async job processor.
Polls agent_jobs, dispatches to the right handler, handles success/failure/retry.
"""

import asyncio
import logging
import signal
import uuid
import traceback
from typing import Optional

from app.core.config import get_settings
from app.jobs.queue import claim_jobs, mark_running, complete_job, fail_job
from app.jobs.job_types import JobType

logger = logging.getLogger(__name__)

# Graceful shutdown flag
_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    _shutdown = True


async def dispatch_job(job: dict) -> None:
    """
    Dispatch a claimed job to the appropriate handler.
    """
    job_type = job["job_type"]
    payload = job["payload"]
    job_id = job["id"]

    logger.info(f"Dispatching job {job_id} type={job_type}")
    mark_running(job_id)

    try:
        if job_type == JobType.ANALYZE_SITE:
            from app.services.site_analysis import analyze_site
            await analyze_site(payload)

        elif job_type == JobType.GENERATE_PERSONAS:
            from app.services.persona_generation import generate_personas
            await generate_personas(payload)

        elif job_type == JobType.RUN_AGENT_SESSION:
            from app.services.agent_session.runner import run_agent_session
            await run_agent_session(payload)

        elif job_type == JobType.ANALYZE_SESSION:
            from app.services.post_session_analysis import analyze_session
            await analyze_session(payload)

        elif job_type == JobType.SYNTHESIZE_STUDY:
            from app.services.cross_persona_analysis import synthesize_study
            await synthesize_study(payload)

        else:
            raise ValueError(f"Unknown job type: {job_type}")

        complete_job(job_id)

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"Job {job_id} failed: {error_msg}")
        fail_job(job_id, str(e))

        # If this is a session job, update the session status
        if job_type == JobType.RUN_AGENT_SESSION:
            try:
                from app.core.supabase_client import get_supabase_client
                sb = get_supabase_client()
                session_id = payload.get("session_id")
                if session_id:
                    sb.table("agent_sessions").update({
                        "status": "failed",
                        "outcome": "error",
                        "outcome_reason": str(e),
                    }).eq("id", session_id).execute()
            except Exception:
                logger.error("Failed to update session status after job failure")


async def run_worker():
    """
    Main worker loop. Polls for jobs and dispatches them.
    Supports graceful shutdown via SIGTERM/SIGINT.
    """
    # Register signal handlers
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    settings = get_settings()
    worker_id = f"worker-{uuid.uuid4().hex[:8]}"
    poll_interval = settings.worker_poll_interval_seconds
    concurrency = settings.worker_concurrency

    logger.info(
        f"Worker {worker_id} starting: "
        f"poll_interval={poll_interval}s, concurrency={concurrency}"
    )

    # Track running tasks
    running_tasks: set[asyncio.Task] = set()

    while not _shutdown:
        try:
            # Clean up finished tasks
            done = {t for t in running_tasks if t.done()}
            for t in done:
                # Log any exceptions from completed tasks
                if t.exception():
                    logger.error(f"Worker task failed: {t.exception()}")
            running_tasks -= done

            # Calculate how many jobs we can take
            available_slots = concurrency - len(running_tasks)

            if available_slots > 0:
                jobs = claim_jobs(worker_id, limit=available_slots)

                for job in jobs:
                    task = asyncio.create_task(dispatch_job(job))
                    running_tasks.add(task)

            # Wait before next poll
            await asyncio.sleep(poll_interval)

        except Exception as e:
            logger.error(f"Worker poll loop error: {e}")
            await asyncio.sleep(poll_interval * 2)  # Back off on error

    # Graceful shutdown: wait for running tasks to complete
    if running_tasks:
        logger.info(f"Waiting for {len(running_tasks)} running tasks to complete...")
        await asyncio.gather(*running_tasks, return_exceptions=True)

    logger.info(f"Worker {worker_id} shut down cleanly")
