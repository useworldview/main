"""
Playwright browser driver wrapper.
Manages headless Chromium lifecycle, screenshots, and DOM snapshots.
"""

import base64
import logging
import re
from typing import Optional
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
from playwright_stealth import stealth_async

from app.core.config import get_settings

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


def _patch_selector_loop_for_subprocess(loop):
    """Patch a Windows SelectorEventLoop to support subprocess creation.
    
    uvicorn --reload on Windows forces _WindowsSelectorEventLoop, which raises
    NotImplementedError on asyncio.create_subprocess_exec() because it doesn't
    implement _make_subprocess_transport(). Playwright needs this to launch its
    Node.js server process.
    
    This fix creates a persistent ProactorEventLoop in a background thread and
    patches the selector loop's subprocess_exec to delegate subprocess creation
    to the proactor loop. The subprocess transports and protocols are created on
    the proactor loop but are compatible because they communicate via pipes.
    
    Returns a cleanup function that stops the proactor loop and thread.
    """
    import asyncio
    import threading

    proactor_loop = asyncio.ProactorEventLoop()
    proactor_thread = threading.Thread(
        target=proactor_loop.run_forever,
        daemon=True,
        name="playwright-proactor-subprocess",
    )
    proactor_thread.start()
    logger.info("[BROWSER] Started ProactorEventLoop background thread for subprocess support")

    original_subprocess_exec = loop.subprocess_exec

    async def patched_subprocess_exec(protocol_factory, program, *args, **kwargs):
        """Delegate subprocess_exec to the ProactorEventLoop thread."""
        import concurrent.futures

        future = concurrent.futures.Future()

        async def _run_on_proactor():
            try:
                transport, protocol = await proactor_loop.subprocess_exec(
                    protocol_factory, program, *args, **kwargs
                )
                future.set_result((transport, protocol))
            except Exception as e:
                future.set_exception(e)

        asyncio.run_coroutine_threadsafe(_run_on_proactor(), proactor_loop)

        # Wait for the result without blocking the selector event loop
        result = await loop.run_in_executor(None, future.result, 30)
        return result

    loop.subprocess_exec = patched_subprocess_exec

    def cleanup():
        """Stop the proactor loop and restore the original subprocess_exec."""
        try:
            loop.subprocess_exec = original_subprocess_exec
            proactor_loop.call_soon_threadsafe(proactor_loop.stop)
            proactor_thread.join(timeout=5)
            proactor_loop.close()
            logger.info("[BROWSER] Cleaned up ProactorEventLoop background thread")
        except Exception as e:
            logger.warning(f"[BROWSER] Error cleaning up proactor thread: {e}")

    return cleanup

