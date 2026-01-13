"""
Microsoft Graph API Client.

Handles authentication and base Graph API operations.
Tokens must be provided from TrustyVault MCP.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
import requests
from dotenv import load_dotenv

# Load .env for client_id/tenant_id
env_path = Path(__file__).parent.parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

logger = logging.getLogger(__name__)


class GraphAPIError(Exception):
    """Base exception for Graph API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class MicrosoftGraphClient:
    """
    Microsoft Graph API Client.
    
    Provides authenticated access to Microsoft Graph API with automatic
    token management and error handling.
    """
    
    GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
    
    def __init__(
        self, 
        access_token: Optional[str] = None,
        client_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ):
        """
        Initialize Graph API client.
        
        Args:
            access_token: Microsoft Graph API access token (from TrustyVault)
            client_id: Microsoft client ID (from env if not provided) - for reference only
            tenant_id: Microsoft tenant ID (from env if not provided) - for reference only
        """
        self.access_token = access_token
        
        # Get client credentials from env or parameters (for reference/logging only)
        self.client_id = client_id or os.getenv('MICROSOFT_CLIENT_ID')
        self.tenant_id = tenant_id or os.getenv('MICROSOFT_TENANT_ID', 'common')
        
        if access_token:
            logger.debug("GraphClient initialized with access_token")
        else:
            logger.warning("GraphClient initialized without access_token - requests will fail")
    
    def get_token(self) -> Optional[str]:
        """
        Get the access token provided to the constructor.
        
        Note: Token refresh is handled by TrustyVault, not by this client.
        
        Returns:
            Access token or None if not set
        """
        return self.access_token
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers with authentication.
        
        Returns:
            Headers dict with Bearer token
        
        Raises:
            GraphAPIError: If no valid token is available
        """
        token = self.get_token()
        if not token:
            raise GraphAPIError("No valid access token available - token must be provided to constructor")
        
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        data: Optional[bytes] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Graph API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            endpoint: API endpoint (relative to base URL)
            params: Query parameters
            json_data: JSON body for POST/PUT/PATCH
            data: Raw bytes data (for file uploads)
            headers: Additional headers (will be merged with auth headers)
        
        Returns:
            Response JSON data or bytes
        
        Raises:
            GraphAPIError: If request fails
        """
        url = f"{self.GRAPH_API_ENDPOINT}/{endpoint.lstrip('/')}"
        req_headers = self._get_headers()
        
        # Merge additional headers
        if headers:
            req_headers.update(headers)
        
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=req_headers,
                params=params,
                json=json_data if data is None else None,
                data=data,
                timeout=30
            )
            
            # Handle different status codes
            if response.status_code == 204:
                # No content (successful DELETE usually)
                return {"success": True}
            
            # For binary content (file downloads), return raw bytes
            # Only do this for GET requests (downloads), not PUT (uploads)
            content_type = response.headers.get('Content-Type', '')
            is_download_request = method.upper() == 'GET' and (
                'application/octet-stream' in content_type or 
                endpoint.endswith('/content') or 
                endpoint.endswith('/$value') or
                '/$value' in endpoint
            )
            
            if is_download_request:
                if response.status_code == 200:
                    return response.content  # Return bytes directly
                else:
                    raise GraphAPIError(
                        f"Failed to download file: {response.status_code}",
                        status_code=response.status_code
                    )
            
            # Handle 201 Created (e.g., file uploads)
            if response.status_code == 201:
                try:
                    return response.json()
                except ValueError:
                    return {"success": True, "status_code": 201}
            
            # Try to parse JSON response
            try:
                data = response.json()
            except ValueError:
                data = {"raw_response": response.text}
            
            if response.status_code >= 400:
                error_msg = data.get('error', {}).get('message', response.text)
                raise GraphAPIError(
                    f"Graph API error: {error_msg}",
                    status_code=response.status_code,
                    response=data
                )
            
            return data
        
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise GraphAPIError(f"Request failed: {str(e)}")
    
    def get(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make GET request to Graph API.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Additional headers
        
        Returns:
            Response data
        """
        return self._make_request('GET', endpoint, params=params, headers=headers)
    
    def post(
        self,
        endpoint: str,
        json_data: Optional[Dict] = None,
        json: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make POST request to Graph API.
        
        Args:
            endpoint: API endpoint
            json_data: JSON body (deprecated, use json)
            json: JSON body
        
        Returns:
            Response data
        """
        # Support both json and json_data for backward compatibility
        body = json if json is not None else json_data
        return self._make_request('POST', endpoint, json_data=body)
    
    def patch(
        self,
        endpoint: str,
        json_data: Optional[Dict] = None,
        json: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make PATCH request to Graph API.
        
        Args:
            endpoint: API endpoint
            json_data: JSON body (deprecated, use json)
            json: JSON body
        
        Returns:
            Response data
        """
        # Support both json and json_data for backward compatibility
        body = json if json is not None else json_data
        return self._make_request('PATCH', endpoint, json_data=body)
    
    def delete(
        self,
        endpoint: str
    ) -> Dict[str, Any]:
        """
        Make DELETE request to Graph API.
        
        Args:
            endpoint: API endpoint
        
        Returns:
            Response data
        """
        return self._make_request('DELETE', endpoint)
    
    def put(
        self,
        endpoint: str,
        data: Optional[bytes] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make PUT request to Graph API (typically for file uploads).
        
        Args:
            endpoint: API endpoint
            data: Raw bytes data
            headers: Additional headers
        
        Returns:
            Response data
        """
        return self._make_request('PUT', endpoint, data=data, headers=headers)
    
    def get_user_profile(self) -> Dict[str, Any]:
        """
        Get user profile information for the authenticated user.
        
        Returns:
            User profile data
        """
        return self.get('/me')


# Alias for backward compatibility
GraphClient = MicrosoftGraphClient
