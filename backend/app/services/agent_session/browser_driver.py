"""
Playwright browser driver wrapper.
Manages headless Chromium lifecycle, screenshots, and DOM snapshots.
"""

import base64
import logging
import re
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from app.core.config import get_settings

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 UseWorldviewBot/1.0"


class BrowserDriver:
    """Manages a single browser context for an agent session."""

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def launch(self) -> None:
        """Launch a headless browser and create a page."""
        settings = get_settings()
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=settings.playwright_headless,
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=USER_AGENT,
            locale="en-US",
            timezone_id="America/New_York",
        )
        self._page = await self._context.new_page()
        self._page.set_default_timeout(30000)
        self._page.set_default_navigation_timeout(30000)

    async def close(self) -> None:
        """Close the browser and all contexts."""
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")

    async def navigate(self, url: str) -> bool:
        """Navigate to a URL. Returns True on success."""
        try:
            response = await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # Wait for initial content to render
            await self._page.wait_for_load_state("networkidle", timeout=10000)
            return response is not None and response.status < 400
        except Exception as e:
            logger.warning(f"Navigation to {url} failed: {e}")
            return False

    async def take_screenshot(self) -> str:
        """Take a full-page screenshot and return as base64."""
        try:
            screenshot_bytes = await self._page.screenshot(
                type="png",
                full_page=False,  # viewport only, not full page
            )
            return base64.b64encode(screenshot_bytes).decode("utf-8")
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return ""

    async def take_screenshot_bytes(self) -> bytes:
        """Take a screenshot and return raw bytes (for storage upload)."""
        try:
            return await self._page.screenshot(type="png", full_page=False)
        except Exception as e:
            logger.error(f"Screenshot bytes failed: {e}")
            return b""

    async def get_dom_snapshot(self) -> str:
        """
        Get a simplified DOM/accessibility snapshot of the current page.
        Returns a structured text representation that the LLM can reason over.
        """
        try:
            # Get accessible elements — this is what the agent "sees"
            snapshot = await self._page.evaluate("""() => {
                function getInteractiveElements() {
                    const elements = [];
                    const all = document.querySelectorAll(
                        'a, button, input, select, textarea, [role="button"], [role="link"], ' +
                        '[role="tab"], [role="menuitem"], [onclick], [tabindex]'
                    );
                    
                    for (const el of all) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width === 0 || rect.height === 0) continue;
                        if (rect.top > window.innerHeight * 2) continue;
                        
                        const style = window.getComputedStyle(el);
                        if (style.display === 'none' || style.visibility === 'hidden') continue;
                        
                        const text = (el.textContent || '').trim().substring(0, 100);
                        const tag = el.tagName.toLowerCase();
                        const type = el.getAttribute('type') || '';
                        const role = el.getAttribute('role') || '';
                        const href = el.getAttribute('href') || '';
                        const placeholder = el.getAttribute('placeholder') || '';
                        const ariaLabel = el.getAttribute('aria-label') || '';
                        const name = el.getAttribute('name') || '';
                        const id = el.getAttribute('id') || '';
                        
                        elements.push({
                            tag, type, role, text: text.substring(0, 80),
                            href: href.substring(0, 200),
                            placeholder, ariaLabel, name, id,
                            x: Math.round(rect.x), y: Math.round(rect.y),
                            width: Math.round(rect.width), height: Math.round(rect.height),
                            visible: rect.top < window.innerHeight && rect.bottom > 0,
                        });
                    }
                    return elements;
                }
                
                function getPageInfo() {
                    const title = document.title;
                    const url = window.location.href;
                    const h1 = document.querySelector('h1');
                    const headings = [];
                    document.querySelectorAll('h1, h2, h3').forEach(h => {
                        const text = h.textContent.trim().substring(0, 100);
                        if (text) headings.push({ level: h.tagName, text });
                    });
                    
                    // Get visible text content (truncated)
                    const body = document.body;
                    const visibleText = body ? body.innerText.substring(0, 3000) : '';
                    
                    return {
                        title, url,
                        h1: h1 ? h1.textContent.trim() : '',
                        headings: headings.slice(0, 10),
                        visibleText,
                    };
                }
                
                return {
                    pageInfo: getPageInfo(),
                    elements: getInteractiveElements(),
                };
            }""")

            return self._format_snapshot(snapshot)

        except Exception as e:
            logger.error(f"DOM snapshot failed: {e}")
            return "Failed to capture DOM snapshot"

    def _format_snapshot(self, snapshot: dict) -> str:
        """Format the DOM snapshot into a readable text representation."""
        page_info = snapshot.get("pageInfo", {})
        elements = snapshot.get("elements", [])

        lines = [
            f"## Current Page",
            f"URL: {page_info.get('url', 'Unknown')}",
            f"Title: {page_info.get('title', 'Unknown')}",
            f"H1: {page_info.get('h1', 'None')}",
            "",
            "## Headings",
        ]

        for h in page_info.get("headings", []):
            lines.append(f"  [{h['level']}] {h['text']}")

        lines.extend(["", "## Interactive Elements (visible on page)"])

        for i, el in enumerate(elements):
            if not el.get("visible", False):
                continue

            desc = self._describe_element(el)
            if desc:
                lines.append(f"  [{i}] {desc}")

        lines.extend(["", "## Page Content (excerpt)"])
        visible_text = page_info.get("visibleText", "")
        if visible_text:
            # Truncate to avoid token bloat
            lines.append(visible_text[:2000])

        return "\n".join(lines)

    def _describe_element(self, el: dict) -> str:
        """Create a human-readable description of an interactive element."""
        tag = el.get("tag", "")
        text = el.get("text", "")
        etype = el.get("type", "")
        role = el.get("role", "")
        href = el.get("href", "")
        placeholder = el.get("placeholder", "")
        aria_label = el.get("ariaLabel", "")
        name = el.get("name", "")

        label = text or aria_label or placeholder or name or ""

        if tag == "a":
            return f"Link: \"{label}\" → {href}" if href else f"Link: \"{label}\""
        elif tag == "button" or role == "button":
            return f"Button: \"{label}\""
        elif tag == "input":
            input_desc = f"Input ({etype})"
            if placeholder:
                input_desc += f": placeholder=\"{placeholder}\""
            if label and label != placeholder:
                input_desc += f" label=\"{label}\""
            return input_desc
        elif tag == "select":
            return f"Dropdown: \"{label}\""
        elif tag == "textarea":
            return f"TextArea: \"{label or placeholder}\""
        elif role:
            return f"{role}: \"{label}\""
        elif label:
            return f"{tag}: \"{label}\""

        return ""

    async def click_element(self, index: int) -> bool:
        """Click an element by its index from the DOM snapshot."""
        try:
            elements = await self._get_interactive_elements()
            if index < 0 or index >= len(elements):
                logger.warning(f"Element index {index} out of range")
                return False

            el = elements[index]
            selector = self._build_selector(el)
            if selector:
                await self._page.click(selector, timeout=5000)
                await self._page.wait_for_load_state("domcontentloaded", timeout=5000)
                return True
            else:
                # Fall back to coordinate-based click
                x = el.get("x", 0) + el.get("width", 0) // 2
                y = el.get("y", 0) + el.get("height", 0) // 2
                await self._page.mouse.click(x, y)
                await self._page.wait_for_load_state("domcontentloaded", timeout=5000)
                return True

        except Exception as e:
            logger.warning(f"Click on element {index} failed: {e}")
            return False

    async def type_text(self, index: int, text: str) -> bool:
        """Type text into an input element by its index."""
        try:
            elements = await self._get_interactive_elements()
            if index < 0 or index >= len(elements):
                return False

            el = elements[index]
            selector = self._build_selector(el)
            if selector:
                await self._page.fill(selector, text, timeout=5000)
                return True
            return False

        except Exception as e:
            logger.warning(f"Type into element {index} failed: {e}")
            return False

    async def scroll_down(self) -> bool:
        """Scroll down one viewport."""
        try:
            await self._page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
            await self._page.wait_for_timeout(500)
            return True
        except Exception as e:
            logger.warning(f"Scroll failed: {e}")
            return False

    async def scroll_up(self) -> bool:
        """Scroll up one viewport."""
        try:
            await self._page.evaluate("window.scrollBy(0, -window.innerHeight * 0.8)")
            await self._page.wait_for_timeout(500)
            return True
        except Exception as e:
            logger.warning(f"Scroll failed: {e}")
            return False

    async def go_back(self) -> bool:
        """Navigate back."""
        try:
            await self._page.go_back(wait_until="domcontentloaded", timeout=10000)
            return True
        except Exception as e:
            logger.warning(f"Go back failed: {e}")
            return False

    async def go_forward(self) -> bool:
        """Navigate forward."""
        try:
            await self._page.go_forward(wait_until="domcontentloaded", timeout=10000)
            return True
        except Exception as e:
            logger.warning(f"Go forward failed: {e}")
            return False

    async def get_current_url(self) -> str:
        """Get the current page URL."""
        return self._page.url if self._page else ""

    async def _get_interactive_elements(self) -> list[dict]:
        """Get all interactive elements on the current page."""
        try:
            return await self._page.evaluate("""() => {
                const elements = [];
                const all = document.querySelectorAll(
                    'a, button, input, select, textarea, [role="button"], [role="link"], ' +
                    '[role="tab"], [role="menuitem"], [onclick], [tabindex]'
                );
                for (const el of all) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) continue;
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden') continue;
                    elements.push({
                        tag: el.tagName.toLowerCase(),
                        type: el.getAttribute('type') || '',
                        role: el.getAttribute('role') || '',
                        text: (el.textContent || '').trim().substring(0, 100),
                        href: el.getAttribute('href') || '',
                        placeholder: el.getAttribute('placeholder') || '',
                        ariaLabel: el.getAttribute('aria-label') || '',
                        name: el.getAttribute('name') || '',
                        id: el.getAttribute('id') || '',
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        width: Math.round(rect.width), height: Math.round(rect.height),
                        visible: rect.top < window.innerHeight && rect.bottom > 0,
                    });
                }
                return elements;
            }""")
        except Exception:
            return []

    def _build_selector(self, el: dict) -> Optional[str]:
        """Build a CSS selector for an element."""
        el_id = el.get("id", "")
        if el_id:
            return f"#{el_id}"

        tag = el.get("tag", "")
        name = el.get("name", "")
        if name:
            return f"{tag}[name='{name}']"

        aria_label = el.get("ariaLabel", "")
        if aria_label:
            return f"{tag}[aria-label='{aria_label}']"

        # Fall back to None — caller will use coordinates
        return None
