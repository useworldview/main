"""
JWT verification for Supabase Auth tokens.
Extracts user_id from the 'sub' claim.
"""

from functools import lru_cache
import jwt
from fastapi import HTTPException, status
from app.core.config import get_settings


@lru_cache()
def _get_jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_url)


def verify_supabase_token(token: str) -> str:
    """
    Verify a Supabase access token and return the user_id (sub claim).
    
    Supports modern asymmetric signing (ES256 / RS256 via JWKS) 
    and legacy symmetric signing (HS256).
    Raises HTTPException 401 if the token is invalid or expired.
    """
    settings = get_settings()
    try:
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg")

        if alg in ("ES256", "RS256"):
            jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
            jwks_client = _get_jwks_client(jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256"],
                audience="authenticated",
            )
        else:
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing 'sub' claim",
            )
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )
