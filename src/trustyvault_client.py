"""
TrustyVault API Client for MCP Servers

Provides helper functions to fetch OAuth tokens from TrustyVault
using session_token instead of passing access_token from agent.

Features:
- SQLite token caching (reduces TrustyVault API calls)
- Automatic expiration handling
- Refresh token management
"""

import os
import logging
from typing import Dict, Any, Optional
import httpx
import jwt
from .token_cache import get_cache

logger = logging.getLogger(__name__)

# TrustyVault Configuration (from environment)
TRUSTYVAULT_URL = os.getenv(
    "TRUSTYVAULT_URL",
    "https://trustyvault.brainaihub.tech"
)


class TrustyVaultError(Exception):
    """Base exception for TrustyVault errors."""
    def __init__(self, error_code: str, message: str, status_code: int = 500):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        super().__init__(f"{error_code}: {message}")


async def get_trustyvault_token(
    session_token: str,
    provider: str = "microsoft_graph"
) -> str:
    """
    Fetch access_token from TrustyVault using session_token with SQLite caching.
    
    Caching logic:
    1. Check cache first - if valid token exists, return immediately
    2. If cache miss/expired, fetch from TrustyVault
    3. Cache new token with expiration
    4. Extract UPN from JWT and cache it too
    
    Args:
        session_token: User's TrustyVault session token (from verify_otp)
        provider: Provider key (default: "microsoft_graph")
        
    Returns:
        access_token: Fresh OAuth token (cached or fetched)
        
    Raises:
        TrustyVaultError: If TrustyVault returns an error
        
    Example:
        >>> access_token = await get_trustyvault_token(session_token, "microsoft_graph")
        >>> # First call: fetches from TrustyVault
        >>> # Subsequent calls: returns cached token (fast!)
    """
    # Check cache first
    cache = get_cache()
    cached = cache.get(session_token, provider)
    
    if cached and cached.get("access_token"):
        logger.debug(f"Cache HIT - using cached token (session: {session_token[:8]}...)")
        return cached["access_token"]
    
    # Cache miss - fetch from TrustyVault
    logger.debug(f"Cache MISS - fetching from TrustyVault (session: {session_token[:8]}...)")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TRUSTYVAULT_URL}/api/v1/session/get-credentials",
                headers={
                    "Content-Type": "application/json"
                },
                json={
                    "session_token": session_token,
                    "provider": provider
                },
                timeout=10.0
            )
            
            # Handle error responses
            if response.status_code != 200:
                error_data = response.json()
                error_detail = error_data.get("detail", {})
                error_code = error_detail.get("error", "unknown_error")
                error_message = error_detail.get("message", "Unknown error from TrustyVault")
                
                logger.warning(
                    f"TrustyVault error: {error_code} - {error_message} "
                    f"(status: {response.status_code})"
                )
                
                raise TrustyVaultError(
                    error_code=error_code,
                    message=error_message,
                    status_code=response.status_code
                )
            
            # Parse success response
            data = response.json()
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")
            
            if not access_token:
                raise TrustyVaultError(
                    error_code="INVALID_RESPONSE",
                    message="TrustyVault returned no access_token",
                    status_code=500
                )
            
            token_refreshed = data.get("token_refreshed", False)
            expires_in = data.get("expires_in_seconds", 3600)  # Default 1 hour
            
            # Extract UPN from JWT
            try:
                microsoft_upn = decode_jwt_upn(access_token)
            except Exception as e:
                logger.warning(f"Failed to extract UPN from JWT: {e}")
                microsoft_upn = "unknown"
            
            # Cache token with expiration
            cache.set(
                session_token=session_token,
                access_token=access_token,
                refresh_token=refresh_token,
                microsoft_upn=microsoft_upn,
                expires_in_seconds=expires_in,
                provider=provider
            )
            
            logger.info(
                f"Token fetched and cached: provider={provider}, upn={microsoft_upn}, "
                f"refreshed={token_refreshed}, expires_in={expires_in}s"
            )
            
            return access_token
            
    except httpx.TimeoutException:
        logger.error(f"TrustyVault request timed out (url: {TRUSTYVAULT_URL})")
        raise TrustyVaultError(
            error_code="TIMEOUT",
            message="TrustyVault request timed out after 10 seconds",
            status_code=504
        )
    except httpx.RequestError as e:
        logger.error(f"TrustyVault request failed: {str(e)}")
        raise TrustyVaultError(
            error_code="CONNECTION_ERROR",
            message=f"Could not connect to TrustyVault: {str(e)}",
            status_code=503
        )


