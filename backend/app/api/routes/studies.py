"""
API routes for UseWorldview backend.
This is the ENTIRE backend surface — 6 endpoints + health.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user_id
from app.core.config import get_settings
from app.core.supabase_client import get_supabase_client
from app.jobs.queue import enqueue_job
from app.jobs.job_types import JobType
from app.models.schemas import (
    CreateStudyRequest,
    GeneratePersonasRequest,
    HealthResponse,
    StudyResponse,
    MessageResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Health Check (no auth)
# ============================================================================

@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint — no auth required."""
    return HealthResponse(status="ok")


# ============================================================================
# POST /api/studies — Create a study + kick off site analysis
# ============================================================================

@router.post("/api/studies", response_model=StudyResponse)
async def create_study(
    request: CreateStudyRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Create a new study, validate the URL, and enqueue site analysis.
    
    1. Validate confirmed_authorized (Section 12.1)
    2. Create studies row
    3. Enqueue analyze_site job
    4. Return the study row
    """
    sb = get_supabase_client()

    # Consent check (Section 12.1)
    if not request.confirmed_authorized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You must confirm you have the right to test this URL (confirmed_authorized must be true)",
        )

    # Validate URL format
    target_url = request.target_url.strip()
    if not target_url.startswith(("http://", "https://")):
        target_url = f"https://{target_url}"

    # Create study row
    research_goals = [g.model_dump() for g in request.research_goals]

    result = sb.table("studies").insert({
        "user_id": user_id,
        "target_url": target_url,
        "research_goals": research_goals,
        "status": "draft",
        "confirmed_authorized": True,
    }).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create study",
        )

    study = result.data[0]

    # Enqueue site analysis
    enqueue_job(
        job_type=JobType.ANALYZE_SITE,
        payload={
            "study_id": study["id"],
            "target_url": target_url,
            "research_goals": research_goals,
        },
    )

    return _study_to_response(study)


# ============================================================================
# POST /api/studies/{id}/personas/generate
# ============================================================================

@router.post("/api/studies/{study_id}/personas/generate", response_model=MessageResponse)
async def generate_personas(
    study_id: str,
    request: GeneratePersonasRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Generate AI personas for the given audience segments.
    """
    sb = get_supabase_client()

    # Verify ownership
    study = _verify_study_ownership(sb, study_id, user_id)
    settings = get_settings()

    # Check persona count limit
    existing_count = len(
        sb.table("personas")
        .select("id")
        .eq("study_id", study_id)
        .neq("status", "archived")
        .execute()
        .data or []
    )

    total_new = len(request.segment_ids) * request.personas_per_segment
    if existing_count + total_new > settings.max_personas_per_study:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Would exceed maximum {settings.max_personas_per_study} personas per study "
                   f"(currently {existing_count}, requesting {total_new})",
        )

    # Enqueue job
    job_id = enqueue_job(
        job_type=JobType.GENERATE_PERSONAS,
        payload={
            "study_id": study_id,
            "segment_ids": request.segment_ids,
            "personas_per_segment": request.personas_per_segment,
        },
    )

    return MessageResponse(
        message="Persona generation started",
        study_id=study_id,
        job_id=job_id,
    )


# ============================================================================
# POST /api/personas/{id}/regenerate
# ============================================================================

