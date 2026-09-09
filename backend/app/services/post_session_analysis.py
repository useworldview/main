"""
Post-session analysis service.
Converts raw interaction events into structured findings and decision explanations.
"""

import json
import logging
from typing import Optional

from app.core.supabase_client import get_supabase_client
from app.core.llm_client import call_llm
from app.jobs.queue import enqueue_job
from app.jobs.job_types import JobType

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """You are a senior UX researcher analyzing a complete user session on a website. You are reviewing the actions and reactions of a specific persona to produce structured research findings.

## Persona
{persona_description}

## Their Worldview
{worldview_description}

## Their Situational Context
{situational_context}

## Research Goals
{research_goals}

## Session Summary
- Outcome: {outcome} ({outcome_reason})
- Total Steps: {step_count}
- Pages Visited: {pages_visited}

## Full Session Event Log
{event_log}

## Your Task
Analyze this session from the persona's perspective and produce:

### 1. Findings
For each finding, identify:
- **type**: "like" | "dislike" | "feeling" | "trust" | "distrust"
- **feeling_label** (only for type="feeling"): "confused" | "interested" | "excited" | "frustrated" | "suspicious" | "confident" | "overwhelmed" | "curious" | "uncertain" | "satisfied"
- **description**: A specific, evidence-backed description written from the persona's perspective. Not generic — cite the specific page, element, or moment.
- **linked_event_ids**: Array of event IDs that support this finding (from the event log)

### 2. Decision Explanations
For each major decision point (signing up, purchasing, using a feature, abandoning):
- **decision_type**: "signup" | "purchase" | "feature_use" | "abandon" | "other"
- **rationale_text**: A detailed explanation of WHY the persona made this decision, grounded in their worldview and session experience. What convinced them, what stopped them, what was missing?
- **linked_event_ids**: Array of event IDs supporting this explanation

## Rules
1. Every finding and explanation MUST reference specific events from the session log
2. Be SPECIFIC — "the pricing page was confusing" is not enough. "The pricing page showed three tiers but didn't list what features were in each, causing the persona to scroll back and forth three times before giving up" is specific.
3. Include BOTH positive and negative findings — real research captures what works AND what doesn't
4. Findings about dead ends and page errors are ESPECIALLY important — surface them as distinct dislike findings
5. Write from the PERSONA'S perspective, not a generic analyst's

Respond in JSON:
{{
    "findings": [
        {{
            "type": "like|dislike|feeling|trust|distrust",
            "feeling_label": "null or one of the defined labels",
            "description": "specific, evidence-backed finding",
            "linked_event_ids": ["event-id-1", "event-id-2"]
        }}
    ],
    "decision_explanations": [
        {{
            "decision_type": "signup|purchase|feature_use|abandon|other",
            "rationale_text": "detailed explanation",
            "linked_event_ids": ["event-id-1"]
        }}
    ]
}}"""


async def analyze_session(payload: dict) -> None:
    """
    Analyze a completed agent session.
    
    1. Load all interaction events for the session
    2. LLM call to produce findings + decision explanations
    3. Insert into database
    4. Check if all sessions for the study are done → if so, enqueue synthesis
    """
    session_id = payload["session_id"]
    study_id = payload["study_id"]
    persona_id = payload["persona_id"]
    sid = session_id[:8]
    sb = get_supabase_client()

    logger.info(f"[POST_ANALYSIS] Starting analysis for session={sid}, study={study_id[:8]}")

    # Get persona
    persona = sb.table("personas").select("*").eq("id", persona_id).single().execute().data

    # Get session
    session = sb.table("agent_sessions").select("*").eq("id", session_id).single().execute().data

    # Get study for research goals
    study = sb.table("studies").select("research_goals").eq("id", study_id).single().execute().data
    research_goals = study.get("research_goals", [])

    # Get all interaction events
    events_result = (
        sb.table("interaction_events")
        .select("*")
        .eq("session_id", session_id)
        .order("sequence_no", desc=False)
        .execute()
    )
    events = events_result.data or []

    if not events:
        logger.warning(f"[POST_ANALYSIS] No events found for session {sid}, skipping analysis")
        # Still check synthesis in case this was the last session
        await _check_and_enqueue_synthesis(study_id)
        return

    logger.info(f"[POST_ANALYSIS] Loaded {len(events)} events for session {sid}")

    # Build prompt context
    persona_desc = _format_persona(persona)
    worldview_desc = json.dumps(persona.get("worldview", {}), indent=2)
    context_desc = json.dumps(persona.get("situational_context", {}), indent=2)
    goals_text = "\n".join(f"- {g.get('value', g.get('type', ''))}" for g in research_goals)
    event_log = _format_event_log(events)

    prompt = ANALYSIS_PROMPT.format(
        persona_description=persona_desc,
        worldview_description=worldview_desc,
        situational_context=context_desc,
        research_goals=goals_text,
        outcome=session.get("outcome", "unknown"),
        outcome_reason=session.get("outcome_reason", "unknown"),
        step_count=session.get("step_count", 0),
        pages_visited=session.get("pages_visited", 0),
        event_log=event_log,
    )

    # LLM call
    response = await call_llm(
        messages=[
            {"role": "system", "content": "You are a senior UX researcher producing structured research findings."},
            {"role": "user", "content": prompt},
        ],
        purpose="session_analysis",
        study_id=study_id,
        session_id=session_id,
        temperature=0.5,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )

    result = response.parse_json()

    # Insert findings
    findings = result.get("findings", [])
    for finding in findings:
        try:
            # Validate linked_event_ids exist
            linked_ids = _validate_event_ids(finding.get("linked_event_ids", []), events)

            insert_data = {
                "session_id": session_id,
                "type": finding["type"],
                "description": finding["description"],
                "linked_event_ids": linked_ids,
            }
            if finding.get("feeling_label"):
                insert_data["feeling_label"] = finding["feeling_label"]

            sb.table("findings").insert(insert_data).execute()
        except Exception as e:
            logger.warning(f"[POST_ANALYSIS] Failed to insert finding: {e}")

    # Insert decision explanations
    decisions = result.get("decision_explanations", [])
    for decision in decisions:
        try:
            linked_ids = _validate_event_ids(decision.get("linked_event_ids", []), events)
            sb.table("decision_explanations").insert({
                "session_id": session_id,
                "decision_type": decision["decision_type"],
                "rationale_text": decision["rationale_text"],
                "linked_event_ids": linked_ids,
            }).execute()
        except Exception as e:
            logger.warning(f"[POST_ANALYSIS] Failed to insert decision explanation: {e}")

    logger.info(
        f"[POST_ANALYSIS] ✅ Session {sid} analysis complete: "
        f"{len(findings)} findings, {len(decisions)} decisions"
    )

    # Check if all sessions for this study are analyzed
    await _check_and_enqueue_synthesis(study_id)