def format_trustyvault_error(error: TrustyVaultError) -> Dict[str, Any]:
    """
    Format TrustyVault error for MCP tool response.
    
    Args:
        error: TrustyVaultError exception
        
    Returns:
        Dictionary with user-friendly error information
        
    Example:
        >>> try:
        >>>     token = await get_trustyvault_token(session_token)
        >>> except TrustyVaultError as e:
        >>>     return format_trustyvault_error(e)
    """
    error_messages = {
        "session_expired": (
            "Your TrustyVault session has expired. "
            "Please unlock TrustyVault again with verify_otp."
        ),
        "invalid_session": (
            "Invalid session token. "
            "Please unlock TrustyVault with verify_otp to get a new session."
        ),
        "unauthorized": (
            "MCP server authentication failed. "
            "Contact your administrator (invalid TrustyVault API key)."
        ),
        "provider_not_configured": (
            "Microsoft 365 is not configured in your TrustyVault. "
            "Please add Microsoft 365 credentials in the TrustyVault dashboard."
        ),
        "TIMEOUT": (
            "TrustyVault is not responding. "
            "Please try again in a moment."
        ),
        "CONNECTION_ERROR": (
            "Could not connect to TrustyVault. "
            "Please check your internet connection or try again later."
        ),
    }
    
    user_message = error_messages.get(
        error.error_code,
        f"TrustyVault error: {error.message}"
    )
    
    return {
        "success": False,
        "error": error.error_code,
        "message": user_message,
        "details": {
            "trustyvault_error": error.message,
            "status_code": error.status_code
        }
    }


def decode_jwt_upn(access_token: str) -> Optional[str]:
    """
    Extract UPN (User Principal Name) from JWT access token.
    
    This function decodes the JWT token without signature verification
    (read-only access to claims) and extracts the user's identity.
    
    Args:
        access_token: JWT token from TrustyVault (Microsoft Graph)
        
    Returns:
        UPN string (e.g., 'user@company.com')
        
    Raises:
        ValueError: If UPN cannot be extracted from token
        
    Example:
        >>> access_token = "eyJ0eXAiOiJKV1QiLCJub25jZSI6..."
        >>> upn = decode_jwt_upn(access_token)
        >>> print(upn)  # "user@company.com"
        
    Note:
        The function tries multiple JWT claim fields in order:
        1. 'upn' (User Principal Name) - Azure AD standard
        2. 'preferred_username' - OAuth2 standard
        3. 'email' - Generic fallback
        4. 'unique_name' - Legacy Azure AD
    """
    try:
        # Decode JWT without signature verification (read-only)
        decoded = jwt.decode(access_token, options={"verify_signature": False})
        
        # Try multiple JWT claim fields (order matters)
        upn = (
            decoded.get("upn") or 
            decoded.get("preferred_username") or 
            decoded.get("email") or 
            decoded.get("unique_name")
        )
        
        if not upn:
            logger.error(f"UPN not found in JWT claims. Available claims: {list(decoded.keys())}")
            raise ValueError("UPN not found in JWT token claims")
        
        logger.debug(f"Extracted UPN from JWT: {upn}")
        return upn
        
    except jwt.DecodeError as e:
        logger.error(f"JWT decode error: {e}")
        raise ValueError(f"Invalid JWT token: {e}")
    except Exception as e:
        logger.error(f"Unexpected error decoding JWT: {e}")
        raise ValueError(f"Failed to decode JWT token: {e}")
