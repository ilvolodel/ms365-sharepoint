"""
MS365-SharePoint MCP Server
Provides Microsoft SharePoint operations for AI agents

Tools (6):
- sharepoint_get_site: Get SharePoint site information
- sharepoint_list_sites: List accessible sites
- sharepoint_list_lists: List lists in a site
- sharepoint_get_list_items: Get items from a list
- sharepoint_create_list_item: Create item in list
- sharepoint_update_list_item: Update list item

Version: 1.0.0
"""

import os
import logging
import asyncio
from typing import Annotated, Optional, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP
from pydantic import Field

# Import operations
from .sharepoint_operations import SharePointOperations
from .auth_provider import APIKeyAuthProvider
from .trustyvault_client import get_trustyvault_token, format_trustyvault_error, decode_jwt_upn, TrustyVaultError
from .token_cache import get_cache

# Import prompts from separate folder
from .prompts import (
    get_site_info_workflow,
    list_items_workflow,
    create_item_workflow
)

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Initialize auth provider
auth_provider = APIKeyAuthProvider()

# Initialize FastMCP with auth
mcp = FastMCP("ms365-sharepoint", auth=auth_provider)

# Initialize SharePoint operations
sp_ops = SharePointOperations()

# Create FastAPI app for /health endpoint
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Background task for periodic token cleanup
async def cleanup_expired_tokens_task():
    """Background task to cleanup expired tokens every 1 hour"""
    while True:
        try:
            await asyncio.sleep(3600)  # 1 hour
            cache = get_cache()
            deleted = cache.cleanup_expired()
            if deleted > 0:
                logger.info(f"Background cleanup: removed {deleted} expired tokens")
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")


@app.on_event("startup")
async def startup_event():
    """Run on server startup"""
    # Initial cleanup
    cache = get_cache()
    deleted = cache.cleanup_expired()
    logger.info(f"Startup: Token cache initialized, cleaned {deleted} expired tokens")
    
    # Start background cleanup task
    asyncio.create_task(cleanup_expired_tokens_task())
    logger.info("Background cleanup task started (runs every 1 hour)")


@app.get("/health")
async def health_check():
    """Health check endpoint with cache stats"""
    cache = get_cache()
    stats = cache.get_stats()
    
    return {
        "status": "healthy",
        "service": "ms365-sharepoint",
        "version": "1.0.0",
        "tools": 6,
        "prompts": 3,
        "cache": {
            "total_tokens": stats["total_tokens"],
            "valid_tokens": stats["valid_tokens"],
            "expired_tokens": stats["expired_tokens"]
        }
    }

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "name": "MS365-SharePoint MCP Server",
        "version": "1.0.0",
        "description": "Microsoft SharePoint operations for AI agents",
        "tools": 6,
        "prompts": 3,
        "endpoints": {
            "mcp_sse": "/mcp/sse",
            "mcp_message": "/mcp/message",
            "health": "/health"
        },
        "tools_list": [
            "sharepoint_get_site",
            "sharepoint_list_sites",
            "sharepoint_list_lists",
            "sharepoint_get_list_items",
            "sharepoint_create_list_item",
            "sharepoint_update_list_item"
        ],
        "prompts_list": [
            "get_site_info_workflow",
            "list_items_workflow",
            "create_item_workflow"
        ]
    }

# Mount MCP SSE app
mcp_app = mcp.sse_app()
app.mount("/mcp", mcp_app)


# ============================================================================
# MCP PROMPTS (3 workflow templates - imported from src/prompts/)
# ============================================================================

# Register prompts with FastMCP
mcp.prompt()(get_site_info_workflow)
mcp.prompt()(list_items_workflow)
mcp.prompt()(create_item_workflow)


# ============================================================================
# MCP TOOLS (6 total)
# ============================================================================

