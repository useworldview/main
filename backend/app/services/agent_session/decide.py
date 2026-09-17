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

## MULTI-PAGE EXPLORATION RULES (VERY IMPORTANT)
9. You MUST visit multiple pages. Do NOT complete the session after only seeing the homepage. You should visit at least 2-3 different pages to properly evaluate the product.
10. When you see navigation links (in the nav bar, header, footer, or in-page links), PREFER clicking them to explore other pages over scrolling further on the same page.
11. Use the **navigate** action with a URL to directly visit a page from the Discovered Pages list. This is the most reliable way to move between pages.
12. After scrolling 2-3 times on the same page without finding new relevant content, you SHOULD navigate to a different page.
13. Only use 'complete' or 'abandon' after you have visited multiple pages and thoroughly explored the product relevant to your research goal.

## Session History
{session_history}

## Discovered Pages (Site Map)
{page_map}

## Exploration Progress
{exploration_progress}

## Available Actions
You can take ONE of these actions:
- **click**: Click an element by its index number [N]
- **type**: Type text into an input by its index number [N]  
- **scroll_down**: Scroll down to see more content
- **scroll_up**: Scroll up
- **back**: Go to the previous page
- **forward**: Go to the next page
- **navigate**: Go to a specific URL (use URLs from the Discovered Pages list above)
- **complete**: You've accomplished your goal or seen enough (ONLY after visiting multiple pages)
- **abandon**: You're leaving because of frustration, confusion, distrust, or inability to find what you need

