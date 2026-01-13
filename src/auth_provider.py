"""
Custom FastMCP Auth Provider for API key validation (ENV-based)
Simple, atomic, no database dependencies.
"""
import os
from fastmcp.server.auth.providers.debug import DebugTokenVerifier


async def validate_api_key(token: str) -> bool:
    """
    Validate API key against environment variable.
    
    Args:
        token: API key from client (Bearer token or query param)
    
    Returns:
        True if valid, False otherwise
    """
    expected_key = os.getenv("MCP_API_KEY")
    
    if not expected_key:
        print("⚠️ MCP_API_KEY not configured in environment")
        return False
    
    if token == expected_key:
        print(f"✅ Valid API key (matches MCP_API_KEY)")
        return True
    else:
        print("🚫 Invalid API key")
        return False


class APIKeyAuthProvider(DebugTokenVerifier):
    """
    FastMCP Auth Provider using DebugTokenVerifier with ENV-based validation.
    
    Supports both:
    - Authorization: Bearer <token> header (FastMCP standard)
    - ?api_key=<token> query parameter (for agents that don't support headers)
    
    No database dependencies - validates against MCP_API_KEY environment variable.
    """
    
    def __init__(self):
        super().__init__(
            validate=validate_api_key,
            client_id="ms365-users-server",
            scopes=["user:read"]
        )
    
    async def extract_token(self, request) -> str | None:
        """
        Extract token from Authorization header OR api_key query param.
        
        Override FastMCP default to support both methods.
        """
        # Try Bearer header first (FastMCP standard)
        token = await super().extract_token(request)
        if token:
            return token
        
        # Fallback to query param for agents that don't support headers
        if hasattr(request, 'query_params') and 'api_key' in request.query_params:
            return request.query_params['api_key']
        
        return None
