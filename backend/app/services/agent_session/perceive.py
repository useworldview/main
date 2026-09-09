"""
Perception module — builds a structured view of the current page state.
Combines screenshot + DOM snapshot into a perception the agent can reason over.
"""

import logging
from typing import Optional

from app.services.agent_session.browser_driver import BrowserDriver

logger = logging.getLogger(__name__)


class Perception:
    """Represents the agent's perception of the current page state."""

    def __init__(
        self,
        url: str,
        dom_snapshot: str,
        screenshot_base64: str,
        screenshot_bytes: bytes,
    ):
        self.url = url
        self.dom_snapshot = dom_snapshot
        self.screenshot_base64 = screenshot_base64
        self.screenshot_bytes = screenshot_bytes

    def to_prompt_text(self) -> str:
        """Convert perception to text for the LLM prompt."""
        return f"""## Current Page State

{self.dom_snapshot}
"""


async def perceive(driver: BrowserDriver) -> Perception:
    """
    Perceive the current page state.
    
    Captures:
    - Current URL
    - Simplified DOM/accessibility snapshot
    - Screenshot (for vision-capable models and storage)
    """
    url = await driver.get_current_url()
    dom_snapshot = await driver.get_dom_snapshot()
    screenshot_base64 = await driver.take_screenshot()
    screenshot_bytes = await driver.take_screenshot_bytes()

    return Perception(
        url=url,
        dom_snapshot=dom_snapshot,
        screenshot_base64=screenshot_base64,
        screenshot_bytes=screenshot_bytes,
    )