class BrowserDriver:
    """Manages a single browser context for an agent session."""

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def launch(self) -> None:
        """Launch a headless browser and create a page.
        
        On Windows, uvicorn --reload forces SelectorEventLoop which breaks
        Playwright's subprocess creation. We detect and fix this by temporarily
        swapping the running loop's _make_subprocess_transport to use a
        ProactorEventLoop for subprocess operations only.
        """
        import sys
        import time as _time
        _start = _time.time()
        settings = get_settings()
        logger.info(f"[BROWSER] Launching Chromium (headless={settings.playwright_headless})...")

        # ── Windows SelectorEventLoop workaround ──
        # uvicorn --reload on Windows forces _WindowsSelectorEventLoop which
        # raises NotImplementedError on asyncio.create_subprocess_exec().
        # Fix: patch the loop to delegate subprocess creation to a 
        # ProactorEventLoop running in a background thread.
        _cleanup_proactor = None
        if sys.platform == "win32":
            import asyncio as _asyncio
            loop = _asyncio.get_running_loop()
            if "Selector" in type(loop).__name__:
                logger.warning(
                    f"[BROWSER] Detected {type(loop).__name__} on Windows — "
                    "patching subprocess support for Playwright"
                )
                _cleanup_proactor = _patch_selector_loop_for_subprocess(loop)

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=settings.playwright_headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=USER_AGENT,
            locale="en-US",
            timezone_id="America/New_York",
            device_scale_factor=1,
            has_touch=False,
            is_mobile=False,
        )
        
        # Add a realistic init script to bypass webdriver detection
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        self._page = await self._context.new_page()
        
        # Apply playwright-stealth
        await stealth_async(self._page)
        
        self._page.set_default_timeout(30000)
        self._page.set_default_navigation_timeout(30000)

        # Store cleanup function for the proactor (called on close)
        self._cleanup_proactor = _cleanup_proactor

        logger.info(f"[BROWSER] ✅ Chromium launched in {_time.time() - _start:.1f}s")

    async def close(self) -> None:
        """Close the browser and all contexts."""
        logger.info("[BROWSER] Closing browser...")
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            # Clean up the proactor thread if we patched the loop
            if hasattr(self, '_cleanup_proactor') and self._cleanup_proactor:
                self._cleanup_proactor()
            logger.info("[BROWSER] Browser closed")
        except Exception as e:
            logger.warning(f"[BROWSER] Error closing browser: {e}")

    async def navigate(self, url: str) -> bool:
        """Navigate to a URL. Returns True on success."""
        logger.info(f"[BROWSER] Navigating to {url}...")
        try:
            response = await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # Best-effort wait for network to settle — many modern SPAs (Vercel,
            # Next.js, etc.) have persistent WebSocket/analytics connections that
            # prevent networkidle from ever firing. Don't fail navigation for this.
            try:
                await self._page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                logger.debug(f"[BROWSER] networkidle timeout for {url} (normal for SPAs)")
            success = response is not None and response.status < 400
            if success:
                logger.info(f"[BROWSER] ✅ Navigation success: {url} (HTTP {response.status})")
            else:
                status = response.status if response else 'no response'
                logger.warning(f"[BROWSER] ❌ Navigation failed: {url} (HTTP {status})")
            return success
        except Exception as e:
            logger.error(f"[BROWSER] ❌ Navigation to {url} failed: {type(e).__name__}: {e}")
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
            logger.error(f"[BROWSER] Screenshot failed: {e}")
            return ""

    async def take_screenshot_bytes(self) -> bytes:
        """Take a screenshot and return raw bytes (for storage upload)."""
        try:
            return await self._page.screenshot(type="png", full_page=False)
        except Exception as e:
            logger.error(f"[BROWSER] Screenshot bytes failed: {e}")
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
                        const className = el.getAttribute('class') || '';
                        const title = el.getAttribute('title') || '';
                        const hasIcon = el.querySelector('svg') !== null;
                        
                        elements.push({
                            tag, type, role, text: text.substring(0, 80),
                            href: href.substring(0, 200),
                            placeholder, ariaLabel, name, id,
                            className, title, hasIcon,
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
            logger.error(f"[BROWSER] DOM snapshot failed: {type(e).__name__}: {e}")
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
        title = el.get("title", "")
        class_name = el.get("className", "").lower()
        has_icon = el.get("hasIcon", False)

        label = text or aria_label or placeholder or title or name or ""

        # Special handling for icon-only buttons that might be close buttons
        if not label:
            if "close" in class_name or "dismiss" in class_name:
                label = "Close Icon"
            elif has_icon:
                label = "Icon Button"

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
            logger.warning(f"[BROWSER] Click on element {index} failed: {type(e).__name__}: {e}")
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
            logger.warning(f"[BROWSER] Type into element {index} failed: {type(e).__name__}: {e}")
            return False

    async def scroll_down(self) -> bool:
        """Scroll down one viewport."""
        try:
            await self._page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
            await self._page.wait_for_timeout(500)
            return True
        except Exception as e:
            logger.warning(f"[BROWSER] Scroll down failed: {e}")
            return False

    async def scroll_up(self) -> bool:
        """Scroll up one viewport."""
        try:
            await self._page.evaluate("window.scrollBy(0, -window.innerHeight * 0.8)")
            await self._page.wait_for_timeout(500)
            return True
        except Exception as e:
            logger.warning(f"[BROWSER] Scroll up failed: {e}")
            return False

    async def go_back(self) -> bool:
        """Navigate back."""
        try:
            await self._page.go_back(wait_until="domcontentloaded", timeout=10000)
            return True
        except Exception as e:
            logger.warning(f"[BROWSER] Go back failed: {e}")
            return False

    async def go_forward(self) -> bool:
        """Navigate forward."""
        try:
            await self._page.go_forward(wait_until="domcontentloaded", timeout=10000)
            return True
        except Exception as e:
            logger.warning(f"[BROWSER] Go forward failed: {e}")
            return False

    async def dismiss_overlays(self) -> list[str]:
        """
        Auto-detect and dismiss common overlays/popups/banners via JS injection.
        Returns a list of descriptions of what was dismissed.
        
        This is DETERMINISTIC — no LLM involved. Runs JS that:
        1. Finds common consent/cookie/newsletter overlays by selectors & text
        2. Clicks dismiss buttons (Accept, Close, X, Got it, etc.)
        3. Falls back to hiding overlay elements if no button found
        4. Handles common consent manager iframes (OneTrust, CookieBot, etc.)
        """
        try:
            dismissed = await self._page.evaluate("""() => {
                const dismissed = [];
                
                // ── PHASE 1: Click known dismiss buttons ──
                // Common button texts for overlay dismiss (case-insensitive matching)
                const dismissTexts = [
                    'accept all', 'accept all cookies', 'accept cookies', 'accept',
                    'agree', 'agree and continue', 'allow all', 'allow all cookies',
                    'allow cookies', 'got it', 'i agree', 'i understand', 'ok',
                    'okay', 'continue', 'dismiss', 'no thanks', 'not now',
                    'close', 'reject all', 'decline', 'deny',
                    'consent', 'i accept', 'understood',
                ];
                
                // Common selectors for cookie/consent banners
                const bannerSelectors = [
                    '[class*="cookie-banner"]', '[class*="cookie-consent"]',
                    '[class*="cookieBanner"]', '[class*="cookieConsent"]',
                    '[class*="cookie_banner"]', '[class*="cookie_consent"]',
                    '[class*="consent-banner"]', '[class*="consent-modal"]',
                    '[class*="gdpr"]', '[class*="GDPR"]',
                    '[class*="privacy-banner"]', '[class*="privacy-notice"]',
                    '[id*="cookie"]', '[id*="consent"]', '[id*="gdpr"]',
                    '[id*="onetrust"]', '[id*="OneTrust"]',
                    '[id*="cookiebot"]', '[id*="CookieBot"]',
                    '[class*="cc-banner"]', '[class*="cc-window"]',
                    '[class*="cmp-banner"]', '[class*="cmp-modal"]',
                    '[aria-label*="cookie"]', '[aria-label*="consent"]',
                    '[role="dialog"]', '[role="alertdialog"]',
                    '[class*="modal"]', '[class*="popup"]', '[class*="overlay"]',
                    '[class*="newsletter"]', '[class*="subscribe-popup"]',
                    '[class*="notification-bar"]', '[class*="announcement-bar"]',
                ];
                
                // Find and click dismiss buttons within overlay containers
                function tryClickDismissInContainer(container) {
                    // Try buttons and links first
                    const clickables = container.querySelectorAll(
                        'button, a, [role="button"], input[type="button"], input[type="submit"], span[onclick], div[onclick]'
                    );
                    
                    for (const el of clickables) {
                        const text = (el.textContent || el.value || '').trim().toLowerCase();
                        const ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase();
                        const title = (el.getAttribute('title') || '').toLowerCase();
                        const combined = text + ' ' + ariaLabel + ' ' + title;
                        
                        for (const dismissText of dismissTexts) {
                            if (combined.includes(dismissText)) {
                                try {
                                    el.click();
                                    dismissed.push('Clicked: "' + text.substring(0, 50) + '" in ' + container.tagName);
                                    return true;
                                } catch(e) {}
                            }
                        }
                    }
                    
                    // Try close buttons (X icons, close class, etc.)
                    const closeSelectors = [
                        '[class*="close"]', '[class*="dismiss"]', '[class*="reject"]',
                        '[aria-label="close"]', '[aria-label="Close"]',
                        '[aria-label="dismiss"]', '[aria-label="Dismiss"]',
                        '[title="close"]', '[title="Close"]',
                        'button svg', '.close-btn', '.close-button',
                        '[data-dismiss]', '[data-close]',
                    ];
                    
                    for (const sel of closeSelectors) {
                        try {
                            const closeBtn = container.querySelector(sel);
                            if (closeBtn) {
                                // Make sure it's the close button, not some other element
                                const closeBtnEl = closeBtn.closest('button, a, [role="button"]') || closeBtn;
                                closeBtnEl.click();
                                dismissed.push('Clicked close button in ' + container.tagName);
                                return true;
                            }
                        } catch(e) {}
                    }
                    
                    return false;
                }
                
                // ── PHASE 2: Find overlay containers ──
                for (const selector of bannerSelectors) {
                    try {
                        const elements = document.querySelectorAll(selector);
                        for (const el of elements) {
                            const rect = el.getBoundingClientRect();
                            const style = window.getComputedStyle(el);
                            
                            // Skip invisible elements
                            if (style.display === 'none' || style.visibility === 'hidden') continue;
                            if (rect.width === 0 || rect.height === 0) continue;
                            
                            // Check if this looks like an overlay (fixed/sticky position, or covers significant area)
                            const isFixed = style.position === 'fixed' || style.position === 'sticky';
                            const isAbsolute = style.position === 'absolute';
                            const coversWidth = rect.width > window.innerWidth * 0.5;
                            const hasHighZIndex = parseInt(style.zIndex) > 100;
                            const isLikelyOverlay = isFixed || (isAbsolute && (coversWidth || hasHighZIndex));
                            
                            if (isLikelyOverlay || hasHighZIndex) {
                                const clicked = tryClickDismissInContainer(el);
                                if (!clicked) {
                                    // Fallback: hide the overlay
                                    el.style.display = 'none';
                                    dismissed.push('Hidden overlay: ' + selector);
                                }
                            }
                        }
                    } catch(e) {}
                }
                
                // ── PHASE 3: Handle full-screen backdrop overlays ──
                // Use targeted selectors instead of querySelectorAll('*') to avoid
                // computing styles for every DOM element (15k+ on heavy pages).
                try {
                    const backdropCandidates = document.querySelectorAll(
                        'div[style*="fixed"], div[style*="z-index"], ' +
                        '[class*="backdrop"], [class*="overlay"], [class*="modal"], ' +
                        'dialog, [role="dialog"], [role="alertdialog"], [aria-modal="true"], ' +
                        'body > div, body > aside, body > section'
                    );
                    for (const el of backdropCandidates) {
                        const style = window.getComputedStyle(el);
                        if ((style.position === 'fixed' || style.position === 'absolute') && 
                            parseInt(style.zIndex) > 100 &&
                            el.getBoundingClientRect().width >= window.innerWidth * 0.8 &&
                            el.getBoundingClientRect().height >= window.innerHeight * 0.8) {
                            
                            // This is likely a modal backdrop or full-screen overlay
                            const clicked = tryClickDismissInContainer(el);
                            if (!clicked) {
                                el.style.display = 'none';
                                dismissed.push('Hidden full-screen overlay');
                            }
                        }
                    }
                } catch(e) {}
                
                // ── PHASE 4: Handle consent manager iframes ──
                try {
                    const iframes = document.querySelectorAll('iframe');
                    for (const iframe of iframes) {
                        const src = (iframe.getAttribute('src') || '').toLowerCase();
                        const id = (iframe.getAttribute('id') || '').toLowerCase();
                        const cls = (iframe.getAttribute('class') || '').toLowerCase();
                        
                        if (src.includes('consent') || src.includes('cookie') ||
                            id.includes('consent') || id.includes('cookie') ||
                            cls.includes('consent') || cls.includes('cookie') ||
                            src.includes('onetrust') || src.includes('cookiebot') ||
                            src.includes('trustarc') || src.includes('quantcast')) {
                            
                            try {
                                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                                const buttons = iframeDoc.querySelectorAll('button, a, [role="button"]');
                                for (const btn of buttons) {
                                    const text = (btn.textContent || '').trim().toLowerCase();
                                    for (const dismissText of dismissTexts) {
                                        if (text.includes(dismissText)) {
                                            btn.click();
                                            dismissed.push('Clicked in iframe: "' + text.substring(0, 50) + '"');
                                            break;
                                        }
                                    }
                                }
                            } catch(e) {
                                // Cross-origin iframe — can't access, try hiding the parent
                                const parent = iframe.closest('[class*="consent"], [class*="cookie"], [class*="modal"]');
                                if (parent) {
                                    parent.style.display = 'none';
                                    dismissed.push('Hidden consent iframe container');
                                }
                            }
                        }
                    }
                } catch(e) {}
                
                // ── PHASE 5: Remove scroll locks that overlays often add ──
                try {
                    document.body.style.overflow = '';
                    document.body.style.position = '';
                    document.documentElement.style.overflow = '';
                    document.body.classList.remove('modal-open', 'no-scroll', 'overflow-hidden', 'noscroll');
                } catch(e) {}
                
                return dismissed;
            }""")

            if dismissed:
                for d in dismissed:
                    logger.info(f"[BROWSER] 🧹 OVERLAY DISMISSED: {d}")
            else:
                logger.info("[BROWSER] No overlays detected to dismiss")
            
            # Small wait for any animations to complete
            await self._page.wait_for_timeout(500)
            return dismissed

        except Exception as e:
            logger.warning(f"[BROWSER] Overlay dismissal failed: {type(e).__name__}: {e}")
            return []

    async def discover_page_links(self, base_url: str) -> list[dict]:
        """
        Crawl internal navigation links from the current page's DOM.
        Returns a list of {text, url, source} dicts for same-domain links.
        
        This gives the agent a PAGE MAP so it knows what pages exist
        and can navigate to them directly instead of only scrolling.
        """
        try:
            parsed_base = urlparse(base_url)
            base_domain = parsed_base.netloc
            
            links = await self._page.evaluate("""(baseDomain) => {
                const links = [];
                const seen = new Set();
                
                function addLink(el, source) {
                    const href = el.getAttribute('href');
                    if (!href) return;
                    
                    // Skip non-navigation links
                    if (href.startsWith('#') || href.startsWith('javascript:') || 
                        href.startsWith('mailto:') || href.startsWith('tel:') ||
                        href.startsWith('data:')) return;
                    
                    // Resolve relative URLs
                    let fullUrl;
                    try {
                        fullUrl = new URL(href, window.location.href).href;
                    } catch(e) { return; }
                    
                    // Filter to same domain only
                    try {
                        const urlObj = new URL(fullUrl);
                        if (urlObj.hostname !== baseDomain && 
                            !urlObj.hostname.endsWith('.' + baseDomain)) return;
                        
                        // Skip asset URLs
                        const path = urlObj.pathname.toLowerCase();
                        if (path.match(/\.(jpg|jpeg|png|gif|svg|ico|css|js|woff|woff2|ttf|eot|pdf|zip|mp4|webm|mp3)$/)) return;
                        
                        // Normalize URL (remove trailing slash, fragment)
                        urlObj.hash = '';
                        const normalized = urlObj.href.replace(/\/$/, '');
                        
                        if (seen.has(normalized)) return;
                        seen.add(normalized);
                        
                        const text = (el.textContent || el.getAttribute('aria-label') || '').trim().substring(0, 100);
                        if (!text) return;
                        
                        links.push({
                            text: text,
                            url: normalized,
                            source: source,
                        });
                    } catch(e) {}
                }
                
                // Scan nav elements (highest priority)
                document.querySelectorAll('nav a, header a').forEach(a => addLink(a, 'nav'));
                
                // Scan footer
                document.querySelectorAll('footer a').forEach(a => addLink(a, 'footer'));
                
                // Scan main content area
                document.querySelectorAll('main a, article a, section a, [role="main"] a').forEach(a => addLink(a, 'content'));
                
                // Scan sidebar
                document.querySelectorAll('aside a, [role="complementary"] a').forEach(a => addLink(a, 'sidebar'));
                
                // Catch-all for remaining body links
                document.querySelectorAll('body a').forEach(a => addLink(a, 'body'));
                
                return links;
            }""", base_domain)

            logger.info(
                f"[BROWSER] 🗺️ Discovered {len(links)} internal page links: "
                f"nav={sum(1 for l in links if l['source'] == 'nav')}, "
                f"footer={sum(1 for l in links if l['source'] == 'footer')}, "
                f"content={sum(1 for l in links if l['source'] == 'content')}, "
                f"other={sum(1 for l in links if l['source'] not in ('nav', 'footer', 'content'))}"
            )
            return links

        except Exception as e:
            logger.warning(f"[BROWSER] Page link discovery failed: {type(e).__name__}: {e}")
            return []

    async def detect_overlay(self) -> bool:
        """
        Quick check: is there currently an overlay blocking the page?
        Returns True if an overlay is detected.
        """
        try:
            return await self._page.evaluate("""() => {
                // Check for fixed/sticky elements with high z-index covering significant area
                const allElements = document.querySelectorAll('*');
                for (const el of allElements) {
                    const style = window.getComputedStyle(el);
                    if ((style.position === 'fixed' || style.position === 'sticky') &&
                        style.display !== 'none' && style.visibility !== 'hidden') {
                        const rect = el.getBoundingClientRect();
                        const zIndex = parseInt(style.zIndex) || 0;
                        // Overlay if: high z-index + covers most of viewport
                        if (zIndex > 100 && rect.width > window.innerWidth * 0.3 && rect.height > 50) {
                            // But not navbars (typically at the very top, thin)
                            if (rect.height > 100 || rect.top > 50) {
                                return true;
                            }
                        }
                    }
                }
                
                // Check for body scroll lock (common overlay indicator)
                const bodyStyle = window.getComputedStyle(document.body);
                if (bodyStyle.overflow === 'hidden' && document.querySelector('[role="dialog"], [role="alertdialog"], [class*="modal"][class*="open"], [class*="modal"][class*="show"]')) {
                    return true;
                }
                
                return false;
            }""")
        except Exception:
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
                        className: el.getAttribute('class') || '',
                        title: el.getAttribute('title') || '',
                        hasIcon: el.querySelector('svg') !== null,
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
