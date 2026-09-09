"""
FastAPI dependencies for route handlers.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import verify_supabase_token

# Bearer token scheme
bearer_scheme = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """
    FastAPI dependency that verifies the Bearer token and returns the user's UUID.
    401 on invalid/missing tokens.
    """
    return verify_supabase_token(credentials.credentials)