async def _check_and_enqueue_synthesis(study_id: str) -> None:
    """
    Check if all sessions for a study have reached a terminal state.
    If so, enqueue study synthesis.
    """
    sb = get_supabase_client()

    # Get all sessions for the study
    sessions = (
        sb.table("agent_sessions")
        .select("id, status, outcome")
        .eq("study_id", study_id)
        .execute()
    ).data or []

    if not sessions:
        return

    # Check if all sessions are in a terminal state
    terminal_states = {"completed", "failed", "aborted"}
    all_terminal = all(s.get("status") in terminal_states for s in sessions)

    if all_terminal:
        # Check if any session has findings (i.e., was analyzed)
        sessions_with_findings = 0
        for s in sessions:
            findings = (
                sb.table("findings")
                .select("id")
                .eq("session_id", s["id"])
                .limit(1)
                .execute()
            ).data
            if findings:
                sessions_with_findings += 1

        # Count how many sessions were analyzed
        analyzed_sessions = sessions_with_findings
        total_with_data = len([s for s in sessions if s.get("outcome") in ("completed", "abandoned")])

        logger.info(
            f"[POST_ANALYSIS] Study {study_id[:8]}: all sessions terminal. "
            f"analyzed={analyzed_sessions}/{total_with_data} sessions with data"
        )

        # If no sessions produced usable data, mark study as failed
        if total_with_data == 0:
            from datetime import datetime, timezone
            sb.table("studies").update({
                "status": "failed",
                "error_message": "All agent sessions failed — no data to analyze",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", study_id).execute()
            logger.warning(f"[POST_ANALYSIS] Study {study_id[:8]} marked FAILED — no sessions produced data")
            return

        # Only synthesize once all sessions that produced data have been analyzed
        if analyzed_sessions >= total_with_data:
            logger.info(f"[POST_ANALYSIS] ✅ All sessions analyzed for study {study_id[:8]}, enqueuing synthesis")
            sb.table("studies").update({
                "status": "analyzing_results",
            }).eq("id", study_id).execute()

            enqueue_job(
                job_type=JobType.SYNTHESIZE_STUDY,
                payload={"study_id": study_id},
            )
        else:
            logger.info(
                f"[POST_ANALYSIS] Study {study_id[:8]}: waiting for more sessions to be analyzed "
                f"({analyzed_sessions}/{total_with_data})"
            )
    else:
        non_terminal = [s for s in sessions if s.get("status") not in terminal_states]
        logger.info(
            f"[POST_ANALYSIS] Study {study_id[:8]}: {len(non_terminal)} sessions still running"
        )


def _format_persona(persona: dict) -> str:
    """Format persona for the prompt."""
    return (
        f"Name: {persona.get('name', 'Unknown')}\n"
        f"Age: {persona.get('age', 'Unknown')}\n"
        f"Location: {persona.get('location', 'Unknown')}\n"
        f"Profession: {persona.get('profession', 'Unknown')}\n"
        f"Education: {persona.get('education', 'Unknown')}\n"
        f"Income: {persona.get('income_level', 'Unknown')}"
    )


def _format_event_log(events: list[dict]) -> str:
    """Format events into a readable log."""
    lines = []
    for event in events:
        line = (
            f"[Event {event['id']}] Step {event['sequence_no']}: "
            f"{event['event_type']} on {event.get('page_url', 'unknown')} "
        )
        if event.get("target_element"):
            line += f"target={event['target_element']} "
        if event.get("reasoning"):
            line += f"— {event['reasoning']} "

        details = event.get("details", {})
        if details.get("thinking"):
            line += f"\n  Thinking: {details['thinking']}"
        if details.get("feeling"):
            line += f"\n  Feeling: {details['feeling']}"
        if details.get("trust_signal"):
            line += f"\n  Trust signal: {details['trust_signal']}"
        if details.get("like_or_dislike"):
            line += f"\n  Like/Dislike: {details['like_or_dislike']}"
        if details.get("error"):
            line += f"\n  ERROR: {details['error']}"

        lines.append(line)

    return "\n\n".join(lines)


def _validate_event_ids(ids: list, events: list[dict]) -> list[str]:
    """Validate that event IDs exist in the event log."""
    valid_ids = {e["id"] for e in events}
    return [str(id) for id in ids if str(id) in valid_ids]
