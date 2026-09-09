"""
Persona generation service — the Worldview Engine.
Generates full personas with psychographic attributes, worldview, and situational context.
"""

import json
import logging
from typing import Optional

from app.core.config import get_settings
from app.core.supabase_client import get_supabase_client
from app.core.llm_client import call_llm

logger = logging.getLogger(__name__)

PERSONA_GENERATION_PROMPT = """You are the Worldview Engine — an expert in creating deeply realistic, psychologically coherent synthetic user personas for user research.

Your job is to create a complete, believable persona for the given audience segment. This persona will be deployed as an autonomous AI user to test a real product — so they MUST behave like a real person, not an idealized version.

## Core Persona Attributes (all required)

### Demographics
- name (realistic first and last name)
- age (specific number)
- location (city, country)
- profession (specific job title and brief role description)
- education (highest level + field)
- income_level (specific bracket, e.g., "$45,000-$65,000/year")

### Psychographics / Worldview
- technical_ability: 1-10 scale with description
- digital_literacy: 1-10 scale with description
- goals: what they want to achieve in life and work (2-3 sentences)
- motivations: what drives their decisions (2-3 sentences)
- prior_experience: with similar products/services (specific examples)
- personality_traits: 3-5 specific traits with brief explanations
- habits: relevant digital/purchasing habits
- preferences: UX/design/communication preferences
- fears: what they worry about related to this product category
- frustrations: common pain points they experience
- expectations: what they expect from a product like this
- trust_level: how easily they trust new products (1-10 with explanation)
- price_sensitivity: how much price matters in their decisions (1-10 with explanation)
- decision_making_style: how they evaluate and decide (analytical, impulsive, research-heavy, etc.)
- risk_tolerance: willingness to try new/unproven things (1-10 with explanation)
- attention_span: patience for complex flows (1-10 with explanation)
- patience_level: tolerance for friction/loading/errors (1-10 with explanation)
- familiarity_with_similar_products: specific products they've used and their experience

### Situational Context
- current_situation: what's happening in their life right now that brings them to this product
- reason_for_visiting: the specific trigger/motivation for this visit
- what_they_want_to_accomplish: their concrete goal for this session
- decision_influences: what factors will most influence their decision

## Critical Rules
1. The persona must be INTERNALLY CONSISTENT. A 22-year-old art student should not have 15 years of enterprise software experience.
2. The persona must be REALISTICALLY SKEPTICAL. Real users don't assume products are good. They get confused, suspicious, impatient, and frustrated. Build that in.
3. Include SPECIFIC DETAILS, not vague generalities. "Uses Notion and Google Docs daily" > "uses productivity tools."
4. The persona's worldview should PLAUSIBLY influence their behavior on the target site. A high price-sensitivity persona should react differently to pricing than a low one.
5. Make the persona a WHOLE PERSON with contradictions and nuances, not a caricature of a market segment.

Respond in JSON format with a single persona object matching the structure above. Use the exact field names specified."""


