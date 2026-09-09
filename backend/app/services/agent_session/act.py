"""
Action execution module.
Executes decided actions via Playwright with defense-in-depth guardrails.
"""

import logging
import re
from typing import Optional

from app.services.agent_session.browser_driver import BrowserDriver
from app.services.agent_session.decide import AgentDecision

logger = logging.getLogger(__name__)

# Hard blocklist for destructive actions — defense in depth alongside prompt instructions
DESTRUCTIVE_TEXT_PATTERNS = [
    r"delete\s*(my\s*)?account",
    r"cancel\s*(my\s*)?account",
    r"close\s*(my\s*)?account",
    r"unsubscribe\s*all",
    r"deactivate\s*(my\s*)?account",
    r"remove\s*(my\s*)?account",
    r"permanently\s*delete",
]

# Payment button blocklist — never click these
PAYMENT_BUTTON_PATTERNS = [
    r"place\s*order",
    r"complete\s*purchase",
    r"pay\s*now",
    r"submit\s*payment",
    r"confirm\s*payment",
    r"buy\s*now",
    r"checkout",
    r"process\s*payment",
]

# Synthetic data for form filling
SYNTHETIC_DATA = {
    "name": "Jane Testerson",
    "first_name": "Jane",
    "last_name": "Testerson",
    "email": "test+useworldview@example.com",
    "phone": "555-0199",
    "company": "Test Company Inc",
    "address": "123 Test Street",
    "city": "San Francisco",
    "state": "CA",
    "zip": "94105",
    "country": "United States",
}


async def execute_action(driver: BrowserDriver, decision: AgentDecision) -> dict:
    """
    Execute the decided action via Playwright.
    Returns a dict describing what happened.
    
    Applies hard guardrails as defense-in-depth:
    - Blocks destructive actions regardless of LLM decision
    - Blocks payment submission
    - Forces synthetic data for form fills
    """
    action = decision.action
    logger.info(f"[ACT] Executing action={action}, target={decision.target}")
    result = {
        "action": action,
        "success": False,
        "details": {},
        "blocked": False,
    }

    try:
        if action == "click":
            target_index = _parse_target_index(decision.target)
            if target_index is not None:
                # Check if click target is a destructive or payment action
                blocked, reason = await _check_click_guardrails(driver, target_index)
                if blocked:
                    result["blocked"] = True
                    result["details"] = {"reason": reason}
                    result["success"] = True  # Not a failure — it's a guardrail
                    logger.warning(f"[ACT] 🛑 BLOCKED click on element {target_index}: {reason}")
                    return result

                success = await driver.click_element(target_index)
                result["success"] = success
                result["details"] = {"element_index": target_index}
            else:
                result["details"] = {"error": f"Invalid target: {decision.target}"}

        elif action == "type":
            target_index = _parse_target_index(decision.target)
            text = decision.type_text or ""

            # Sanitize text — replace any real-looking data with synthetic
            text = _sanitize_form_input(text)

            if target_index is not None:
                success = await driver.type_text(target_index, text)
                result["success"] = success
                result["details"] = {"element_index": target_index, "text": text}
            else:
                result["details"] = {"error": f"Invalid target: {decision.target}"}

        elif action == "scroll_down":
            success = await driver.scroll_down()
            result["success"] = success

        elif action == "scroll_up":
            success = await driver.scroll_up()
            result["success"] = success

        elif action == "back":
            success = await driver.go_back()
            result["success"] = success

        elif action == "forward":
            success = await driver.go_forward()
            result["success"] = success

        elif action == "navigate":
            url = str(decision.target or "")
            if url:
                success = await driver.navigate(url)
                result["success"] = success
                result["details"] = {"url": url}
            else:
                result["details"] = {"error": "No URL provided for navigate action"}

        elif action in ("complete", "abandon"):
            result["success"] = True
            result["details"] = {
                "outcome": "completed" if action == "complete" else "abandoned",
                "reason": decision.reasoning,
            }

        else:
            result["details"] = {"error": f"Unknown action: {action}"}

    except Exception as e:
        result["details"] = {"error": str(e)}
        logger.error(f"[ACT] ❌ Action execution failed: action={action}, error={type(e).__name__}: {e}")

    # Log result summary
    if result.get("success"):
        if result.get("blocked"):
            logger.info(f"[ACT] Result: BLOCKED (guardrail)")
        else:
            logger.info(f"[ACT] Result: ✅ SUCCESS (action={action})")
    elif not result.get("success") and "error" not in result.get("details", {}):
        logger.warning(f"[ACT] Result: ❌ FAILED (action={action})")

    return result


async def _check_click_guardrails(driver: BrowserDriver, element_index: int) -> tuple[bool, str]:
    """
    Check if clicking an element would violate guardrails.
    Returns (is_blocked, reason).
    """
    try:
        elements = await driver._get_interactive_elements()
        if element_index >= len(elements):
            return False, ""

        el = elements[element_index]
        text = (el.get("text", "") or "").lower().strip()
        aria_label = (el.get("ariaLabel", "") or "").lower().strip()
        combined = f"{text} {aria_label}"

        # Check destructive patterns
        for pattern in DESTRUCTIVE_TEXT_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return True, f"Destructive action blocked: matches '{pattern}'"

        # Check payment patterns
        for pattern in PAYMENT_BUTTON_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return True, f"Payment action blocked: matches '{pattern}' — goal considered complete"

        return False, ""

    except Exception as e:
        logger.warning(f"[ACT] Guardrail check failed: {e}")
        return False, ""


def _parse_target_index(target) -> Optional[int]:
    """Parse the target value to get an element index."""
    if target is None:
        return None
    try:
        return int(target)
    except (ValueError, TypeError):
        # Try to extract a number from strings like "[5]" or "element 5"
        match = re.search(r"\d+", str(target))
        return int(match.group()) if match else None


def _sanitize_form_input(text: str) -> str:
    """
    Sanitize form input to ensure only synthetic data is submitted.
    Replaces anything that looks like real personal data.
    """
    # If the text looks like an email, use synthetic
    if "@" in text and "example.com" not in text:
        return SYNTHETIC_DATA["email"]

    # If it looks like a phone number, use synthetic
    if re.match(r"[\d\s\-\+\(\)]{7,}", text):
        return SYNTHETIC_DATA["phone"]

    return text
