"""
Recommendations engine.
Converts aggregated findings into prioritized, structured recommendations
following the PRD Section 23 format exactly.
"""

import json
import logging
from typing import Optional

from app.core.supabase_client import get_supabase_client
from app.core.llm_client import call_llm

logger = logging.getLogger(__name__)

RECOMMENDATIONS_PROMPT = """You are a senior product consultant generating actionable recommendations from a user research study.

## Product Context
{site_context}

## Research Goals
{research_goals}

## Persona Summaries & Their Findings
{persona_summaries}

## Your Task
Generate prioritized recommendations. Each recommendation MUST follow this EXACT format:

1. **Problem**: What is broken, unclear, or causing friction — in one specific sentence
2. **Evidence**: Specific session events, persona quotes, and behaviors that demonstrate the problem
3. **Affected Users**: Which personas/segments experienced this, and how many (e.g., "6/10 personas, primarily price-sensitive segments")
4. **Why It Matters**: The downstream impact — trust, conversion, task completion, etc.
5. **Suggested Improvement**: A concrete, specific fix the team can act on

For each recommendation, also estimate:
- **severity**: "high" (blocks task completion / trust-breaking), "medium" (causes friction but task still completable), or "low" (minor annoyance)
- **affected_persona_count**: how many personas were affected
- **total_persona_count**: total personas in the study

## Rules
1. Every recommendation MUST cite specific evidence — no generic, unsourced advice
2. Be SPECIFIC in suggested improvements — "improve the pricing page" is not enough. "Add a feature-comparison table under each pricing tier and surface an inline FAQ" is specific.
3. Rank by estimated impact (more personas affected + higher severity = higher priority)
4. Include BOTH UX and content/messaging recommendations where relevant
5. Don't recommend things that would require completely rebuilding the product — focus on actionable, incremental improvements

Respond in JSON:
{{
    "recommendations": [
        {{
            "problem": "...",
            "evidence": "...",
            "affected_users": "...",
            "why_it_matters": "...",
            "suggested_improvement": "...",
            "severity": "high|medium|low",
            "affected_persona_count": 6,
            "total_persona_count": 10
        }}
    ]
}}"""

SEVERITY_WEIGHTS = {
    "high": 1.0,
    "medium": 0.6,
    "low": 0.3,
}


async def generate_recommendations(
    study_id: str,
    persona_summaries: list[dict],
    all_findings: list[dict],
    all_decisions: list[dict],
    site_context: dict,
    research_goals: list[dict],
    total_personas: int,
) -> None:
    """
    Generate prioritized recommendations from study findings.
    
    Each recommendation follows the PRD Section 23 format:
    Problem → Evidence → Affected Users → Why It Matters → Suggested Improvement
    """
    sb = get_supabase_client()

    goals_text = "\n".join(f"- {g.get('value', g.get('type', ''))}" for g in research_goals)
    site_text = (
        f"URL: {site_context.get('url', 'Unknown')}\n"
        f"Title: {site_context.get('title', 'Unknown')}\n"
        f"Description: {site_context.get('meta_description', '')}"
    )

    prompt = RECOMMENDATIONS_PROMPT.format(
        site_context=site_text,
        research_goals=goals_text,
        persona_summaries=json.dumps(persona_summaries, indent=2),
    )

    response = await call_llm(
        messages=[
            {"role": "system", "content": "You are a senior product consultant generating actionable UX recommendations."},
            {"role": "user", "content": prompt},
        ],
        purpose="recommendation_generation",
        study_id=study_id,
        temperature=0.5,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )

    result = response.parse_json()
    recommendations = result.get("recommendations", [])

    for rec in recommendations:
        try:
            severity = rec.get("severity", "medium")
            severity_weight = SEVERITY_WEIGHTS.get(severity, 0.6)
            affected_count = rec.get("affected_persona_count", 0)
            total_count = rec.get("total_persona_count", total_personas)

            # Compute priority score: (affected/total) * severity_weight
            priority_score = 0.0
            if total_count > 0:
                priority_score = round((affected_count / total_count) * severity_weight, 3)

            sb.table("recommendations").insert({
                "study_id": study_id,
                "problem": rec["problem"],
                "evidence": rec["evidence"],
                "affected_users": rec["affected_users"],
                "why_it_matters": rec["why_it_matters"],
                "suggested_improvement": rec["suggested_improvement"],
                "priority_score": priority_score,
                "affected_persona_count": affected_count,
                "total_persona_count": total_count,
                "severity_weight": severity_weight,
                "status": "new",
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to insert recommendation: {e}")

    logger.info(f"Generated {len(recommendations)} recommendations for study {study_id}")