@mcp.tool()
async def sharepoint_get_site(
    session_token: Annotated[str, Field(description="TrustyVault session token (from trustyvault_verify_otp)")],
    site_url: Annotated[Optional[str], Field(description="SharePoint site URL (e.g., https://contoso.sharepoint.com/sites/engineering)")] = None,
    site_id: Annotated[Optional[str], Field(description="Site ID (alternative to site_url)")] = None
) -> dict:
    """Get SharePoint site information. Provide either site_url OR site_id."""
    try:
        access_token = await get_trustyvault_token(session_token, "microsoft_graph")
        microsoft_user = decode_jwt_upn(access_token)
        
        result = sp_ops.execute("get_site", {
            "access_token": access_token,
            "microsoft_user": microsoft_user,
            "site_url": site_url,
            "site_id": site_id
        })
        return result
    except TrustyVaultError as e:
        return format_trustyvault_error(e)
    except Exception as e:
        logger.error(f"sharepoint_get_site error: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def sharepoint_list_sites(
    session_token: Annotated[str, Field(description="TrustyVault session token")],
    max_results: Annotated[int, Field(description="Max sites to return (default 50)", ge=1, le=500)] = 50,
    search: Annotated[Optional[str], Field(description="Search query (optional)")] = None
) -> dict:
    """List accessible SharePoint sites. Optional search query."""
    try:
        access_token = await get_trustyvault_token(session_token, "microsoft_graph")
        microsoft_user = decode_jwt_upn(access_token)
        
        result = sp_ops.execute("list_sites", {
            "access_token": access_token,
            "microsoft_user": microsoft_user,
            "max_results": max_results,
            "search": search
        })
        return result
    except TrustyVaultError as e:
        return format_trustyvault_error(e)
    except Exception as e:
        logger.error(f"sharepoint_list_sites error: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def sharepoint_list_lists(
    session_token: Annotated[str, Field(description="TrustyVault session token")],
    site_url: Annotated[str, Field(description="SharePoint site URL")],
    include_hidden: Annotated[bool, Field(description="Include hidden lists (default False)")] = False
) -> dict:
    """List all lists in a SharePoint site."""
    try:
        access_token = await get_trustyvault_token(session_token, "microsoft_graph")
        microsoft_user = decode_jwt_upn(access_token)
        
        result = sp_ops.execute("list_lists", {
            "access_token": access_token,
            "microsoft_user": microsoft_user,
            "site_url": site_url,
            "include_hidden": include_hidden
        })
        return result
    except TrustyVaultError as e:
        return format_trustyvault_error(e)
    except Exception as e:
        logger.error(f"sharepoint_list_lists error: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def sharepoint_get_list_items(
    session_token: Annotated[str, Field(description="TrustyVault session token")],
    site_url: Annotated[str, Field(description="SharePoint site URL")],
    list_id: Annotated[str, Field(description="List ID or title")],
    max_results: Annotated[int, Field(description="Max items (default 100, max 500)", ge=1, le=500)] = 100,
    filter: Annotated[Optional[str], Field(description="OData filter query (optional)")] = None,
    select: Annotated[Optional[str], Field(description="Comma-separated field names (optional)")] = None
) -> dict:
    """Get items from a SharePoint list. Supports filtering and field selection."""
    try:
        access_token = await get_trustyvault_token(session_token, "microsoft_graph")
        microsoft_user = decode_jwt_upn(access_token)
        
        result = sp_ops.execute("get_list_items", {
            "access_token": access_token,
            "microsoft_user": microsoft_user,
            "site_url": site_url,
            "list_id": list_id,
            "max_results": max_results,
            "filter": filter,
            "select": select
        })
        return result
    except TrustyVaultError as e:
        return format_trustyvault_error(e)
    except Exception as e:
        logger.error(f"sharepoint_get_list_items error: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def sharepoint_create_list_item(
    session_token: Annotated[str, Field(description="TrustyVault session token")],
    site_url: Annotated[str, Field(description="SharePoint site URL")],
    list_id: Annotated[str, Field(description="List ID or title")],
    fields: Annotated[Dict, Field(description="Field values as dictionary (e.g., {'Title': 'Item', 'Status': 'Active'})")]
) -> dict:
    """Create a new item in a SharePoint list."""
    try:
        access_token = await get_trustyvault_token(session_token, "microsoft_graph")
        microsoft_user = decode_jwt_upn(access_token)
        
        result = sp_ops.execute("create_list_item", {
            "access_token": access_token,
            "microsoft_user": microsoft_user,
            "site_url": site_url,
            "list_id": list_id,
            "fields": fields
        })
        return result
    except TrustyVaultError as e:
        return format_trustyvault_error(e)
    except Exception as e:
        logger.error(f"sharepoint_create_list_item error: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def sharepoint_update_list_item(
    session_token: Annotated[str, Field(description="TrustyVault session token")],
    site_url: Annotated[str, Field(description="SharePoint site URL")],
    list_id: Annotated[str, Field(description="List ID or title")],
    item_id: Annotated[str, Field(description="Item ID to update")],
    fields: Annotated[Dict, Field(description="Field values to update")]
) -> dict:
    """Update an existing SharePoint list item."""
    try:
        access_token = await get_trustyvault_token(session_token, "microsoft_graph")
        microsoft_user = decode_jwt_upn(access_token)
        
        result = sp_ops.execute("update_list_item", {
            "access_token": access_token,
            "microsoft_user": microsoft_user,
            "site_url": site_url,
            "list_id": list_id,
            "item_id": item_id,
            "fields": fields
        })
        return result
    except TrustyVaultError as e:
        return format_trustyvault_error(e)
    except Exception as e:
        logger.error(f"sharepoint_update_list_item error: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8046))
    uvicorn.run(app, host="0.0.0.0", port=port)


