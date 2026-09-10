"""
Unified LLM router with fallback chain.
Tries providers in order: Groq → Gemini → OpenRouter → Claude.
Logs token usage to llm_usage_log for every call.
"""

import json
import logging
import time
from typing import Optional, Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class LLMResponse:
    """Standardized response from any LLM provider."""

    def __init__(
        self,
        content: str,
        provider: str,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ):
        self.content = content
        self.provider = provider
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

    def parse_json(self) -> dict:
        """Parse the content as JSON, handling markdown code blocks."""
        text = self.content.strip()
        # Strip markdown JSON code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())


# Cost estimates per 1M tokens (input/output) for common models
COST_TABLE = {
    "groq": {"input": 0.05, "output": 0.10},
    "gemini": {"input": 0.075, "output": 0.30},
    "openrouter": {"input": 0.15, "output": 0.60},
    "claude": {"input": 3.00, "output": 15.00},
}


def _estimate_cost(provider: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for a given LLM call."""
    rates = COST_TABLE.get(provider, {"input": 0.10, "output": 0.50})
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000


async def _call_groq(
    messages: list[dict],
    model: str = "openai/gpt-oss-20b",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    response_format: Optional[dict] = None,
) -> LLMResponse:
    """Call Groq API."""
    from groq import Groq

    settings = get_settings()
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY not configured")

    client = Groq(api_key=settings.groq_api_key)

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        kwargs["response_format"] = response_format

    response = client.chat.completions.create(**kwargs)

    return LLMResponse(
        content=response.choices[0].message.content or "",
        provider="groq",
        model=model,
        input_tokens=response.usage.prompt_tokens if response.usage else 0,
        output_tokens=response.usage.completion_tokens if response.usage else 0,
    )


async def _call_gemini(
    messages: list[dict],
    model: str = "gemini-2.5-flash",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    response_format: Optional[dict] = None,
) -> LLMResponse:
    """Call Gemini API."""
    import google.generativeai as genai

    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY not configured")

    genai.configure(api_key=settings.gemini_api_key)

    # Convert OpenAI-style messages to Gemini format
    system_instruction = None
    contents = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            system_instruction = content
        elif role == "user":
            contents.append({"role": "user", "parts": [{"text": content}]})
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": content}]})

    gen_config = {
        "temperature": temperature,
        "max_output_tokens": max_tokens,
    }
    if response_format and response_format.get("type") == "json_object":
        gen_config["response_mime_type"] = "application/json"

    gen_model = genai.GenerativeModel(
        model_name=model,
        system_instruction=system_instruction,
        generation_config=gen_config,
    )
    response = gen_model.generate_content(contents)

    # Estimate tokens (Gemini doesn't always return exact counts)
    input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) if hasattr(response, "usage_metadata") else 0
    output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) if hasattr(response, "usage_metadata") else 0

    return LLMResponse(
        content=response.text or "",
        provider="gemini",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


async def _call_openrouter(
    messages: list[dict],
    model: str = "openrouter/free",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    response_format: Optional[dict] = None,
) -> LLMResponse:
    """Call OpenRouter API (OpenAI-compatible)."""
    from openai import OpenAI

    settings = get_settings()
    if not settings.openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY not configured")

    client = OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        kwargs["response_format"] = response_format

    response = client.chat.completions.create(**kwargs)

    return LLMResponse(
        content=response.choices[0].message.content or "",
        provider="openrouter",
        model=model,
        input_tokens=response.usage.prompt_tokens if response.usage else 0,
        output_tokens=response.usage.completion_tokens if response.usage else 0,
    )


async def _call_claude(
    messages: list[dict],
    model: str = "claude-sonnet-4-20250514",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    response_format: Optional[dict] = None,
) -> LLMResponse:
    """Call Anthropic Claude API."""
    # pyrefly: ignore [missing-import]
    from anthropic import Anthropic

    settings = get_settings()
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    client = Anthropic(api_key=settings.anthropic_api_key)

    # Extract system message
    system_text = ""
    chat_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_text = msg["content"]
        else:
            chat_messages.append(msg)

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": chat_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if system_text:
        kwargs["system"] = system_text

    response = client.messages.create(**kwargs)

    content = ""
    for block in response.content:
        if hasattr(block, "text"):
            content += block.text

    return LLMResponse(
        content=content,
        provider="claude",
        model=model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )


# Provider dispatch table
_PROVIDERS = {
    "groq": _call_groq,
    "gemini": _call_gemini,
    "openrouter": _call_openrouter,
    "claude": _call_claude,
}


# Counter for round-robin load distribution across available providers
_rr_counter = 0


def _get_ordered_providers() -> list[str]:
    """
    Get available providers ordered with round-robin load distribution.

    If multiple providers are configured (e.g. both Groq and OpenRouter),
    alternates the primary provider on each request (Groq -> OpenRouter -> Groq -> ...)
    so traffic is evenly split and neither hits '429 Too Many Requests'.
    The other provider acts as the immediate fallback.

    If only one provider is configured, that single provider is used.
    """
    global _rr_counter
    settings = get_settings()

    configured = []
    for p in settings.llm_providers:
        if p == "groq" and settings.groq_api_key:
            configured.append("groq")
        elif p == "openrouter" and settings.openrouter_api_key:
            configured.append("openrouter")
        elif p == "gemini" and settings.gemini_api_key:
            configured.append("gemini")
        elif p == "claude" and settings.anthropic_api_key:
            configured.append("claude")

    if not configured:
        return settings.llm_providers

    if len(configured) == 1:
        return configured

    idx = _rr_counter % len(configured)
    _rr_counter += 1
    return configured[idx:] + configured[:idx]


async def call_llm(
    messages: list[dict],
    purpose: str,
    study_id: Optional[str] = None,
    session_id: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    response_format: Optional[dict] = None,
) -> LLMResponse:
    """
    Call an LLM using the configured fallback chain.
    
    Tries each provider in order. On failure, falls to the next.
    Logs token usage to llm_usage_log for every successful call.
    
    Args:
        messages: OpenAI-style message list [{role, content}, ...]
        purpose: What this call is for (logged for cost tracking)
        study_id: Optional study UUID for cost attribution
        session_id: Optional session UUID for cost attribution
        temperature: Sampling temperature
        max_tokens: Max tokens to generate
        response_format: Optional response format (e.g., {"type": "json_object"})
    
    Returns:
        LLMResponse with the content and usage info
    
    Raises:
        RuntimeError: If all providers fail
    """
    providers = _get_ordered_providers()
    logger.info(f"[LLM] Provider priority for purpose='{purpose}': {providers}")
    errors = []

    for provider_name in providers:
        provider_fn = _PROVIDERS.get(provider_name)
        if not provider_fn:
            logger.warning(f"[LLM] Unknown provider '{provider_name}', skipping")
            continue

        try:
            logger.info(f"[LLM] Trying provider '{provider_name}' for purpose='{purpose}'")
            start_time = time.time()

            response = await provider_fn(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )

            elapsed = time.time() - start_time
            logger.info(
                f"[LLM] ✅ Success: provider={provider_name}, model={response.model}, "
                f"tokens={response.input_tokens}in/{response.output_tokens}out, "
                f"elapsed={elapsed:.2f}s, purpose={purpose}"
            )

            # Log to database
            await _log_usage(
                study_id=study_id,
                session_id=session_id,
                purpose=purpose,
                provider=response.provider,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )

            return response

        except Exception as e:
            error_msg = f"Provider '{provider_name}' failed: {type(e).__name__}: {str(e)}"
            logger.error(f"[LLM] ❌ {error_msg}")
            errors.append(error_msg)
            continue

    error_detail = "\n".join(f"  • {e}" for e in errors)
    logger.critical(
        f"[LLM] 🚨 ALL PROVIDERS FAILED for purpose='{purpose}'\n"
        f"[LLM] Tried providers: {providers}\n"
        f"[LLM] Errors:\n{error_detail}\n"
        f"[LLM] 💡 Check your API keys in .env — at least one LLM provider must be configured and working."
    )
    raise RuntimeError(
        f"All LLM providers failed for purpose '{purpose}'. "
        f"Check API keys in .env. Errors:\n{error_detail}"
    )


async def call_llm_with_vision(
    messages: list[dict],
    image_base64: str,
    purpose: str,
    study_id: Optional[str] = None,
    session_id: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    response_format: Optional[dict] = None,
) -> LLMResponse:
    """
    Call an LLM with a vision-capable model, attaching an image.
    Uses a vision-specific fallback chain (only providers with vision support).
    """
    providers = _get_ordered_providers()
    logger.info(f"[LLM] Vision provider priority for purpose='{purpose}': {providers}")
    errors = []

    # Build messages with image for each provider
    for provider_name in providers:
        try:
            if provider_name == "groq":
                # Groq supports vision with qwen/qwen3.8-27b
                vision_messages = _build_vision_messages_openai_style(messages, image_base64)
                response = await _call_groq(
                    messages=vision_messages,
                    model="qwen/qwen3.8-27b",
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
            elif provider_name == "gemini":
                # Gemini natively supports vision
                vision_messages = _build_vision_messages_gemini(messages, image_base64)
                response = await _call_gemini(
                    messages=vision_messages,
                    model="gemini-2.5-flash",
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
            elif provider_name == "openrouter":
                vision_messages = _build_vision_messages_openai_style(messages, image_base64)
                response = await _call_openrouter(
                    messages=vision_messages,
                    model="nvidia/nemotron-nano-12b-vl:free",
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
            elif provider_name == "claude":
                vision_messages = _build_vision_messages_claude(messages, image_base64)
                response = await _call_claude(
                    messages=vision_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
            else:
                continue

            logger.info(f"[LLM] ✅ Vision call succeeded: provider={provider_name}, purpose={purpose}")

            await _log_usage(
                study_id=study_id,
                session_id=session_id,
                purpose=purpose,
                provider=response.provider,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )

            return response

        except Exception as e:
            error_msg = f"Vision provider '{provider_name}' failed: {type(e).__name__}: {str(e)}"
            logger.error(f"[LLM] ❌ {error_msg}")
            errors.append(error_msg)
            continue

    error_detail = "\n".join(f"  • {e}" for e in errors)
    logger.critical(
        f"[LLM] 🚨 ALL VISION PROVIDERS FAILED for purpose='{purpose}'\n"
        f"[LLM] Errors:\n{error_detail}\n"
        f"[LLM] 💡 Vision requires Groq (qwen/qwen3.8-27b), Gemini, OpenRouter, or Claude."
    )
    raise RuntimeError(
        f"All vision LLM providers failed for purpose '{purpose}'. Errors:\n{error_detail}"
    )


def _build_vision_messages_openai_style(messages: list[dict], image_base64: str) -> list[dict]:
    """Build OpenAI/Groq/OpenRouter-style vision messages."""
    result = []
    for msg in messages:
        if msg["role"] == "user" and msg == messages[-1]:
            # Add image to the last user message
            result.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": msg["content"]},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}",
                        },
                    },
                ],
            })
        else:
            result.append(msg)
    return result


def _build_vision_messages_gemini(messages: list[dict], image_base64: str) -> list[dict]:
    """Build Gemini-style messages with image. Gemini handles image inline."""
    import base64
    result = []
    for msg in messages:
        if msg["role"] == "user" and msg == messages[-1]:
            result.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": msg["content"]},
                    {
                        "type": "image_base64",
                        "image_base64": image_base64,
                        "mime_type": "image/png",
                    },
                ],
            })
        else:
            result.append(msg)
    return result


def _build_vision_messages_claude(messages: list[dict], image_base64: str) -> list[dict]:
    """Build Claude-style messages with image."""
    result = []
    for msg in messages:
        if msg["role"] == "user" and msg == messages[-1]:
            result.append({
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_base64,
                        },
                    },
                    {"type": "text", "text": msg["content"]},
                ],
            })
        else:
            result.append(msg)
    return result


async def _log_usage(
    study_id: Optional[str],
    session_id: Optional[str],
    purpose: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Log LLM usage to the database for cost tracking."""
    try:
        from app.core.supabase_client import get_supabase_client

        estimated_cost = _estimate_cost(provider, input_tokens, output_tokens)
        sb = get_supabase_client()
        sb.table("llm_usage_log").insert({
            "study_id": study_id,
            "session_id": session_id,
            "purpose": purpose,
            "model_name": model,
            "provider": provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": estimated_cost,
        }).execute()
    except Exception as e:
        logger.error(f"[LLM] Failed to log usage to DB: {e}")
