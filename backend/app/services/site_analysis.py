"""
Site analysis service.
Fetches target URL, extracts content, detects product category and audience segments.
"""

import logging
import re
from typing import Optional
from urllib.parse import urlparse, urljoin

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.core.supabase_client import get_supabase_client
from app.core.llm_client import call_llm
from app.services.audience_detection import detect_audience_segments

logger = logging.getLogger(__name__)


async def analyze_site(payload: dict) -> None:
    """
    Main analyze_site job handler.
    
    1. Check robots.txt
    2. Fetch and parse the target URL
    3. LLM call to detect product category + audience segments
    4. Insert audience_segments rows, store site_context, set status
    """
    study_id = payload["study_id"]
    target_url = payload["target_url"]
    research_goals = payload["research_goals"]
    sb = get_supabase_client()

    # Update status
    sb.table("studies").update({
        "status": "analyzing_site",
    }).eq("id", study_id).execute()

    try:
        # Step 1: Check robots.txt
        is_allowed = await check_robots_txt(target_url)
        if not is_allowed:
            sb.table("studies").update({
                "status": "failed",
                "error_message": "Target site disallows automated access via robots.txt",
            }).eq("id", study_id).execute()
            return

        # Step 2: Fetch and parse the target URL
        site_content = await fetch_site_content(target_url)
        if not site_content:
            sb.table("studies").update({
                "status": "failed",
                "error_message": "Failed to fetch target URL — site may be unreachable or blocking automated access",
            }).eq("id", study_id).execute()
            return

        # Step 3: Clean content for LLM (strip scripts, styles, tracking)
        cleaned_content = _clean_content_for_llm(site_content["raw_html"])
        site_context = {
            "title": site_content["title"],
            "meta_description": site_content["meta_description"],
            "headings": site_content["headings"],
            "nav_links": site_content["nav_links"],
            "main_text": cleaned_content[:8000],  # Cap to avoid token bloat
            "url": target_url,
        }

        # Step 4: Detect audience segments via LLM
        segments = await detect_audience_segments(
            site_context=site_context,
            research_goals=research_goals,
            study_id=study_id,
        )

        # Step 5: Insert audience segments
        for segment in segments:
            sb.table("audience_segments").insert({
                "study_id": study_id,
                "name": segment["name"],
                "description": segment.get("description", ""),
                "source": "detected",
            }).execute()

        # Step 6: Store site context and update status
        sb.table("studies").update({
            "site_context": site_context,
            "status": "audience_ready",
        }).eq("id", study_id).execute()

        logger.info(f"Site analysis complete for study {study_id}: {len(segments)} segments detected")

    except Exception as e:
        logger.error(f"Site analysis failed for study {study_id}: {e}")
        sb.table("studies").update({
            "status": "failed",
            "error_message": f"Site analysis failed: {str(e)}",
        }).eq("id", study_id).execute()
        raise


async def check_robots_txt(target_url: str) -> bool:
    """Check robots.txt for the target URL. Returns True if allowed."""
    parsed = urlparse(target_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(robots_url)

        if response.status_code == 404:
            # No robots.txt — allowed
            return True

        if response.status_code != 200:
            # Can't read robots.txt — assume allowed
            return True

        robots_text = response.text.lower()

        # Simple robots.txt parsing — check for blanket disallow
        # We identify as UseWorldviewBot
        in_our_section = False
        in_wildcard_section = False

        for line in robots_text.split("\n"):
            line = line.strip()
            if line.startswith("user-agent:"):
                agent = line.split(":", 1)[1].strip()
                in_our_section = agent in ("useworldviewbot", "*")
                in_wildcard_section = agent == "*"
            elif (in_our_section or in_wildcard_section) and line.startswith("disallow:"):
                path = line.split(":", 1)[1].strip()
                if path == "/" or path == "/*":
                    return False  # Blanket disallow

        return True

    except Exception as e:
        logger.warning(f"Failed to check robots.txt for {target_url}: {e}")
        return True  # Assume allowed on error


async def fetch_site_content(target_url: str) -> Optional[dict]:
    """
    Fetch target URL content. First try httpx, fall back to Playwright if JS-rendered.
    Returns structured content dict or None on failure.
    """
    content = await _fetch_with_httpx(target_url)

    if content and len(content.get("main_text", "")) < 100:
        # Content looks too short — might be JS-rendered, try Playwright
        logger.info("Content looks JS-rendered, falling back to Playwright...")
        playwright_content = await _fetch_with_playwright(target_url)
        if playwright_content:
            content = playwright_content

    return content


async def _fetch_with_httpx(target_url: str) -> Optional[dict]:
    """Fetch URL with httpx (fast, no JS execution)."""
    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "UseWorldviewBot/1.0 (+https://useworldview.com/bot)"
            },
        ) as client:
            response = await client.get(target_url)

        if response.status_code != 200:
            logger.warning(f"HTTP {response.status_code} for {target_url}")
            return None

        return _parse_html(response.text, target_url)

    except Exception as e:
        logger.warning(f"httpx fetch failed for {target_url}: {e}")
        return None


async def _fetch_with_playwright(target_url: str) -> Optional[dict]:
    """Fetch URL with Playwright (JS execution, slower)."""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            page.set_default_timeout(30000)

            await page.goto(target_url, wait_until="networkidle")
            html = await page.content()
            await browser.close()

        return _parse_html(html, target_url)

    except Exception as e:
        logger.warning(f"Playwright fetch failed for {target_url}: {e}")
        return None


def _parse_html(html: str, base_url: str) -> dict:
    """Parse HTML into structured content."""
    soup = BeautifulSoup(html, "lxml")

    # Title
    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)

    # Meta description
    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag:
        meta_desc = meta_tag.get("content", "")

    # Headings
    headings = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(strip=True)
        if text:
            headings.append({"level": tag.name, "text": text[:200]})

    # Nav links
    nav_links = []
    nav = soup.find("nav")
    if nav:
        for link in nav.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True)
            if text and href:
                full_url = urljoin(base_url, href)
                nav_links.append({"text": text, "url": full_url})

    # Main text content
    # Remove script, style, and hidden elements
    for element in soup.find_all(["script", "style", "noscript", "svg", "path"]):
        element.decompose()

    main_text = soup.get_text(separator="\n", strip=True)

    return {
        "raw_html": str(soup),
        "title": title,
        "meta_description": meta_desc,
        "headings": headings[:20],
        "nav_links": nav_links[:30],
        "main_text": main_text[:10000],
    }


def _clean_content_for_llm(html: str) -> str:
    """
    Strip HTML to visible text only — no raw HTML, no script/style tags,
    no hidden form-field names or embedded tracking/personal data.
    Per PRD Section 16: minimize data sent to the LLM.
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove script, style, hidden elements
    for element in soup.find_all(["script", "style", "noscript", "svg", "path", "meta", "link"]):
        element.decompose()

    # Remove hidden elements
    for element in soup.find_all(attrs={"hidden": True}):
        element.decompose()
    for element in soup.find_all(attrs={"style": re.compile(r"display:\s*none")}):
        element.decompose()

    text = soup.get_text(separator="\n", strip=True)

    # Remove excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)

    return text.strip()
