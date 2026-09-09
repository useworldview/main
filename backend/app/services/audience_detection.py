"""
Audience detection service.
Uses LLM to infer target audience segments from site content.
"""

import json
import logging
from typing import Optional

from app.core.llm_client import call_llm

logger = logging.getLogger(__name__)

AUDIENCE_DETECTION_PROMPT = """You are an expert user researcher and market analyst. Your job is to analyze a website/product and identify its target audience segments.

Given the following website content and research goals, identify 3-5 distinct audience segments that would be the most likely users/visitors of this product.

For each segment, provide:
- **name**: A concise, descriptive name (e.g., "Early-Stage SaaS Founders", "Budget-Conscious Online Shoppers")
- **description**: A 2-3 sentence description of who this segment is, what they care about, and why they'd visit this product

Rules:
- Focus on DISTINCT segments — each should represent a meaningfully different type of user with different needs/behaviors
- Consider the product category, positioning, pricing signals, and content tone
- Think about both primary users AND secondary audiences (e.g., a dev tool might have both developers and engineering managers)
- Don't be generic — "tech-savvy users" is too broad. Be specific about WHO they are and WHY they're here.

Respond in JSON format:
{
  "product_category": "brief description of what this product is",
  "segments": [
    {
      "name": "Segment Name",
      "description": "2-3 sentence description"
    }
  ]
}"""


async def detect_audience_segments(
    site_context: dict,
    research_goals: list[dict],
    study_id: str,
) -> list[dict]:
    """
    Detect target audience segments from site content using LLM.
    
    Args:
        site_context: Parsed site content (title, headings, nav_links, main_text)
        research_goals: List of research goal dicts [{type, value}, ...]
        study_id: Study UUID for cost attribution
    
    Returns:
        List of segment dicts [{name, description}, ...]
    """
    # Build the user message with site context
    goals_text = "\n".join(
        f"- {g.get('value', g.get('type', 'General'))}" for g in research_goals
    )

    user_message = f"""## Website Information

**URL:** {site_context.get('url', 'Unknown')}
**Title:** {site_context.get('title', 'Unknown')}
**Meta Description:** {site_context.get('meta_description', 'None')}

### Headings
{_format_headings(site_context.get('headings', []))}

### Navigation Links
{_format_nav_links(site_context.get('nav_links', []))}

### Main Content (excerpt)
{site_context.get('main_text', '')[:4000]}

## Research Goals
{goals_text}

Based on this website, identify the target audience segments."""

    response = await call_llm(
        messages=[
            {"role": "system", "content": AUDIENCE_DETECTION_PROMPT},
            {"role": "user", "content": user_message},
        ],
        purpose="audience_detection",
        study_id=study_id,
        temperature=0.7,
        max_tokens=2048,
        response_format={"type": "json_object"},
    )

    try:
        result = response.parse_json()
        segments = result.get("segments", [])
        logger.info(f"Detected {len(segments)} audience segments for study {study_id}")
        return segments
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse audience detection response: {e}")
        # Return a default segment rather than failing
        return [
            {
                "name": "General Website Visitors",
                "description": "Visitors who arrive at this website looking to understand the product, evaluate its value, and decide whether to engage further.",
            }
        ]


def _format_headings(headings: list[dict]) -> str:
    """Format headings for the prompt."""
    if not headings:
        return "None found"
    return "\n".join(
        f"- [{h.get('level', 'h2')}] {h.get('text', '')}" for h in headings[:15]
    )


def _format_nav_links(nav_links: list[dict]) -> str:
    """Format nav links for the prompt."""
    if not nav_links:
        return "None found"
    return "\n".join(
        f"- {l.get('text', 'Unknown')} → {l.get('url', '#')}" for l in nav_links[:20]
    )
