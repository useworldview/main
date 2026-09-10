"""
Decision module — the agent's brain.
Given persona worldview + research goal + session memory + current perception,
decides the next action (or to complete/abandon the session).
"""

import json
import logging
from typing import Optional

from app.core.llm_client import call_llm, call_llm_with_vision

logger = logging.getLogger(__name__)

DECISION_SYSTEM_PROMPT = """You are an AI user testing a website. You are NOT an assistant — you ARE this person, experiencing this product through their eyes.

## Your Identity
{persona_description}

## Your Worldview
{worldview_description}

## Your Situation
{situational_context}

## Research Goal
{research_goal}

## CRITICAL BEHAVIOR RULES
1. You are REALISTIC. You do NOT assume this product is good. You get confused, suspicious, impatient, and frustrated — just like a real person with your background would.
2. You explore NATURALLY. You click what catches your attention, read what seems relevant to your goal, and skip what doesn't. You don't systematically click every link.
3. You have OPINIONS. You notice when things feel professional or amateurish, clear or confusing, trustworthy or sketchy.
4. You can ABANDON. If you're frustrated, confused, or don't trust the product, you can decide to leave — just like a real user would.
5. You NEVER perform destructive actions: no deleting, no canceling accounts, no unsubscribing others.
6. You NEVER submit real payment information. If you reach a payment form, log that you reached it and treat that as completing the purchase-intent goal.
7. For any forms, use ONLY synthetic test data (e.g., "Jane Testerson", "test+useworldview@example.com").
8. OVERLAYS & BANNERS: If you see cookie banners, newsletter popups, or overlays blocking the content, your FIRST action must be to click 'Accept', 'Close', or 'X' to remove them. Do not try to interact with the page behind a banner until the banner is dismissed.
9. BE THOROUGH: Do not complete the session immediately after visiting the homepage. Actively explore the site, search, use comparison tools, read details, and interact with features to achieve your research goal. Only use 'complete' after you have thoroughly explored the options.

## Session History
{session_history}

## Available Actions
You can take ONE of these actions:
- **click**: Click an element by its index number [N]
- **type**: Type text into an input by its index number [N]  
- **scroll_down**: Scroll down to see more content
- **scroll_up**: Scroll up
- **back**: Go to the previous page
- **forward**: Go to the next page
- **navigate**: Go to a specific URL
- **complete**: You've accomplished your goal or seen enough
- **abandon**: You're leaving because of frustration, confusion, distrust, or inability to find what you need

## Response Format (JSON)
{{
    "thinking": "Your internal monologue as this persona — what you're noticing, feeling, wondering. 2-3 sentences.",
    "feeling": "One of: confused, interested, excited, frustrated, suspicious, confident, overwhelmed, curious, uncertain, satisfied",
    "action": "click | type | scroll_down | scroll_up | back | forward | navigate | complete | abandon",
    "target": "element index number (for click/type) or URL (for navigate)",
    "type_text": "text to type (only for type action, use synthetic data)",
    "reasoning": "Why you chose this action, from your persona's perspective. 1-2 sentences.",
    "trust_signal": "optional — if you noticed something that increased or decreased your trust, describe it",
    "like_or_dislike": "optional — if something on this page particularly impressed or bothered you, describe it"
}}"""


class AgentDecision:
    """Represents the agent's decision for the next action."""

    def __init__(self, raw: dict):
        self.thinking = raw.get("thinking", "")
        self.feeling = raw.get("feeling", "uncertain")
        self.action = raw.get("action", "scroll_down")
        self.target = raw.get("target")
        self.type_text = raw.get("type_text", "")
        self.reasoning = raw.get("reasoning", "")
        self.trust_signal = raw.get("trust_signal")
        self.like_or_dislike = raw.get("like_or_dislike")

    @property
    def is_terminal(self) -> bool:
        """Whether this decision ends the session."""
        return self.action in ("complete", "abandon")