@router.post("/api/personas/{persona_id}/regenerate", response_model=MessageResponse)
async def regenerate_persona(
    persona_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Regenerate a single persona with fresh attributes.
    """
    sb = get_supabase_client()

    # Get persona and verify ownership through study
    persona = sb.table("personas").select("*, studies(user_id)").eq("id", persona_id).single().execute().data
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    study_user_id = persona.get("studies", {}).get("user_id")
    if study_user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Enqueue regeneration
    job_id = enqueue_job(
        job_type=JobType.GENERATE_PERSONAS,
        payload={
            "study_id": persona["study_id"],
            "segment_ids": [persona["audience_segment_id"]] if persona.get("audience_segment_id") else [],
            "personas_per_segment": 1,
            "regenerate_persona_id": persona_id,
        },
    )

    return MessageResponse(
        message="Persona regeneration started",
        study_id=persona["study_id"],
        job_id=job_id,
    )


# ============================================================================
# POST /api/studies/{id}/deploy — Deploy AI users into the target site
# ============================================================================

@router.post("/api/studies/{study_id}/deploy", response_model=StudyResponse)
async def deploy_study(
    study_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Deploy all active personas in the study.
    
    1. Validate study has ≥1 active persona
    2. Create agent_sessions rows
    3. Enqueue one run_agent_session job per persona
    4. Set study status to 'running'
    """
    sb = get_supabase_client()

    # Verify ownership
    study = _verify_study_ownership(sb, study_id, user_id)

    # Get active personas
    personas = (
        sb.table("personas")
        .select("id")
        .eq("study_id", study_id)
        .eq("status", "draft")  # draft personas are deployable
        .execute()
    ).data or []

    if not personas:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Study has no active personas to deploy",
        )

    # Update personas to active
    for p in personas:
        sb.table("personas").update({"status": "active"}).eq("id", p["id"]).execute()

    # Create agent sessions and enqueue jobs
    for persona in personas:
        # Create session row
        session_result = sb.table("agent_sessions").insert({
            "study_id": study_id,
            "persona_id": persona["id"],
            "status": "queued",
            "step_budget": study.get("step_budget_per_session", 40),
        }).execute()

        session = session_result.data[0]

        # Enqueue agent session job
        enqueue_job(
            job_type=JobType.RUN_AGENT_SESSION,
            payload={
                "session_id": session["id"],
                "study_id": study_id,
                "persona_id": persona["id"],
                "target_url": study["target_url"],
                "step_budget": study.get("step_budget_per_session", 40),
                "max_pages": study.get("max_pages", 5),
            },
        )

    # Update study status
    sb.table("studies").update({
        "status": "running",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", study_id).execute()

    # Refetch updated study
    updated = sb.table("studies").select("*").eq("id", study_id).single().execute().data
    return _study_to_response(updated)


# ============================================================================
# POST /api/studies/{id}/cancel — Cancel a running study
# ============================================================================

@router.post("/api/studies/{study_id}/cancel", response_model=MessageResponse)
async def cancel_study(
    study_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Cancel a running study immediately.
    
    1. Mark all non-terminal sessions as failed (cancelled)
    2. Clean up pending jobs
    3. Set study status to failed with 'Cancelled by user'
    """
    sb = get_supabase_client()

    # Verify ownership
    study = _verify_study_ownership(sb, study_id, user_id)

    # Only allow cancelling active studies
    cancellable_statuses = {"analyzing_site", "deploying", "running", "analyzing_results"}
    if study["status"] not in cancellable_statuses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Study is not in a cancellable state (current: {study['status']})",
        )

    # Mark all non-terminal sessions as failed
    non_terminal_sessions = (
        sb.table("agent_sessions")
        .select("id, status")
        .eq("study_id", study_id)
        .in_("status", ["queued", "running"])
        .execute()
    ).data or []

    cancelled_count = 0
    for session in non_terminal_sessions:
        sb.table("agent_sessions").update({
            "status": "failed",
            "outcome": "error",
            "outcome_reason": "Cancelled by user",
            "end_time": datetime.now(timezone.utc).isoformat(),
        }).eq("id", session["id"]).execute()
        cancelled_count += 1

    # Clean up pending jobs for this study's sessions
    session_ids = [s["id"] for s in non_terminal_sessions]
    if session_ids:
        # Delete pending/claimed jobs that reference these sessions
        for session_id in session_ids:
            try:
                sb.table("agent_jobs").delete().in_(
                    "status", ["pending", "claimed"]
                ).contains("payload", {"session_id": session_id}).execute()
            except Exception:
                pass  # Best effort cleanup

    # Also delete any pending analyze_site or other study-level jobs
    try:
        sb.table("agent_jobs").delete().in_(
            "status", ["pending", "claimed"]
        ).contains("payload", {"study_id": study_id}).execute()
    except Exception:
        pass  # Best effort cleanup

    # Update study status
    sb.table("studies").update({
        "status": "failed",
        "error_message": "Cancelled by user",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", study_id).execute()

    logger.info(
        f"Study {study_id} cancelled by user: "
        f"{cancelled_count} sessions cancelled"
    )

    return MessageResponse(
        message=f"Study cancelled. {cancelled_count} running sessions stopped.",
        study_id=study_id,
    )


# ============================================================================
# POST /api/studies/{id}/retry-failed-sessions
# ============================================================================

@router.post("/api/studies/{study_id}/retry-failed-sessions", response_model=MessageResponse)
async def retry_failed_sessions(
    study_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Re-enqueue only sessions with status='failed'.
    """
    sb = get_supabase_client()

    # Verify ownership
    study = _verify_study_ownership(sb, study_id, user_id)

    # Get failed sessions
    failed_sessions = (
        sb.table("agent_sessions")
        .select("*")
        .eq("study_id", study_id)
        .eq("status", "failed")
        .execute()
    ).data or []

    if not failed_sessions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No failed sessions to retry",
        )

    retried = 0
    for session in failed_sessions:
        # Reset session status
        sb.table("agent_sessions").update({
            "status": "queued",
            "outcome": None,
            "outcome_reason": None,
            "step_count": 0,
            "pages_visited": 0,
            "start_time": None,
            "end_time": None,
        }).eq("id", session["id"]).execute()

        # Enqueue new job
        enqueue_job(
            job_type=JobType.RUN_AGENT_SESSION,
            payload={
                "session_id": session["id"],
                "study_id": study_id,
                "persona_id": session["persona_id"],
                "target_url": study["target_url"],
                "step_budget": session.get("step_budget", 40),
                "max_pages": study.get("max_pages", 5),
            },
        )
        retried += 1

    # Update study status back to running
    sb.table("studies").update({
        "status": "running",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", study_id).execute()

    return MessageResponse(
        message=f"Retrying {retried} failed sessions",
        study_id=study_id,
    )


# ============================================================================
# DELETE /api/studies/{id}/purge-storage — Delete screenshots from Storage
# ============================================================================

@router.delete("/api/studies/{study_id}/purge-storage", response_model=MessageResponse)
async def purge_study_storage(
    study_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Delete all screenshots from Supabase Storage for a study.
    Called by the frontend alongside the DB-side study deletion.
    """
    sb = get_supabase_client()

    # Verify ownership
    _verify_study_ownership(sb, study_id, user_id)

    try:
        # List and delete all files in the study's storage folder
        files = sb.storage.from_("screenshots").list(study_id)
        if files:
            # Supabase Storage needs the full path within the bucket
            paths = []
            for session_folder in files:
                folder_name = session_folder.get("name", "")
                if folder_name:
                    session_files = sb.storage.from_("screenshots").list(f"{study_id}/{folder_name}")
                    for f in (session_files or []):
                        paths.append(f"{study_id}/{folder_name}/{f.get('name', '')}")

            if paths:
                sb.storage.from_("screenshots").remove(paths)
                logger.info(f"Purged {len(paths)} screenshot files for study {study_id}")

        return MessageResponse(message=f"Storage purged for study {study_id}")

    except Exception as e:
        logger.error(f"Failed to purge storage for study {study_id}: {e}")
        return MessageResponse(message=f"Storage purge attempted with errors: {str(e)}")


# ============================================================================
# Helpers
# ============================================================================

def _verify_study_ownership(sb, study_id: str, user_id: str) -> dict:
    """Verify the user owns this study. Returns the study dict."""
    result = sb.table("studies").select("*").eq("id", study_id).single().execute()
    study = result.data

    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    if study["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this study")

    return study


def _study_to_response(study: dict) -> StudyResponse:
    """Convert a study dict to a StudyResponse."""
    return StudyResponse(
        id=study["id"],
        user_id=study["user_id"],
        title=study.get("title"),
        research_goals=study.get("research_goals", []),
        target_url=study["target_url"],
        status=study["status"],
        step_budget_per_session=study.get("step_budget_per_session", 40),
        max_pages=study.get("max_pages", 5),
        site_context=study.get("site_context"),
        summary_metrics=study.get("summary_metrics"),
        error_message=study.get("error_message"),
        confirmed_authorized=study.get("confirmed_authorized", False),
        created_at=str(study["created_at"]),
        updated_at=str(study["updated_at"]),
        completed_at=str(study["completed_at"]) if study.get("completed_at") else None,
    )