async def generate_personas(payload: dict) -> None:
    """
    Generate personas for the given segments.
    
    1. For each segment, LLM call to synthesize a persona
    2. Self-consistency check
    3. Insert persona rows, update study status
    """
    study_id = payload["study_id"]
    segment_ids = payload["segment_ids"]
    personas_per_segment = payload.get("personas_per_segment", 1)
    sb = get_supabase_client()
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
    total_requested = len(segment_ids) * personas_per_segment
    max_allowed = settings.max_personas_per_study

    if existing_count + total_requested > max_allowed:
        raise ValueError(
            f"Cannot generate {total_requested} personas — would exceed maximum of "
            f"{max_allowed} per study (currently {existing_count})"
        )

    # Get study context
    study = sb.table("studies").select("*").eq("id", study_id).single().execute().data
    site_context = study.get("site_context", {})
    research_goals = study.get("research_goals", [])

    # Get segments
    segments_result = (
        sb.table("audience_segments")
        .select("*")
        .in_("id", segment_ids)
        .execute()
    )
    segments = segments_result.data or []

    generated_count = 0
    for segment in segments:
        for i in range(personas_per_segment):
            try:
                persona = await _generate_single_persona(
                    segment=segment,
                    site_context=site_context,
                    research_goals=research_goals,
                    study_id=study_id,
                    persona_number=i + 1,
                    total_for_segment=personas_per_segment,
                )

                # Insert into database
                sb.table("personas").insert({
                    "study_id": study_id,
                    "audience_segment_id": segment["id"],
                    "name": persona.get("name", f"Persona {generated_count + 1}"),
                    "age": persona.get("age"),
                    "location": persona.get("location"),
                    "profession": persona.get("profession"),
                    "education": persona.get("education"),
                    "income_level": persona.get("income_level"),
                    "worldview": {
                        "technical_ability": persona.get("technical_ability"),
                        "digital_literacy": persona.get("digital_literacy"),
                        "goals": persona.get("goals"),
                        "motivations": persona.get("motivations"),
                        "prior_experience": persona.get("prior_experience"),
                        "personality_traits": persona.get("personality_traits"),
                        "habits": persona.get("habits"),
                        "preferences": persona.get("preferences"),
                        "fears": persona.get("fears"),
                        "frustrations": persona.get("frustrations"),
                        "expectations": persona.get("expectations"),
                        "trust_level": persona.get("trust_level"),
                        "price_sensitivity": persona.get("price_sensitivity"),
                        "decision_making_style": persona.get("decision_making_style"),
                        "risk_tolerance": persona.get("risk_tolerance"),
                        "attention_span": persona.get("attention_span"),
                        "patience_level": persona.get("patience_level"),
                        "familiarity_with_similar_products": persona.get("familiarity_with_similar_products"),
                    },
                    "situational_context": {
                        "current_situation": persona.get("current_situation"),
                        "reason_for_visiting": persona.get("reason_for_visiting"),
                        "what_they_want_to_accomplish": persona.get("what_they_want_to_accomplish"),
                        "decision_influences": persona.get("decision_influences"),
                    },
                    "status": "draft",
                }).execute()

                generated_count += 1
                logger.info(
                    f"Generated persona '{persona.get('name')}' for segment "
                    f"'{segment['name']}' in study {study_id}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to generate persona for segment '{segment['name']}': {e}"
                )
                # Continue with other personas — one failure shouldn't stop all

    # Update study status
    if generated_count > 0:
        sb.table("studies").update({
            "status": "personas_ready",
        }).eq("id", study_id).execute()
    else:
        sb.table("studies").update({
            "status": "failed",
            "error_message": "Failed to generate any personas",
        }).eq("id", study_id).execute()

    logger.info(f"Generated {generated_count} personas for study {study_id}")

    # Emit analytics event
    _emit_analytics(sb, study.get("user_id"), study_id, generated_count)


async def regenerate_single_persona(persona_id: str, study_id: str) -> None:
    """Regenerate a single persona."""
    sb = get_supabase_client()

    # Get existing persona
    persona_row = sb.table("personas").select("*").eq("id", persona_id).single().execute().data
    if not persona_row:
        raise ValueError(f"Persona {persona_id} not found")

    # Get study and segment context
    study = sb.table("studies").select("*").eq("id", study_id).single().execute().data
    site_context = study.get("site_context", {})
    research_goals = study.get("research_goals", [])

    segment = None
    if persona_row.get("audience_segment_id"):
        segment_result = (
            sb.table("audience_segments")
            .select("*")
            .eq("id", persona_row["audience_segment_id"])
            .single()
            .execute()
        )
        segment = segment_result.data

    if not segment:
        segment = {"name": "General", "description": "General audience segment"}

    # Generate a new persona
    persona = await _generate_single_persona(
        segment=segment,
        site_context=site_context,
        research_goals=research_goals,
        study_id=study_id,
    )

    # Update the existing row
    sb.table("personas").update({
        "name": persona.get("name", persona_row["name"]),
        "age": persona.get("age"),
        "location": persona.get("location"),
        "profession": persona.get("profession"),
        "education": persona.get("education"),
        "income_level": persona.get("income_level"),
        "worldview": {
            "technical_ability": persona.get("technical_ability"),
            "digital_literacy": persona.get("digital_literacy"),
            "goals": persona.get("goals"),
            "motivations": persona.get("motivations"),
            "prior_experience": persona.get("prior_experience"),
            "personality_traits": persona.get("personality_traits"),
            "habits": persona.get("habits"),
            "preferences": persona.get("preferences"),
            "fears": persona.get("fears"),
            "frustrations": persona.get("frustrations"),
            "expectations": persona.get("expectations"),
            "trust_level": persona.get("trust_level"),
            "price_sensitivity": persona.get("price_sensitivity"),
            "decision_making_style": persona.get("decision_making_style"),
            "risk_tolerance": persona.get("risk_tolerance"),
            "attention_span": persona.get("attention_span"),
            "patience_level": persona.get("patience_level"),
            "familiarity_with_similar_products": persona.get("familiarity_with_similar_products"),
        },
        "situational_context": {
            "current_situation": persona.get("current_situation"),
            "reason_for_visiting": persona.get("reason_for_visiting"),
            "what_they_want_to_accomplish": persona.get("what_they_want_to_accomplish"),
            "decision_influences": persona.get("decision_influences"),
        },
    }).eq("id", persona_id).execute()

    logger.info(f"Regenerated persona {persona_id}")


