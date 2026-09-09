"""
Cross-persona analysis and study synthesis.
Aggregates findings across all personas into patterns, insights, and summary metrics.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.supabase_client import get_supabase_client
from app.core.llm_client import call_llm
from app.services.recommendations_engine import generate_recommendations

logger = logging.getLogger(__name__)

SYNTHESIS_PROMPT = """You are a senior UX research director synthesizing findings across multiple personas who tested the same website.

## Product Context
{site_context}

## Research Goals
{research_goals}

## Persona Summaries & Their Findings
{persona_summaries}

## Your Task
Produce cross-persona insights — patterns that emerge when you look across all personas. These are the study's most valuable outputs.

### 1. Study-Wide Insights
Pattern statements grounded in the data: "X out of Y personas experienced Z because of W."
- Each insight must cite a specific count (e.g., "6/8 personas")
- Each insight must be specific and actionable (not "some users had issues")

### 2. Segment-Level Insights
Differences between audience segments: "Non-technical users struggled significantly more with X than technical users."
- Only include these if you observe genuine differences across segments
- Include the segment name for filtering

### 3. Summary Metrics
Compute these as plain ratios:
- **trust_score**: (# trust findings) / (# trust + distrust findings) — null if no trust-related findings
- **usability_score**: (# like findings) / (# like + dislike findings) — null if no like/dislike findings
- **task_completion_rate**: (# completed sessions) / (# total sessions)
- **conversion_intent**: (# sessions ending with completed goal or positive sentiment) / (# total sessions)
- **value_prop_clarity**: based on how many personas understood what the product does (subjective, estimate 0-1)

For each metric, also provide the numerator and denominator so the frontend can show "X/Y" not just a bare number.

Respond in JSON:
{
    "study_wide_insights": [
        {
            "statement": "7/10 personas found the navigation intuitive and could reach key pages within 2 clicks",
            "supporting_count": 7,
            "total_count": 10
        }
    ],
    "segment_insights": [
        {
            "statement": "Non-technical personas (3/4) struggled with the API documentation, while technical personas (4/4) found it clear",
            "supporting_count": 3,
            "total_count": 4,
            "segment": "Non-Technical Users"
        }
    ],
    "summary_metrics": {
        "trust_score": {"value": 0.75, "numerator": 6, "denominator": 8, "label": "Trust Score"},
        "usability_score": {"value": 0.60, "numerator": 9, "denominator": 15, "label": "Usability Score"},
        "task_completion_rate": {"value": 0.80, "numerator": 8, "denominator": 10, "label": "Task Completion Rate"},
        "conversion_intent": {"value": 0.70, "numerator": 7, "denominator": 10, "label": "Conversion Intent"},
        "value_prop_clarity": {"value": 0.85, "numerator": null, "denominator": null, "label": "Value Prop Clarity"}
    }
}"""


async def synthesize_study(payload: dict) -> None:
    """
    Synthesize findings across all personas in a study.
    
    1. Gather all findings and decision explanations
    2. LLM call to produce cross-persona insights and summary metrics
    3. Generate recommendations
    4. Update study status to completed
    """
    study_id = payload["study_id"]
    sb = get_supabase_client()

    logger.info(f"[SYNTHESIS] Starting cross-persona synthesis for study={study_id[:8]}")

    # Get study
    study = sb.table("studies").select("*").eq("id", study_id).single().execute().data
    site_context = study.get("site_context", {})
    research_goals = study.get("research_goals", [])

    # Get all personas for the study
    personas = (
        sb.table("personas")
        .select("*, audience_segments(name)")
        .eq("study_id", study_id)
        .execute()
    ).data or []

    # Get all sessions
    sessions = (
        sb.table("agent_sessions")
        .select("*")
        .eq("study_id", study_id)
        .execute()
    ).data or []

    # Build persona summaries with their findings
    persona_summaries = []
    all_findings = []
    all_decisions = []

    for persona in personas:
        # Find this persona's session(s)
        persona_sessions = [s for s in sessions if s["persona_id"] == persona["id"]]

        for session in persona_sessions:
            # Get findings
            findings = (
                sb.table("findings")
                .select("*")
                .eq("session_id", session["id"])
                .execute()
            ).data or []
            all_findings.extend(findings)

            # Get decision explanations
            decisions = (
                sb.table("decision_explanations")
                .select("*")
                .eq("session_id", session["id"])
                .execute()
            ).data or []
            all_decisions.extend(decisions)

            # Build summary
            segment_name = ""
            if persona.get("audience_segments"):
                segment_name = persona["audience_segments"].get("name", "")

            summary = {
                "persona_name": persona.get("name", "Unknown"),
                "segment": segment_name,
                "outcome": session.get("outcome", "unknown"),
                "outcome_reason": session.get("outcome_reason", ""),
                "steps": session.get("step_count", 0),
                "pages_visited": session.get("pages_visited", 0),
                "findings": [
                    {"type": f["type"], "description": f["description"], "feeling": f.get("feeling_label")}
                    for f in findings
                ],
                "decisions": [
                    {"type": d["decision_type"], "rationale": d["rationale_text"]}
                    for d in decisions
                ],
            }
            persona_summaries.append(summary)

    if not persona_summaries:
        logger.warning(f"[SYNTHESIS] No persona data for study {study_id[:8]}, marking as failed")
        sb.table("studies").update({
            "status": "failed",
            "error_message": "No persona sessions produced analyzable data",
        }).eq("id", study_id).execute()
        return

    logger.info(
        f"[SYNTHESIS] Loaded data: {len(persona_summaries)} persona sessions, "
        f"{len(all_findings)} findings, {len(all_decisions)} decisions"
    )

    # Prepare prompt
    goals_text = "\n".join(f"- {g.get('value', g.get('type', ''))}" for g in research_goals)
    site_text = f"URL: {site_context.get('url', 'Unknown')}\nTitle: {site_context.get('title', 'Unknown')}\nDescription: {site_context.get('meta_description', 'Unknown')}"

    prompt = SYNTHESIS_PROMPT.format(
        site_context=site_text,
        research_goals=goals_text,
        persona_summaries=json.dumps(persona_summaries, indent=2),
    )

    # LLM call
    response = await call_llm(
        messages=[
            {"role": "system", "content": "You are a senior UX research director synthesizing study findings."},
            {"role": "user", "content": prompt},
        ],
        purpose="study_synthesis",
        study_id=study_id,
        temperature=0.5,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )

    result = response.parse_json()

    # Insert cross-persona insights
    total_personas = len(personas)

    study_wide = result.get("study_wide_insights", [])
    for insight in study_wide:
        try:
            sb.table("cross_persona_insights").insert({
                "study_id": study_id,
                "statement": insight["statement"],
                "supporting_persona_count": insight.get("supporting_count", 0),
                "total_persona_count": insight.get("total_count", total_personas),
                "segment_filter": None,
            }).execute()
        except Exception as e:
            logger.warning(f"[SYNTHESIS] Failed to insert insight: {e}")

    segment_insights = result.get("segment_insights", [])
    for insight in segment_insights:
        try:
            sb.table("cross_persona_insights").insert({
                "study_id": study_id,
                "statement": insight["statement"],
                "supporting_persona_count": insight.get("supporting_count", 0),
                "total_persona_count": insight.get("total_count", total_personas),
                "segment_filter": insight.get("segment"),
            }).execute()
        except Exception as e:
            logger.warning(f"[SYNTHESIS] Failed to insert segment insight: {e}")

    # Store summary metrics
    summary_metrics = result.get("summary_metrics", {})

    # Also compute metrics from raw data as a sanity check
    computed_metrics = _compute_metrics_from_data(sessions, all_findings)
    # Merge — prefer computed values for hard metrics, LLM for subjective ones
    final_metrics = {**summary_metrics}
    for key in ["task_completion_rate", "trust_score", "usability_score"]:
        if key in computed_metrics:
            final_metrics[key] = computed_metrics[key]

    sb.table("studies").update({
        "summary_metrics": final_metrics,
    }).eq("id", study_id).execute()

    logger.info(
        f"[SYNTHESIS] Insights generated: "
        f"{len(study_wide)} study-wide, {len(segment_insights)} segment-level"
    )

    # Generate recommendations
    await generate_recommendations(
        study_id=study_id,
        persona_summaries=persona_summaries,
        all_findings=all_findings,
        all_decisions=all_decisions,
        site_context=site_context,
        research_goals=research_goals,
        total_personas=total_personas,
    )

    # Mark study as completed
    sb.table("studies").update({
        "status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", study_id).execute()

    logger.info(f"[SYNTHESIS] ✅ Study {study_id[:8]} synthesis and recommendations COMPLETE")


def _compute_metrics_from_data(sessions: list[dict], findings: list[dict]) -> dict:
    """
    Compute auditable metrics directly from the data.
    These are plain ratios, not opaque scores.
    """
    metrics = {}

    # Task completion rate
    total_sessions = len(sessions)
    completed = len([s for s in sessions if s.get("outcome") == "completed"])
    if total_sessions > 0:
        metrics["task_completion_rate"] = {
            "value": round(completed / total_sessions, 2),
            "numerator": completed,
            "denominator": total_sessions,
            "label": "Task Completion Rate",
        }

    # Trust score
    trust_findings = len([f for f in findings if f.get("type") == "trust"])
    distrust_findings = len([f for f in findings if f.get("type") == "distrust"])
    trust_total = trust_findings + distrust_findings
    if trust_total > 0:
        metrics["trust_score"] = {
            "value": round(trust_findings / trust_total, 2),
            "numerator": trust_findings,
            "denominator": trust_total,
            "label": "Trust Score",
        }

    # Usability score
    like_findings = len([f for f in findings if f.get("type") == "like"])
    dislike_findings = len([f for f in findings if f.get("type") == "dislike"])
    usability_total = like_findings + dislike_findings
    if usability_total > 0:
        metrics["usability_score"] = {
            "value": round(like_findings / usability_total, 2),
            "numerator": like_findings,
            "denominator": usability_total,
            "label": "Usability Score",
        }

    return metrics