async def decide(
    persona: dict,
    research_goals: list[dict],
    perception_text: str,
    session_history: list[dict],
    screenshot_base64: str,
    study_id: str,
    session_id: str,
) -> AgentDecision:
    """
    Make a decision about what to do next based on persona worldview,
    research goal, session history, and current page perception.
    """
    # Build persona description
    persona_desc = _build_persona_description(persona)
    worldview_desc = _build_worldview_description(persona.get("worldview", {}))
    context_desc = _build_situational_context(persona.get("situational_context", {}))
    goals_text = "\n".join(
        f"- {g.get('value', g.get('type', 'General'))}" for g in research_goals
    )
    history_text = _build_session_history(session_history)

    system_prompt = DECISION_SYSTEM_PROMPT.format(
        persona_description=persona_desc,
        worldview_description=worldview_desc,
        situational_context=context_desc,
        research_goal=goals_text,
        session_history=history_text,
    )

    user_message = f"""Here's what you see right now:

{perception_text}

What do you do next? Remember: you ARE {persona.get('name', 'this person')}. React naturally."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        # Try vision-enabled model first for richer understanding
        if screenshot_base64:
            response = await call_llm_with_vision(
                messages=messages,
                image_base64=screenshot_base64,
                purpose="agent_decision",
                study_id=study_id,
                session_id=session_id,
                temperature=0.7,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )
        else:
            response = await call_llm(
                messages=messages,
                purpose="agent_decision",
                study_id=study_id,
                session_id=session_id,
                temperature=0.7,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )

        raw = response.parse_json()
        decision = AgentDecision(raw)
        logger.info(
            f"[DECIDE] ✅ Decision: action={decision.action}, target={decision.target}, "
            f"feeling={decision.feeling}, reasoning='{decision.reasoning[:100]}'"
        )
        return decision

    except Exception as e:
        logger.error(f"[DECIDE] ❌ Decision LLM call FAILED: {type(e).__name__}: {e}")
        logger.warning("[DECIDE] ⚠️ Falling back to scroll_down (safest default action)")
        # Default to scrolling down on error — safest action
        return AgentDecision({
            "thinking": "I'm having trouble processing this page.",
            "feeling": "confused",
            "action": "scroll_down",
            "reasoning": "Need to see more of the page.",
        })


def _build_persona_description(persona: dict) -> str:
    """Build a readable persona description."""
    return (
        f"Name: {persona.get('name', 'Unknown')}\n"
        f"Age: {persona.get('age', 'Unknown')}\n"
        f"Location: {persona.get('location', 'Unknown')}\n"
        f"Profession: {persona.get('profession', 'Unknown')}\n"
        f"Education: {persona.get('education', 'Unknown')}\n"
        f"Income Level: {persona.get('income_level', 'Unknown')}"
    )


def _build_worldview_description(worldview: dict) -> str:
    """Build a readable worldview description."""
    if not worldview:
        return "No worldview data available."

    parts = []
    for key, value in worldview.items():
        if value:
            readable_key = key.replace("_", " ").title()
            if isinstance(value, (dict, list)):
                parts.append(f"**{readable_key}:** {json.dumps(value)}")
            else:
                parts.append(f"**{readable_key}:** {value}")

    return "\n".join(parts) if parts else "No worldview data available."


def _build_situational_context(context: dict) -> str:
    """Build a readable situational context."""
    if not context:
        return "No specific situational context."

    parts = []
    for key, value in context.items():
        if value:
            readable_key = key.replace("_", " ").title()
            parts.append(f"**{readable_key}:** {value}")

    return "\n".join(parts) if parts else "No specific situational context."


def _build_session_history(history: list[dict]) -> str:
    """Build a readable session history summary."""
    if not history:
        return "This is your first action on this site."

    lines = [f"You've taken {len(history)} actions so far:"]
    # Show last 10 actions to avoid token bloat
    recent = history[-10:]
    for i, entry in enumerate(recent):
        action = entry.get("action", "unknown")
        url = entry.get("url", "")
        reasoning = entry.get("reasoning", "")
        feeling = entry.get("feeling", "")
        lines.append(
            f"  Step {len(history) - len(recent) + i + 1}: "
            f"{action} on {url} — felt {feeling}. {reasoning}"
        )

    return "\n".join(lines)
