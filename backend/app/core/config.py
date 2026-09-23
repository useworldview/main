"""
Configuration management for UseWorldview backend.
All env vars loaded via pydantic-settings with proper defaults.
"""

# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase
    supabase_url: str
    supabase_service_role_key: str
    supabase_jwt_secret: str

    # LLM API Keys (need at least one)
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # LLM fallback order
    llm_fallback_order: str = "groq,gemini,openrouter,claude"

    # Browser automation
    playwright_headless: bool = True

    # Agent session budgets
    max_step_budget_default: int = 40
    max_pages_default: int = 5
    session_wall_clock_timeout_seconds: int = 600

    # Worker config
    worker_poll_interval_seconds: int = 2
    worker_concurrency: int = 2
    worker_idle_shutdown_seconds: int = 30  # Cloud Run: exit after N seconds with no jobs

    # Run mode: "unified" (API + worker in one process), "api_only", "worker_only", "webhook"
    run_mode: str = "unified"
    
    # Webhook secret for Supabase Cloud Run triggering
    webhook_secret: Optional[str] = None

    # Frontend URL
    frontend_url: str = "http://localhost:3000"

    # Persona limits
    max_personas_per_study: int = 10

    # Data retention
    screenshot_retention_days: int = 90

    # Environment
    env: str = "development"

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def llm_providers(self) -> list[str]:
        """Ordered list of LLM providers to try."""
        return [p.strip() for p in self.llm_fallback_order.split(",")]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
