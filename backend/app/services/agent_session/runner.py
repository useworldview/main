"""
Agent session runner — the main perceive → decide → act → observe loop.
This is the autonomous browsing engine that drives each persona's session.
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.supabase_client import get_supabase_client
from app.jobs.queue import enqueue_job
from app.jobs.job_types import JobType
from app.services.agent_session.browser_driver import BrowserDriver
from app.services.agent_session.perceive import perceive
from app.services.agent_session.decide import decide
from app.services.agent_session.act import execute_action
from app.services.agent_session.guardrails import (
    check_robots_for_path,
    enforce_rate_limit,
    check_step_budget,
    check_wall_clock_timeout,
    check_for_bot_detection,
    GuardrailViolation,
    BotDetected,
)

logger = logging.getLogger(__name__)


async def run_agent_session(payload: dict) -> None:
    """
    Main agent session runner.
    
    1. Launch browser, navigate to target URL
    2. OVERLAY DISMISSAL PHASE — auto-dismiss cookie banners, popups, etc.
    3. PAGE DISCOVERY PHASE — crawl internal links to build page map
    4. Loop (bounded by step budget AND wall-clock timeout):
       - Perceive current state (with overlay detection)
       - Auto-dismiss overlays if detected mid-loop
       - Decide next action (with page map + navigation nudging)
       - Guardrail check
       - Act
       - Log interaction_events row + upload screenshot
       - Update session memory
       - Re-discover pages on navigation to new pages
    5. On completion: write terminal state, enqueue analyze_session
    """
    session_id = payload["session_id"]
    study_id = payload["study_id"]
    persona_id = payload["persona_id"]
    target_url = payload["target_url"]
    step_budget = payload.get("step_budget", 40)
    max_pages = payload.get("max_pages", 5)
    sid = session_id[:8]  # Short ID for logs

    logger.info(
        f"[SESSION:{sid}] ═══ Starting agent session ═══\n"
        f"[SESSION:{sid}]   study={study_id[:8]}, persona={persona_id[:8]}\n"
        f"[SESSION:{sid}]   target={target_url}\n"
        f"[SESSION:{sid}]   budget={step_budget} steps, max_pages={max_pages}"
    )

    sb = get_supabase_client()
    settings = get_settings()
    wall_clock_timeout = settings.session_wall_clock_timeout_seconds

    # Get persona data
    persona_result = sb.table("personas").select("*").eq("id", persona_id).single().execute()
    persona = persona_result.data

    # Get study data for research goals
    study_result = sb.table("studies").select("research_goals").eq("id", study_id).single().execute()
    research_goals = study_result.data.get("research_goals", [])

    # Update session status
    sb.table("agent_sessions").update({
        "status": "running",
        "start_time": datetime.now(timezone.utc).isoformat(),
    }).eq("id", session_id).execute()
    logger.info(f"[SESSION:{sid}] Session status set to 'running'")

    # Emit analytics event
    _emit_event(sb, study_id, "agent_session_started", {"persona_id": persona_id})

    driver = BrowserDriver()
    session_history: list[dict] = []
    pages_visited: set[str] = set()
    discovered_pages: list[dict] = []  # Page map from DOM link crawling
    step_count = 0
    consecutive_failures = 0  # Track consecutive nav/action failures
    start_time = time.time()
    outcome = "error"
    outcome_reason = "Session did not complete normally"

    try:
        # Launch browser
        logger.info(f"[SESSION:{sid}] Launching browser...")
        _update_session_progress(sb, session_id, step_count=0, current_phase="Launching browser…")
        await driver.launch()

        # Check robots.txt for target URL
        parsed = urlparse(target_url)
        is_allowed = await check_robots_for_path(target_url, parsed.path or "/")
        if not is_allowed:
            outcome = "error"
            outcome_reason = "Target site disallows automated access via robots.txt"
            logger.warning(f"[SESSION:{sid}] ❌ Blocked by robots.txt")
            return

        # Rate limit check
        await enforce_rate_limit(parsed.netloc)

        # Navigate to target URL
        logger.info(f"[SESSION:{sid}] Navigating to {target_url}...")
        _update_session_progress(sb, session_id, step_count=0, current_phase="Loading target site…")
        nav_success = await driver.navigate(target_url)
        if not nav_success:
            outcome = "error"
            outcome_reason = f"Failed to load target URL: {target_url}"
            logger.error(f"[SESSION:{sid}] ❌ Failed to load target URL")
            return

        pages_visited.add(target_url)

        # ================================================================
        # OVERLAY DISMISSAL PHASE — runs before main loop, no LLM needed
        # ================================================================
        logger.info(f"[SESSION:{sid}] 🧹 Phase 1: Auto-dismissing overlays...")
        _update_session_progress(sb, session_id, step_count=0, current_phase="Dismissing popups & cookie banners…")
        
        # First pass — dismiss immediately visible overlays
        dismissed_1 = await driver.dismiss_overlays()
        
        # Wait for delayed overlays (many appear after 1-2 seconds)
        await driver._page.wait_for_timeout(1500)
        
        # Second pass — catch delayed popups
        dismissed_2 = await driver.dismiss_overlays()
        
        all_dismissed = dismissed_1 + dismissed_2
        if all_dismissed:
            logger.info(f"[SESSION:{sid}] 🧹 Dismissed {len(all_dismissed)} overlay(s) before starting exploration")
            # Log overlay dismissal as an interaction event
            initial_screenshot = await driver.take_screenshot_bytes()
            await _log_event(
                sb=sb,
                session_id=session_id,
                sequence_no=0,
                event_type="overlay_dismissed",
                target_element=None,
                page_url=target_url,
                details={
                    "type": "auto_overlay_dismissal",
                    "dismissed": all_dismissed,
                    "count": len(all_dismissed),
                },
                screenshot_bytes=initial_screenshot,
                reasoning=f"Auto-dismissed {len(all_dismissed)} overlay(s): {', '.join(all_dismissed[:3])}",
                study_id=study_id,
            )

        # ================================================================
        # PAGE DISCOVERY PHASE — crawl internal links for page map
        # ================================================================
        logger.info(f"[SESSION:{sid}] 🗺️ Phase 2: Discovering page links...")
        _update_session_progress(sb, session_id, step_count=0, current_phase="Mapping site pages…")
        discovered_pages = await driver.discover_page_links(target_url)
        logger.info(f"[SESSION:{sid}] 🗺️ Found {len(discovered_pages)} navigable pages")

        # Log initial navigation event (after overlay dismissal)
        initial_perception = await perceive(driver)
        await _log_event(
            sb=sb,
            session_id=session_id,
            sequence_no=0,
            event_type="navigate",
            target_element=None,
            page_url=target_url,
            details={
                "type": "initial_navigation",
                "overlays_dismissed": len(all_dismissed),
                "pages_discovered": len(discovered_pages),
            },
            screenshot_bytes=initial_perception.screenshot_bytes,
            reasoning="Starting session — navigating to target URL",
            study_id=study_id,
        )

        # ================================================================
        # MAIN LOOP: perceive → decide → act → observe
        # ================================================================
        while True:
            step_count += 1
            logger.info(f"[SESSION:{sid}] ═══ STEP {step_count}/{step_budget} ═══")

            # Guardrail checks
            try:
                check_step_budget(step_count, step_budget)
                check_wall_clock_timeout(start_time, wall_clock_timeout)
            except GuardrailViolation as e:
                logger.info(f"[SESSION:{sid}] ⏱️ Budget exhausted: {e}")
                outcome = "completed"
                outcome_reason = f"Session budget reached: {str(e)}"
                break

            # PERCEIVE
            logger.info(f"[SESSION:{sid}] Step {step_count} → PERCEIVE")
            current_perception = await perceive(driver)
            current_url = current_perception.url
            pages_visited.add(current_url)

            # ── Mid-loop overlay dismissal ──
            if current_perception.has_overlay:
                logger.info(f"[SESSION:{sid}] 🧹 Mid-loop overlay detected, auto-dismissing...")
                mid_dismissed = await driver.dismiss_overlays()
                if mid_dismissed:
                    logger.info(f"[SESSION:{sid}] 🧹 Mid-loop dismissed {len(mid_dismissed)} overlay(s)")
                    # Re-perceive after dismissal
                    current_perception = await perceive(driver)
                    current_url = current_perception.url

            # Check for bot detection
            try:
                check_for_bot_detection(current_perception.dom_snapshot)
            except BotDetected as e:
                outcome = "error"
                outcome_reason = f"Target site blocked automated access: {str(e)}"
                logger.warning(f"[SESSION:{sid}] 🤖 Bot detection triggered: {e}")
                await _log_event(
                    sb=sb,
                    session_id=session_id,
                    sequence_no=step_count,
                    event_type="page_error",
                    target_element=None,
                    page_url=current_url,
                    details={"error": str(e), "type": "bot_detection"},
                    screenshot_bytes=current_perception.screenshot_bytes,
                    reasoning=str(e),
                    study_id=study_id,
                )
                break

            # Check robots.txt for new pages
            parsed_current = urlparse(current_url)
            if parsed_current.netloc == parsed.netloc:
                is_allowed = await check_robots_for_path(current_url, parsed_current.path or "/")
                if not is_allowed:
                    logger.info(f"[SESSION:{sid}] Path {parsed_current.path} disallowed by robots.txt, going back")
                    await driver.go_back()
                    continue

            # DECIDE (now with page map + navigation context)
            logger.info(f"[SESSION:{sid}] Step {step_count} → DECIDE")
            decision = await decide(
                persona=persona,
                research_goals=research_goals,
                perception_text=current_perception.to_prompt_text(),
                session_history=session_history,
                screenshot_base64=current_perception.screenshot_base64,
                study_id=study_id,
                session_id=session_id,
                discovered_pages=discovered_pages,
                pages_visited=pages_visited,
            )

            # Map action to event type
            event_type = _map_action_to_event_type(decision.action)

            # Check if session should end
            if decision.is_terminal:
                outcome = "completed" if decision.action == "complete" else "abandoned"
                outcome_reason = decision.reasoning
                logger.info(
                    f"[SESSION:{sid}] 🏁 Session ending: outcome={outcome}, "
                    f"reason='{decision.reasoning[:100]}'"
                )

                await _log_event(
                    sb=sb,
                    session_id=session_id,
                    sequence_no=step_count,
                    event_type=event_type,
                    target_element=str(decision.target) if decision.target else None,
                    page_url=current_url,
                    details={
                        "thinking": decision.thinking,
                        "feeling": decision.feeling,
                        "outcome": outcome,
                        "trust_signal": decision.trust_signal,
                        "like_or_dislike": decision.like_or_dislike,
                    },
                    screenshot_bytes=current_perception.screenshot_bytes,
                    reasoning=decision.reasoning,
                    study_id=study_id,
                )

                # Add to session history
                session_history.append({
                    "step": step_count,
                    "action": decision.action,
                    "url": current_url,
                    "reasoning": decision.reasoning,
                    "feeling": decision.feeling,
                    "thinking": decision.thinking,
                })

                break

            # ACT
            logger.info(f"[SESSION:{sid}] Step {step_count} → ACT (action={decision.action})")
            # Build a human-readable phase description
            phase_text = _describe_phase(decision, current_url)
            _update_session_progress(sb, session_id, step_count=step_count, current_phase=phase_text)
            await enforce_rate_limit(parsed.netloc, min_delay_seconds=0.5)
            action_result = await execute_action(driver, decision)

            # Check for page errors after action
            if not action_result.get("success", False) and not action_result.get("blocked", False):
                consecutive_failures += 1
                logger.warning(
                    f"[SESSION:{sid}] Action failed ({consecutive_failures}/3 consecutive)"
                )
                # Log page error
                await _log_event(
                    sb=sb,
                    session_id=session_id,
                    sequence_no=step_count,
                    event_type="page_error",
                    target_element=str(decision.target) if decision.target else None,
                    page_url=current_url,
                    details={
                        "error": action_result.get("details", {}).get("error", "Action failed"),
                        "action_attempted": decision.action,
                        "thinking": decision.thinking,
                    },
                    screenshot_bytes=current_perception.screenshot_bytes,
                    reasoning=f"Action failed: {action_result.get('details', {}).get('error', 'unknown')}",
                    study_id=study_id,
                )
                # Abort session if 3+ consecutive failures
                if consecutive_failures >= 3:
                    outcome = "error"
                    outcome_reason = "Session aborted: 3 consecutive action failures"
                    logger.error(f"[SESSION:{sid}] ❌ 3 consecutive failures — aborting session")
                    break
            else:
                consecutive_failures = 0  # Reset on success
                # Log successful action
                event_details = {
                    "thinking": decision.thinking,
                    "feeling": decision.feeling,
                    "action_result": action_result.get("details", {}),
                    "trust_signal": decision.trust_signal,
                    "like_or_dislike": decision.like_or_dislike,
                }

                if action_result.get("blocked"):
                    event_details["guardrail_blocked"] = True
                    event_details["block_reason"] = action_result.get("details", {}).get("reason", "")

                await _log_event(
                    sb=sb,
                    session_id=session_id,
                    sequence_no=step_count,
                    event_type=event_type,
                    target_element=str(decision.target) if decision.target else None,
                    page_url=current_url,
                    details=event_details,
                    screenshot_bytes=current_perception.screenshot_bytes,
                    reasoning=decision.reasoning,
                    study_id=study_id,
                )

            # Update session memory
            session_history.append({
                "step": step_count,
                "action": decision.action,
                "url": current_url,
                "reasoning": decision.reasoning,
                "feeling": decision.feeling,
                "thinking": decision.thinking,
                "target": str(decision.target) if decision.target else None,
                "success": action_result.get("success", False),
                "blocked": action_result.get("blocked", False),
            })

            # ── Re-discover pages when navigating to new pages ──
            new_url = await driver.get_current_url()
            if new_url != current_url and new_url not in pages_visited:
                logger.info(f"[SESSION:{sid}] 🗺️ Navigated to new page, re-discovering links...")
                pages_visited.add(new_url)
                new_links = await driver.discover_page_links(target_url)
                # Merge new links with existing (deduplicate by URL)
                existing_urls = {p['url'] for p in discovered_pages}
                for link in new_links:
                    if link['url'] not in existing_urls:
                        discovered_pages.append(link)
                        existing_urls.add(link['url'])
                logger.info(f"[SESSION:{sid}] 🗺️ Page map now has {len(discovered_pages)} pages")

            # Update step count in DB on EVERY step for real-time progress
            _update_session_progress(
                sb, session_id,
                step_count=step_count,
                pages_visited_count=len(pages_visited),
                current_phase=phase_text,
            )

    except Exception as e:
        import traceback as _tb
        full_tb = _tb.format_exc()
        logger.error(
            f"[SESSION:{sid}] 💥 CRASHED: {type(e).__name__}: {e}\n"
            f"[SESSION:{sid}] Full traceback:\n{full_tb}"
        )
        outcome = "error"
        outcome_reason = f"Session crashed: {type(e).__name__}: {str(e)}\n\nTraceback:\n{full_tb[:2000]}"

    finally:
        # Close browser
        await driver.close()

        # Update session with final state
        end_time = datetime.now(timezone.utc).isoformat()
        sb.table("agent_sessions").update({
            "status": "completed" if outcome != "error" else "failed",
            "end_time": end_time,
            "step_count": step_count,
            "outcome": outcome,
            "outcome_reason": outcome_reason,
            "pages_visited": len(pages_visited),
        }).eq("id", session_id).execute()

        # Emit analytics event
        _emit_event(sb, study_id, "agent_session_completed" if outcome != "error" else "agent_session_failed", {
            "persona_id": persona_id,
            "session_id": session_id,
            "outcome": outcome,
            "step_count": step_count,
            "pages_visited": len(pages_visited),
            "pages_discovered": len(discovered_pages),
            "duration_seconds": round(time.time() - start_time),
        })

        # Enqueue post-session analysis (only if we got events AND the session didn't crash)
        if step_count > 0 and outcome != "error":
            enqueue_job(
                job_type=JobType.ANALYZE_SESSION,
                payload={
                    "session_id": session_id,
                    "study_id": study_id,
                    "persona_id": persona_id,
                },
            )
            logger.info(f"[SESSION:{sid}] Enqueued post-session analysis")
        elif outcome == "error":
            logger.warning(
                f"[SESSION:{sid}] Skipping post-session analysis (session errored)"
            )

        logger.info(
            f"[SESSION:{sid}] ═══ Session finished ═══\n"
            f"[SESSION:{sid}]   outcome={outcome}\n"
            f"[SESSION:{sid}]   steps={step_count}, pages_visited={len(pages_visited)}, pages_discovered={len(discovered_pages)}\n"
            f"[SESSION:{sid}]   duration={time.time() - start_time:.1f}s\n"
            f"[SESSION:{sid}]   reason='{outcome_reason[:200]}'"
        )


async def _log_event(
    sb,
    session_id: str,
    sequence_no: int,
    event_type: str,
    target_element: Optional[str],
    page_url: str,
    details: dict,
    screenshot_bytes: bytes,
    reasoning: str,
    study_id: str,
) -> None:
    """Log an interaction event and upload screenshot to Supabase Storage."""
    screenshot_ref = None

    # Upload screenshot to storage
    if screenshot_bytes:
        try:
            filename = f"{study_id}/{session_id}/step_{sequence_no:04d}.png"
            sb.storage.from_("screenshots").upload(
                filename,
                screenshot_bytes,
                {"content-type": "image/png"},
            )
            screenshot_ref = filename
        except Exception as e:
            logger.warning(f"Failed to upload screenshot: {e}")

    # Clean details — remove None values
    clean_details = {k: v for k, v in details.items() if v is not None}

    sb.table("interaction_events").insert({
        "session_id": session_id,
        "sequence_no": sequence_no,
        "event_type": event_type,
        "target_element": target_element,
        "page_url": page_url,
        "details": clean_details,
        "screenshot_ref": screenshot_ref,
        "reasoning": reasoning,
    }).execute()


def _map_action_to_event_type(action: str) -> str:
    """Map an agent action to an interaction_events event_type."""
    mapping = {
        "click": "click",
        "type": "type",
        "scroll_down": "scroll",
        "scroll_up": "scroll",
        "back": "back",
        "forward": "forward",
        "navigate": "navigate",
        "complete": "navigate",  # Terminal actions get logged as navigate
        "abandon": "navigate",
        "search": "search",
        "wait": "wait",
    }
    return mapping.get(action, "click")


def _emit_event(sb, study_id: str, event_name: str, properties: dict) -> None:
    """Emit an analytics event."""
    try:
        # Get user_id from study
        study = sb.table("studies").select("user_id").eq("id", study_id).single().execute().data
        user_id = study.get("user_id") if study else None

        sb.table("analytics_events").insert({
            "user_id": user_id,
            "study_id": study_id,
            "event_name": event_name,
            "properties": properties,
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to emit analytics event: {e}")


def _update_session_progress(
    sb,
    session_id: str,
    step_count: int,
    current_phase: str = "",
    pages_visited_count: int = 0,
) -> None:
    """
    Update session progress in the DB on every step.
    This powers the real-time progress bar in the frontend via Supabase Realtime.
    """
    try:
        update = {
            "step_count": step_count,
            "current_phase": current_phase,
        }
        if pages_visited_count > 0:
            update["pages_visited"] = pages_visited_count
        sb.table("agent_sessions").update(update).eq("id", session_id).execute()
    except Exception as e:
        logger.warning(f"Failed to update session progress: {e}")


def _describe_phase(decision, current_url: str) -> str:
    """Build a human-readable phase description for the frontend progress display."""
    from urllib.parse import urlparse
    action = decision.action
    parsed = urlparse(current_url)
    page_name = parsed.path.strip("/").split("/")[-1] or "homepage"
    page_name = page_name.replace("-", " ").replace("_", " ").title()

    if action == "navigate":
        target_url = str(decision.target or "")
        if target_url:
            target_parsed = urlparse(target_url)
            target_page = target_parsed.path.strip("/").split("/")[-1] or "page"
            target_page = target_page.replace("-", " ").replace("_", " ").title()
            return f"Navigating to {target_page}\u2026"
        return "Navigating\u2026"
    elif action == "click":
        return f"Clicking element on {page_name}\u2026"
    elif action == "type":
        return f"Typing in form on {page_name}\u2026"
    elif action == "scroll_down":
        return f"Scrolling down on {page_name}\u2026"
    elif action == "scroll_up":
        return f"Scrolling up on {page_name}\u2026"
    elif action == "back":
        return "Going back\u2026"
    elif action == "forward":
        return "Going forward\u2026"
    elif action == "complete":
        return "Completing session\u2026"
    elif action == "abandon":
        return "Leaving site\u2026"
    else:
        return f"Exploring {page_name}\u2026"