async def _generate_single_persona(
    segment: dict,
    site_context: dict,
    research_goals: list[dict],
    study_id: str,
    persona_number: int = 1,
    total_for_segment: int = 1,
) -> dict:
    """Generate a single persona using LLM."""
    goals_text = "\n".join(
        f"- {g.get('value', g.get('type', 'General'))}" for g in research_goals
    )

    diversity_instruction = ""
    if total_for_segment > 1:
        diversity_instruction = (
            f"\nThis is persona #{persona_number} of {total_for_segment} for this segment. "
            f"Make this persona DISTINCT from others in the same segment — vary their "
            f"demographics, experience level, personality, and situational context."
        )

    user_message = f"""## Target Product
**URL:** {site_context.get('url', 'Unknown')}
**Title:** {site_context.get('title', 'Unknown')}
**Description:** {site_context.get('meta_description', 'Not available')}

### Product Content (excerpt)
{site_context.get('main_text', '')[:3000]}

## Audience Segment
**Name:** {segment.get('name', 'General')}
**Description:** {segment.get('description', 'General audience')}

## Research Goals
{goals_text}
{diversity_instruction}

Generate a complete, realistic persona for this audience segment who would visit this product. Remember: they must be realistically skeptical, not artificially cooperative."""

    response = await call_llm(
        messages=[
            {"role": "system", "content": PERSONA_GENERATION_PROMPT},
            {"role": "user", "content": user_message},
        ],
        purpose="persona_generation",
        study_id=study_id,
        temperature=0.8,  # Slightly higher for diversity
        max_tokens=4096,
        response_format={"type": "json_object"},
    )

    persona = response.parse_json()

    # Self-consistency check
    persona = await _consistency_check(persona, study_id)

    return persona


async def _consistency_check(persona: dict, study_id: str) -> dict:
    """
    Check persona for internal contradictions and fix if needed.
    E.g., "high digital literacy" + "struggles to use a mouse" shouldn't co-occur
    without narrative justification.
    """
    check_prompt = f"""Review this persona for internal contradictions. Check that:
1. Age, education, and experience are consistent (a 22-year-old shouldn't have 20 years of experience)
2. Technical ability and digital literacy align with their profession and habits
3. Income level is plausible for their profession and location
4. Personality traits don't contradict each other without explanation
5. Prior experience is plausible for their background

If the persona is consistent, respond with: {{"consistent": true, "persona": <the original persona unchanged>}}
If there are contradictions, fix them minimally and respond with: {{"consistent": false, "fixes": ["description of fix"], "persona": <the fixed persona>}}

Respond in JSON format.

## Persona to Review
{json.dumps(persona, indent=2)}"""

    try:
        response = await call_llm(
            messages=[
                {"role": "system", "content": "You are a QA reviewer for synthetic user personas. Check for internal contradictions and fix minimally."},
                {"role": "user", "content": check_prompt},
            ],
            purpose="persona_consistency_check",
            study_id=study_id,
            temperature=0.3,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        result = response.parse_json()
        if not result.get("consistent", True):
            fixes = result.get("fixes", [])
            logger.info(f"Persona consistency fixes applied: {fixes}")

        return result.get("persona", persona)

    except Exception as e:
        logger.warning(f"Consistency check failed, using original persona: {e}")
        return persona


def _emit_analytics(sb, user_id: str, study_id: str, count: int) -> None:
    """Emit analytics events for persona generation."""
    try:
        sb.table("analytics_events").insert({
            "user_id": user_id,
            "study_id": study_id,
            "event_name": "persona_generated",
            "properties": {"count": count},
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to emit analytics event: {e}")
