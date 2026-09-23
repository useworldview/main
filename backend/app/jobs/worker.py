"""
Worker poll loop — the async job processor.
Polls agent_jobs, dispatches to the right handler, handles success/failure/retry.

Supports two modes:
- "unified" (Cloud Run): worker runs as a background asyncio task inside the API process.
  Starts on demand via wake_worker(), drains all jobs, then auto-exits after idle timeout.
- "standalone" (local dev): traditional infinite poll loop via run_worker().
"""

import asyncio
import logging
import signal
import uuid
import time
import traceback
from typing import Optional

from app.core.config import get_settings
from app.jobs.queue import claim_jobs, mark_running, complete_job, fail_job, has_pending_or_running_jobs
from app.jobs.job_types import JobType

logger = logging.getLogger(__name__)

# Graceful shutdown flag (used in standalone mode)
_shutdown = False

# Background worker task reference (used in unified mode)
_worker_task: Optional[asyncio.Task] = None


def _handle_signal(signum, frame):
    global _shutdown
    logger.info(f"[WORKER] Received signal {signum}, initiating graceful shutdown...")
    _shutdown = True


async def dispatch_job(job: dict) -> None:
    """
    Dispatch a claimed job to the appropriate handler.
    """
    job_type = job["job_type"]
    payload = job["payload"]
    job_id = job["id"]
    start_time = time.time()

    # Build a short payload summary for logging (redact sensitive fields)
    payload_summary = {k: v for k, v in payload.items() if k not in ("research_goals",)}
    logger.info(f"[WORKER] ▶ Dispatching job {job_id[:8]} type={job_type} payload={payload_summary}")
    mark_running(job_id)

    try:
        if job_type == JobType.ANALYZE_SITE:
            from app.services.site_analysis import analyze_site
            logger.info(f"[WORKER] Starting site analysis for study={payload.get('study_id', '?')[:8]}")
            await analyze_site(payload)

        elif job_type == JobType.GENERATE_PERSONAS:
            from app.services.persona_generation import generate_personas
            logger.info(f"[WORKER] Starting persona generation for study={payload.get('study_id', '?')[:8]}")
            await generate_personas(payload)

        elif job_type == JobType.RUN_AGENT_SESSION:
            from app.services.agent_session.runner import run_agent_session
            logger.info(
                f"[WORKER] Starting agent session={payload.get('session_id', '?')[:8]} "
                f"for study={payload.get('study_id', '?')[:8]} "
                f"persona={payload.get('persona_id', '?')[:8]}"
            )
            await run_agent_session(payload)

        elif job_type == JobType.ANALYZE_SESSION:
            from app.services.post_session_analysis import analyze_session
            logger.info(f"[WORKER] Starting post-session analysis for session={payload.get('session_id', '?')[:8]}")
            await analyze_session(payload)

        elif job_type == JobType.SYNTHESIZE_STUDY:
            from app.services.cross_persona_analysis import synthesize_study
            logger.info(f"[WORKER] Starting study synthesis for study={payload.get('study_id', '?')[:8]}")
            await synthesize_study(payload)

        else:
            raise ValueError(f"Unknown job type: {job_type}")

        elapsed = time.time() - start_time
        complete_job(job_id)
        logger.info(f"[WORKER] ✅ Job {job_id[:8]} completed in {elapsed:.1f}s (type={job_type})")

    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = f"{type(e).__name__}: {str(e)}"
        full_traceback = traceback.format_exc()
        logger.error(
            f"[WORKER] ❌ Job {job_id[:8]} FAILED after {elapsed:.1f}s (type={job_type})\n"
            f"[WORKER] Error: {error_msg}\n"
            f"[WORKER] Full traceback:\n{full_traceback}"
        )
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
                        "outcome_reason": f"{error_msg}\n\nTraceback:\n{full_traceback[:2000]}",
                    }).eq("id", session_id).execute()
                    logger.info(f"[WORKER] Marked session {session_id[:8]} as failed")
            except Exception as inner_e:
                logger.error(f"[WORKER] Failed to update session status after job failure: {inner_e}")

            # Check if ALL sessions for this study are now terminal
            _check_study_completion(payload.get("study_id"))

        # If this is a post-session analysis job that failed, it means the pipeline broke
        if job_type in (JobType.ANALYZE_SESSION, JobType.SYNTHESIZE_STUDY):
            study_id = payload.get("study_id")
            if study_id:
                try:
                    from app.core.supabase_client import get_supabase_client
                    from datetime import datetime, timezone
                    sb = get_supabase_client()
                    sb.table("studies").update({
                        "status": "failed",
                        "error_message": f"{job_type.value} failed: {error_msg}",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }).eq("id", study_id).execute()
                    logger.warning(f"[WORKER] Study {study_id[:8]} marked as FAILED due to {job_type.value} failure")
                except Exception as inner_e:
                    logger.error(f"[WORKER] Failed to mark study as failed after {job_type.value} error: {inner_e}")


