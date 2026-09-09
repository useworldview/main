"""
Worker entrypoint — runs the async job processing loop.
"""

import asyncio
import logging
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.jobs.worker import run_worker

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Configure logging — both console and file
log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    datefmt=date_format,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/worker.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)


def _log_config():
    """Log configuration on startup so we can immediately see what's set."""
    try:
        from app.core.config import get_settings
        settings = get_settings()

        logger.info("=" * 60)
        logger.info("[WORKER] UseWorldview Worker Configuration")
        logger.info("=" * 60)
        logger.info(f"[WORKER] Environment: {settings.env}")
        logger.info(f"[WORKER] LLM fallback order: {settings.llm_providers}")
        logger.info(f"[WORKER] GROQ_API_KEY: {'✅ SET' if settings.groq_api_key else '❌ NOT SET'}")
        logger.info(f"[WORKER] GEMINI_API_KEY: {'✅ SET' if settings.gemini_api_key else '❌ NOT SET'}")
        logger.info(f"[WORKER] OPENROUTER_API_KEY: {'✅ SET' if settings.openrouter_api_key else '❌ NOT SET'}")
        logger.info(f"[WORKER] ANTHROPIC_API_KEY: {'✅ SET' if settings.anthropic_api_key else '❌ NOT SET'}")
        logger.info(f"[WORKER] Supabase URL: {settings.supabase_url[:40]}...")
        logger.info(f"[WORKER] Playwright headless: {settings.playwright_headless}")
        logger.info(f"[WORKER] Worker concurrency: {settings.worker_concurrency}")
        logger.info(f"[WORKER] Worker poll interval: {settings.worker_poll_interval_seconds}s")
        logger.info(f"[WORKER] Session wall clock timeout: {settings.session_wall_clock_timeout_seconds}s")
        logger.info(f"[WORKER] Max step budget: {settings.max_step_budget_default}")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"[WORKER] Failed to load config: {e}", exc_info=True)


def main():
    """Start the worker process."""
    logger.info("[WORKER] Starting UseWorldview Worker...")
    _log_config()
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("[WORKER] Worker stopped by keyboard interrupt")
    except Exception as e:
        logger.error(f"[WORKER] Worker crashed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
