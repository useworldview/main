"""
Supabase client factory for backend/worker usage.
Uses the service-role key — never exposed to frontend.
"""

from supabase import create_client, Client
from app.core.config import get_settings

_client: Client | None = None


def get_supabase_client() -> Client:
    """Get the Supabase service-role client singleton."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _client