def _check_study_completion(study_id: Optional[str]) -> None:
    """
    Check if all sessions for a study are in a terminal state.
    If so, transition the study status appropriately.
    """
    if not study_id:
        return

    try:
        from app.core.supabase_client import get_supabase_client
        from datetime import datetime, timezone

        sb = get_supabase_client()

        # Get all sessions for this study
        sessions_result = (
            sb.table("agent_sessions")
            .select("id, status, outcome")
            .eq("study_id", study_id)
            .execute()
        )
        sessions = sessions_result.data or []

        if not sessions:
            return

        # Check if all sessions are terminal (completed or failed)
        terminal_statuses = {"completed", "failed"}
        all_terminal = all(s["status"] in terminal_statuses for s in sessions)

        if not all_terminal:
            non_terminal = [s for s in sessions if s["status"] not in terminal_statuses]
            logger.info(
                f"[WORKER] Study {study_id[:8]}: {len(non_terminal)} sessions still running, "
                f"not transitioning study status yet"
            )
            return

        completed_count = sum(1 for s in sessions if s["status"] == "completed")
        failed_count = sum(1 for s in sessions if s["status"] == "failed")

        logger.info(
            f"[WORKER] Study {study_id[:8]}: ALL sessions terminal "
            f"({completed_count} completed, {failed_count} failed)"
        )

        if completed_count == 0:
            # All sessions failed — mark study as failed
            sb.table("studies").update({
                "status": "failed",
                "error_message": f"All {failed_count} agent sessions failed. Check session details for error reasons.",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", study_id).execute()
            logger.warning(
                f"[WORKER] Study {study_id[:8]} marked as FAILED — all {failed_count} sessions failed"
            )
        else:
            # At least some sessions completed — the post-session analysis / synthesis
            # pipeline will handle transitioning to 'completed'
            logger.info(
                f"[WORKER] Study {study_id[:8]}: {completed_count} sessions completed, "
                f"waiting for post-analysis pipeline to finish"
            )

    except Exception as e:
        logger.error(f"[WORKER] Failed to check study completion for {study_id}: {e}", exc_info=True)


# ============================================================================
# Unified Mode (Cloud Run) — drain-and-exit worker
# ============================================================================

async def _run_worker_drain_mode():
    """
    Worker loop for Cloud Run unified mode.
    Processes all pending jobs, then waits idle_timeout seconds.
    If no new jobs arrive, exits cleanly so Cloud Run can scale to zero.
    """
    settings = get_settings()
    worker_id = f"worker-{uuid.uuid4().hex[:8]}"
    poll_interval = settings.worker_poll_interval_seconds
    concurrency = settings.worker_concurrency
    idle_timeout = settings.worker_idle_shutdown_seconds

    logger.info(
        f"[WORKER] Worker {worker_id} started (drain mode): "
        f"poll_interval={poll_interval}s, concurrency={concurrency}, "
        f"idle_timeout={idle_timeout}s"
    )

    running_tasks: set[asyncio.Task] = set()
    idle_since: Optional[float] = None
    poll_count = 0

    while True:
        try:
            # Clean up finished tasks
            done = {t for t in running_tasks if t.done()}
            for t in done:
                if t.exception():
                    logger.error(f"[WORKER] Background task exception: {t.exception()}")
            running_tasks -= done

            # Calculate how many jobs we can take
            available_slots = concurrency - len(running_tasks)

            if available_slots > 0:
                jobs = claim_jobs(worker_id, limit=available_slots)

                if jobs:
                    logger.info(f"[WORKER] Claimed {len(jobs)} jobs (slots={available_slots})")
                    idle_since = None  # Reset idle timer — we have work

                for job in jobs:
                    task = asyncio.create_task(dispatch_job(job))
                    running_tasks.add(task)

            # Check if we should idle-exit
            if not running_tasks and not has_pending_or_running_jobs():
                if idle_since is None:
                    idle_since = time.time()
                    logger.info(f"[WORKER] No jobs remaining. Starting {idle_timeout}s idle countdown...")
                elif time.time() - idle_since >= idle_timeout:
                    logger.info(f"[WORKER] Idle timeout reached ({idle_timeout}s). Worker shutting down.")
                    break
            else:
                idle_since = None  # Reset if there are running tasks or pending jobs

            # Periodic status log every 30 polls
            poll_count += 1
            if poll_count % 30 == 0 and running_tasks:
                logger.info(f"[WORKER] Heartbeat: {len(running_tasks)} tasks running")

            await asyncio.sleep(poll_interval)

        except Exception as e:
            logger.error(f"[WORKER] Poll loop error: {e}", exc_info=True)
            await asyncio.sleep(poll_interval * 2)

    # Wait for any remaining tasks
    if running_tasks:
        logger.info(f"[WORKER] Waiting for {len(running_tasks)} running tasks to complete...")
        await asyncio.gather(*running_tasks, return_exceptions=True)

    logger.info(f"[WORKER] Worker {worker_id} shut down cleanly (drain mode)")


def wake_worker():
    """
    Start the background worker if it's not already running.
    Called by enqueue_job() in unified mode.
    Safe to call multiple times — only one worker runs at a time.
    """
    global _worker_task

    settings = get_settings()
    if settings.run_mode != "unified":
        return  # In standalone mode, worker runs separately

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        logger.debug("[WORKER] No event loop available, skipping wake_worker")
        return

    # Check if a worker task is already running
    if _worker_task is not None and not _worker_task.done():
        logger.debug("[WORKER] Worker already running, wake_worker is a no-op")
        return

    logger.info("[WORKER] Waking background worker...")
    _worker_task = loop.create_task(_run_worker_drain_mode())


def is_worker_running() -> bool:
    """Check if the background worker task is currently running."""
    return _worker_task is not None and not _worker_task.done()


# ============================================================================
# Standalone Mode (local dev) — infinite poll loop
# ============================================================================

async def run_worker():
    """
    Main worker loop for standalone mode. Polls for jobs and dispatches them.
    Runs forever until SIGTERM/SIGINT.
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
        f"[WORKER] Worker {worker_id} started (standalone mode): "
        f"poll_interval={poll_interval}s, concurrency={concurrency}"
    )

    # Track running tasks
    running_tasks: set[asyncio.Task] = set()
    poll_count = 0

    while not _shutdown:
        try:
            # Clean up finished tasks
            done = {t for t in running_tasks if t.done()}
            for t in done:
                # Log any exceptions from completed tasks
                if t.exception():
                    logger.error(f"[WORKER] Background task exception: {t.exception()}")
            running_tasks -= done

            # Calculate how many jobs we can take
            available_slots = concurrency - len(running_tasks)

            if available_slots > 0:
                jobs = claim_jobs(worker_id, limit=available_slots)

                if jobs:
                    logger.info(f"[WORKER] Claimed {len(jobs)} jobs (slots={available_slots})")

                for job in jobs:
                    task = asyncio.create_task(dispatch_job(job))
                    running_tasks.add(task)

            # Periodic status log every 30 polls (~60s at 2s interval)
            poll_count += 1
            if poll_count % 30 == 0 and running_tasks:
                logger.info(f"[WORKER] Heartbeat: {len(running_tasks)} tasks running")

            # Wait before next poll
            await asyncio.sleep(poll_interval)

        except Exception as e:
            logger.error(f"[WORKER] Poll loop error: {e}", exc_info=True)
            await asyncio.sleep(poll_interval * 2)  # Back off on error

    # Graceful shutdown: wait for running tasks to complete
    if running_tasks:
        logger.info(f"[WORKER] Waiting for {len(running_tasks)} running tasks to complete...")
        await asyncio.gather(*running_tasks, return_exceptions=True)

    logger.info(f"[WORKER] Worker {worker_id} shut down cleanly")
