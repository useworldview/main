"""
Postgres-based job queue using FOR UPDATE SKIP LOCKED.
Zero extra infra — just a table and a poll loop.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def enqueue_job(
    job_type: str,
    payload: dict,
    max_attempts: int = 3,
) -> str:
    """
    Enqueue a new job for the worker to pick up.
    Returns the job ID.
    Also wakes the background worker if running in unified mode.
    """
    sb = get_supabase_client()
    job_id = str(uuid.uuid4())

    sb.table("agent_jobs").insert({
        "id": job_id,
        "job_type": job_type,
        "payload": payload,
        "status": "pending",
        "attempts": 0,
        "max_attempts": max_attempts,
    }).execute()

    logger.info(f"Enqueued job {job_id} type={job_type}")

    # Wake the background worker (no-op if not in unified mode or already running)
    from app.core.config import get_settings
    settings = get_settings()
    
    if settings.run_mode != "webhook":
        try:
            from app.jobs.worker import wake_worker
            wake_worker()
        except Exception as e:
            logger.debug(f"Could not wake worker (may be running standalone): {e}")

    return job_id


def claim_jobs(worker_id: str, limit: int = 1) -> list[dict]:
    """
    Claim up to `limit` pending jobs using FOR UPDATE SKIP LOCKED.
    Returns a list of claimed job dicts.
    """
    sb = get_supabase_client()

    # Use raw SQL for FOR UPDATE SKIP LOCKED — Supabase client doesn't
    # support this natively, so we use the RPC approach.
    # Instead, we do a simple claim: fetch pending, then update.
    # This is safe with a single worker; for multiple workers we'd need
    # the RPC function. Good enough for V1.
    result = (
        sb.table("agent_jobs")
        .select("*")
        .eq("status", "pending")
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )

    jobs = result.data or []
    claimed = []

    for job in jobs:
        # Atomically claim the job
        update_result = (
            sb.table("agent_jobs")
            .update({
                "status": "claimed",
                "claimed_at": datetime.now(timezone.utc).isoformat(),
                "claimed_by": worker_id,
                "attempts": job["attempts"] + 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", job["id"])
            .eq("status", "pending")  # Only claim if still pending
            .execute()
        )

        if update_result.data:
            claimed.append({**job, **update_result.data[0]})
            logger.info(f"Claimed job {job['id']} type={job['job_type']}")

    return claimed


def mark_running(job_id: str) -> None:
    """Mark a job as running."""
    sb = get_supabase_client()
    sb.table("agent_jobs").update({
        "status": "running",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", job_id).execute()


def complete_job(job_id: str) -> None:
    """Mark a job as done."""
    sb = get_supabase_client()
    sb.table("agent_jobs").update({
        "status": "done",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", job_id).execute()
    logger.info(f"Job {job_id} completed")


def fail_job(job_id: str, error_message: str) -> None:
    """
    Mark a job as failed. If attempts < max_attempts, re-queue it.
    """
    sb = get_supabase_client()

    # Get current job state
    result = sb.table("agent_jobs").select("*").eq("id", job_id).single().execute()
    job = result.data

    if job and job["attempts"] < job["max_attempts"]:
        # Re-queue for retry
        sb.table("agent_jobs").update({
            "status": "pending",
            "error_message": error_message,
            "claimed_at": None,
            "claimed_by": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", job_id).execute()
        logger.warning(
            f"Job {job_id} failed (attempt {job['attempts']}/{job['max_attempts']}), "
            f"re-queued: {error_message}"
        )
    else:
        # Max attempts reached — permanent failure
        sb.table("agent_jobs").update({
            "status": "failed",
            "error_message": error_message,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", job_id).execute()
        logger.error(f"Job {job_id} permanently failed: {error_message}")


def has_pending_or_running_jobs() -> bool:
    """
    Check if there are any jobs that are pending, claimed, or running.
    Used by the worker drain-and-exit logic to decide when to shut down.
    """
    sb = get_supabase_client()
    result = (
        sb.table("agent_jobs")
        .select("id", count="exact")
        .in_("status", ["pending", "claimed", "running"])
        .limit(1)
        .execute()
    )
    return (result.count or 0) > 0