## Response Format (JSON)
{{
    "thinking": "Your internal monologue as this persona — what you're noticing, feeling, wondering. 2-3 sentences.",
    "feeling": "One of: confused, interested, excited, frustrated, suspicious, confident, overwhelmed, curious, uncertain, satisfied",
    "action": "click | type | scroll_down | scroll_up | back | forward | navigate | complete | abandon",
    "target": "element index number (for click/type) or FULL URL (for navigate — use a URL from Discovered Pages)",
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
    discovered_pages: list[dict] = None,
    pages_visited: set = None,
) -> AgentDecision:
    """
    Make a decision about what to do next based on persona worldview,
    research goal, session history, and current page perception.
    
    Now includes:
    - discovered_pages: page map from DOM link crawling
    - pages_visited: set of URLs already visited
    """
    # Build persona description
    persona_desc = _build_persona_description(persona)
    worldview_desc = _build_worldview_description(persona.get("worldview", {}))
    context_desc = _build_situational_context(persona.get("situational_context", {}))
    goals_text = "\n".join(
        f"- {g.get('value', g.get('type', 'General'))}" for g in research_goals
    )
    history_text = _build_session_history(session_history)
    page_map_text = _build_page_map(discovered_pages or [], pages_visited or set())
    exploration_text = _build_exploration_progress(session_history, pages_visited or set(), discovered_pages or [])

    system_prompt = DECISION_SYSTEM_PROMPT.format(
        persona_description=persona_desc,
        worldview_description=worldview_desc,
        situational_context=context_desc,
        research_goal=goals_text,
        session_history=history_text,
        page_map=page_map_text,
        exploration_progress=exploration_text,
    )

    user_message = f"""Here's what you see right now:

{perception_text}

What do you do next? Remember: you ARE {persona.get('name', 'this person')}. React naturally.
If you've been on the same page for a while, consider navigating to an unvisited page from the Discovered Pages list."""

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
        
        # ── Navigation nudge: if agent keeps completing too early, override ──
        if decision.is_terminal and len(pages_visited or set()) < 2 and len(session_history) < 8:
            logger.warning(
                f"[DECIDE] ⚠️ Agent trying to {decision.action} after visiting only "
                f"{len(pages_visited or set())} page(s) and {len(session_history)} steps. "
                f"Overriding to navigate to an unvisited page."
            )
            # Find an unvisited page to navigate to
            unvisited = _get_unvisited_pages(discovered_pages or [], pages_visited or set())
            if unvisited:
                # Pick a nav/content page preferentially
                nav_pages = [p for p in unvisited if p['source'] == 'nav']
                target_page = nav_pages[0] if nav_pages else unvisited[0]
                decision = AgentDecision({
                    "thinking": f"I should explore more of this site before making a judgment. Let me check out the {target_page['text']} page.",
                    "feeling": "curious",
                    "action": "navigate",
                    "target": target_page["url"],
                    "reasoning": f"I've only seen the homepage. Let me look at '{target_page['text']}' to get a fuller picture.",
                })
        
        logger.info(
            f"[DECIDE] ✅ Decision: action={decision.action}, target={decision.target}, "
            f"feeling={decision.feeling}, reasoning='{decision.reasoning[:100]}'"
        )
        return decision

    except Exception as e:
        logger.error(f"[DECIDE] ❌ Decision LLM call FAILED: {type(e).__name__}: {e}")
        
        # Smarter fallback: if we've been scrolling on the same page, navigate instead
        if session_history and len(session_history) >= 3:
            recent_urls = [h.get("url", "") for h in session_history[-3:]]
            if len(set(recent_urls)) == 1:  # All 3 last steps on same page
                unvisited = _get_unvisited_pages(discovered_pages or [], pages_visited or set())
                if unvisited:
                    nav_pages = [p for p in unvisited if p['source'] == 'nav']
                    target_page = nav_pages[0] if nav_pages else unvisited[0]
                    logger.warning(f"[DECIDE] ⚠️ Falling back to navigate to '{target_page['text']}' instead of scroll")
                    return AgentDecision({
                        "thinking": "I should look at other pages on this site.",
                        "feeling": "curious",
                        "action": "navigate",
                        "target": target_page["url"],
                        "reasoning": f"Navigating to '{target_page['text']}' to explore more of the site.",
                    })
        
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


def _build_page_map(discovered_pages: list[dict], pages_visited: set) -> str:
    """Build a page map showing discovered pages and their visit status."""
    if not discovered_pages:
        return "No page map available — navigate using links visible on the current page."

    lines = ["The following pages were discovered on this website:"]
    
    # Group by source
    nav_pages = [p for p in discovered_pages if p['source'] == 'nav']
    footer_pages = [p for p in discovered_pages if p['source'] == 'footer']
    content_pages = [p for p in discovered_pages if p['source'] == 'content']
    other_pages = [p for p in discovered_pages if p['source'] not in ('nav', 'footer', 'content')]

    def format_page_list(pages: list[dict], label: str) -> list[str]:
        if not pages:
            return []
        result = [f"\n**{label}:**"]
        for p in pages[:15]:  # Cap to avoid token bloat
            visited = "✅ VISITED" if p['url'] in pages_visited else "❌ NOT YET VISITED"
            result.append(f"  - [{visited}] \"{p['text']}\" → {p['url']}")
        return result

    lines.extend(format_page_list(nav_pages, "Navigation Pages (HIGHEST PRIORITY)"))
    lines.extend(format_page_list(content_pages, "Content Pages"))
    lines.extend(format_page_list(footer_pages, "Footer Pages"))
    lines.extend(format_page_list(other_pages, "Other Pages"))

    unvisited_count = sum(1 for p in discovered_pages if p['url'] not in pages_visited)
    if unvisited_count > 0:
        lines.append(f"\n⚡ {unvisited_count} pages NOT YET VISITED. Use 'navigate' action with the URL to visit them directly.")

    return "\n".join(lines)


def _build_exploration_progress(session_history: list[dict], pages_visited: set, discovered_pages: list[dict]) -> str:
    """Build exploration progress context with navigation nudging."""
    total_steps = len(session_history)
    pages_count = len(pages_visited)
    discovered_count = len(discovered_pages)
    
    lines = [
        f"Steps taken: {total_steps}",
        f"Distinct pages visited: {pages_count}",
        f"Total discovered pages: {discovered_count}",
    ]
    
    # ── Navigation nudge: detect if agent is stuck on one page ──
    if session_history and total_steps >= 3:
        recent_urls = [h.get("url", "") for h in session_history[-3:]]
        recent_actions = [h.get("action", "") for h in session_history[-3:]]
        
        if len(set(recent_urls)) == 1:  # All last 3 steps on same page
            scroll_count = sum(1 for a in recent_actions if a in ("scroll_down", "scroll_up"))
            if scroll_count >= 2:
                lines.append("")
                lines.append("🚨 NAVIGATION NUDGE: You've been scrolling on the same page for the last 3 steps.")
                lines.append("You should NAVIGATE to a different page now. Use the 'navigate' action with a URL from the Discovered Pages list above.")
                unvisited = _get_unvisited_pages(discovered_pages, pages_visited)
                if unvisited:
                    top_suggestions = unvisited[:3]
                    lines.append("Suggested pages to visit next:")
                    for p in top_suggestions:
                        lines.append(f"  → \"{p['text']}\" at {p['url']}")
    
    # Warn if trying to complete too early
    if pages_count <= 1 and total_steps > 2:
        lines.append("")
        lines.append("⚠️ You've only visited 1 page so far. You MUST explore more pages before completing the session.")
    
    return "\n".join(lines)


def _get_unvisited_pages(discovered_pages: list[dict], pages_visited: set) -> list[dict]:
    """Get pages that haven't been visited yet, prioritizing nav pages."""
    unvisited = [p for p in discovered_pages if p['url'] not in pages_visited]
    # Sort: nav first, then content, then footer, then others
    priority = {'nav': 0, 'content': 1, 'footer': 2, 'sidebar': 3, 'body': 4}
    unvisited.sort(key=lambda p: priority.get(p.get('source', 'body'), 5))
    return unvisited

