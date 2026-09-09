"""
Guardrails module — enforces safety constraints on agent sessions.
robots.txt compliance, rate limiting, budget enforcement, bot detection.
"""

import logging
import re
import time
from typing import Optional
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Track robots.txt cache per domain
_robots_cache: dict[str, dict] = {}

# Track request timing per domain for rate limiting
_domain_timestamps: dict[str, list[float]] = {}

# Bot detection signals
BOT_DETECTION_PATTERNS = [
    r"captcha",
    r"challenge",
    r"verify.*human",
    r"are.*you.*robot",
    r"cloudflare.*checking",
    r"access.*denied",
    r"blocked",
    r"rate.*limit",
    r"too.*many.*requests",
]

BOT_DETECTION_STATUS_CODES = {403, 429, 503}


class GuardrailViolation(Exception):
    """Raised when a guardrail is violated."""
    pass


class BotDetected(Exception):
    """Raised when the target site appears to have blocked the agent."""
    pass


async def check_robots_for_path(target_url: str, path: str) -> bool:
    """
    Check if a specific path is allowed by robots.txt.
    Caches per domain.
    """
    parsed = urlparse(target_url)
    domain = f"{parsed.scheme}://{parsed.netloc}"

    if domain not in _robots_cache:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{domain}/robots.txt")
            if response.status_code == 200:
                _robots_cache[domain] = _parse_robots(response.text)
            else:
                _robots_cache[domain] = {}  # No robots.txt or can't read it
        except Exception:
            _robots_cache[domain] = {}

    rules = _robots_cache.get(domain, {})

    # Check if path is disallowed
    disallowed = rules.get("disallow", [])
    for pattern in disallowed:
        if path.startswith(pattern):
            return False

    return True


def _parse_robots(text: str) -> dict:
    """Simple robots.txt parser."""
    rules: dict[str, list[str]] = {"disallow": [], "allow": []}
    in_relevant_section = False

    for line in text.lower().split("\n"):
        line = line.strip()
        if line.startswith("user-agent:"):
            agent = line.split(":", 1)[1].strip()
            in_relevant_section = agent in ("useworldviewbot", "*")
        elif in_relevant_section:
            if line.startswith("disallow:"):
                path = line.split(":", 1)[1].strip()
                if path:
                    rules["disallow"].append(path)
            elif line.startswith("allow:"):
                path = line.split(":", 1)[1].strip()
                if path:
                    rules["allow"].append(path)

    return rules


def enforce_rate_limit(domain: str, min_delay_seconds: float = 1.0) -> None:
    """
    Enforce rate limiting per domain.
    Sleeps if needed to maintain minimum delay between requests.
    """
    now = time.time()

    if domain not in _domain_timestamps:
        _domain_timestamps[domain] = []

    timestamps = _domain_timestamps[domain]

    # Clean old timestamps (keep last minute)
    timestamps[:] = [t for t in timestamps if now - t < 60]

    if timestamps:
        elapsed = now - timestamps[-1]
        if elapsed < min_delay_seconds:
            sleep_time = min_delay_seconds - elapsed
            time.sleep(sleep_time)

    _domain_timestamps[domain].append(time.time())


def check_step_budget(current_step: int, max_steps: int) -> None:
    """Raise if step budget is exceeded."""
    if current_step >= max_steps:
        raise GuardrailViolation(
            f"Step budget exhausted ({current_step}/{max_steps})"
        )


def check_wall_clock_timeout(start_time: float, timeout_seconds: int) -> None:
    """Raise if wall-clock timeout is exceeded."""
    elapsed = time.time() - start_time
    if elapsed >= timeout_seconds:
        raise GuardrailViolation(
            f"Wall-clock timeout exceeded ({elapsed:.0f}s / {timeout_seconds}s)"
        )


def check_for_bot_detection(page_content: str, status_code: int = 200) -> None:
    """
    Check if the page content suggests bot detection / blocking.
    Raises BotDetected if signals are found.
    """
    if status_code in BOT_DETECTION_STATUS_CODES:
        raise BotDetected(
            f"Target site returned HTTP {status_code} — likely blocking automated access"
        )

    content_lower = page_content.lower()
    for pattern in BOT_DETECTION_PATTERNS:
        if re.search(pattern, content_lower):
            # Only flag if it looks like the ENTIRE page is a challenge
            # (not just a word appearing in normal content)
            if len(content_lower) < 2000:  # Short pages are more likely to be challenges
                raise BotDetected(
                    f"Target site appears to be showing a bot challenge (matched: '{pattern}')"
                )
