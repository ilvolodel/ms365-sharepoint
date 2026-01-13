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
# MCP TOOLS (3 total)
# ============================================================================

@mcp.tool()
async def users_get_profile(
    session_token: Annotated[str, Field(
        description="REQUIRED: TrustyVault session token (36-char UUID). Get this by calling trustyvault_verify_otp first. The agent must unlock TrustyVault with OTP before using any Microsoft 365 tools."
    )],
    target_email: Annotated[Optional[str], Field(
        description="OPTIONAL: Email OR UPN of user to lookup. Examples: 'giovanni.albero@infocert.it' (display email) OR 'GAL1234@infocert.it' (UPN). System auto-resolves both formats. If OMITTED: returns YOUR profile via /me endpoint. Use this when searching for OTHERS, omit when getting YOUR OWN info."
    )] = None
) -> dict:
    """
    Get Microsoft 365 user profile with full contact details.
    
    **Two modes:**
    1. YOUR profile: Omit target_email → uses /me endpoint (no search needed)
    2. OTHER user: Provide target_email → searches directory and returns match
    
    **Returns fields:**
    - id, displayName, mail, userPrincipalName
    - jobTitle, department, officeLocation
    - mobilePhone, businessPhones
    
    **Common workflows:**
    - "Who am I?" → Omit target_email
    - "Find Giovanni's email" → Use target_email="giovanni.albero@infocert.it"
    - "Get contact for GAL1234" → Use target_email="GAL1234@infocert.it"
    
    **Auto-resolution:**
    Accepts BOTH email display (giovanni@company.com) AND UPN (GIO123@company.com).
    System automatically resolves to correct user.
    
    **Error handling:**
    - If target_email not found: Returns error with suggestion to use users_search
    - If multiple matches: Returns first match (use users_search for disambiguation)
    
    **Note:** User identity automatically extracted from JWT token.
    """
    try:
        # Fetch fresh access_token from TrustyVault
        access_token = await get_trustyvault_token(session_token, "microsoft_graph")
        
        # Extract UPN from JWT token
        microsoft_user = decode_jwt_upn(access_token)
        
        # Execute user operation with access_token
        params = {
            "access_token": access_token,
            "microsoft_user": microsoft_user
        }
        if target_email:
            params["target_email"] = target_email
        
        result = user_ops.execute(
            action="get",
            params=params
        )
        return result
    except TrustyVaultError as e:
        logger.error(f"TrustyVault error in users_get_profile: {e.error_code}")
        return format_trustyvault_error(e)
    except Exception as e:
        logger.error(f"users_get_profile error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def users_search(
    session_token: Annotated[str, Field(
        description="REQUIRED: TrustyVault session token (36-char UUID). Get from trustyvault_verify_otp. Agent must unlock TrustyVault first."
    )],
    query: Annotated[str, Field(
        description="REQUIRED: Search text (min 2 chars). **FLEXIBLE MATCHING**: 'Mario Rossi' = 'Rossi Mario' (order-independent!). Partial works: 'Mar Ros' finds 'Mario Rossi'. Single terms: 'Rossi' finds all surnames. Searches: displayName, givenName, surname, mail, userPrincipalName."
    )],
    max_results: Annotated[int, Field(
        description="OPTIONAL: Max results (1-100, default 10). Use 5-10 for quick lookups, 50-100 for comprehensive searches.",
        ge=1, 
        le=100
    )] = 10
) -> dict:
    """
    Search Microsoft 365 directory for colleagues by name or email with FLEXIBLE MATCHING.
    
    **Purpose**: Find users in organization directory when user wants contact information.
    
    **🆕 FLEXIBLE MULTI-WORD SEARCH (v2.0.2):**
    - ✅ "Mario Rossi" = "Rossi Mario" (order-independent!)
    - ✅ "Mar Ros" finds "Mario Rossi" (partial matching)
    - ✅ "Rossi" finds all people with surname Rossi
    - ✅ Works with ANY word order and partial names
    
    **Search behavior:**
    - Query split into tokens: "mario rossi" → ["mario", "rossi"]
    - Each token checked with startsWith against: displayName, givenName, surname, mail, userPrincipalName
    - ALL tokens must match (AND logic), but flexible on which field
    - Case-insensitive, order-independent
    - Returns up to max_results (unsorted due to Graph API limitation)
    
    **Returns per user:**
    id, displayName, mail, userPrincipalName, jobTitle, department, officeLocation
    
    **Common queries:**
    - Full name any order: "Mario Rossi" OR "Rossi Mario" → Same result
    - Last name: "Rossi" → All Rossis
    - Partial shortcuts: "Mar Ros" instead of full names (faster!)
    - Email: "mario@company.com" → Direct match
    
    **⚠️ DISAMBIGUATION WORKFLOW (CRITICAL!):**
    - **0 results:** Inform user no matches found, suggest checking spelling or trying partial name
    - **1 result:** Show user the profile found ✅
    - **2+ results:** **MUST ask user which one!** Show numbered list with:
      * Full name (displayName)
      * Department (if available)
      * Job title (if available)
      * Email (for clarity)
      Example: "I found 3 people named 'Mario':
               1. Mario Rossi - IT Department - Developer - mario.rossi@company.com
               2. Mario Bianchi - Sales - Account Manager - mario.bianchi@company.com
               3. Mario Verdi - HR - Recruiter - mario.verdi@company.com
               Which one do you want to know more about?"
    - **User selects:** Use users_get_profile with selected email for full details
    
    **Use case examples:**
    - User: "Who is Mario Rossi?" → Search, show profile
    - User: "Find everyone in Sales department" → Use users_list instead
    - User: "Contact info for my manager" → Search by name, show profile
    
    **Note:** User identity automatically extracted from JWT token.
    """
    try:
        # Fetch fresh access_token from TrustyVault
        access_token = await get_trustyvault_token(session_token, "microsoft_graph")
        
        # Extract UPN from JWT token
        microsoft_user = decode_jwt_upn(access_token)
        
        # Execute search operation
        result = user_ops.execute(
            action="search",
            params={
                "access_token": access_token,
                "microsoft_user": microsoft_user,
                "query": query,
                "max_results": max_results
            }
        )
        return result
    except TrustyVaultError as e:
        logger.error(f"TrustyVault error in users_search: {e.error_code}")
        return format_trustyvault_error(e)
    except Exception as e:
        logger.error(f"users_search error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def users_list(
    session_token: Annotated[str, Field(
        description="REQUIRED: TrustyVault session token (36-char UUID). Get from trustyvault_verify_otp. Agent must unlock TrustyVault first."
    )],
    max_results: Annotated[int, Field(
        description="OPTIONAL: Max results (1-999, default 50). Use 50-100 for departments, 200-500 for full directory browsing, 999 for complete export.",
        ge=1, 
        le=999
    )] = 50,
    filters: Annotated[Optional[Dict], Field(
        description="OPTIONAL: Filter dictionary. Available keys: 'department' (exact match, e.g., 'Legal', 'IT', 'Sales'), 'job_title_contains' (partial match, e.g., 'Manager', 'Director', 'Engineer'). Example: {'department': 'Legal'} or {'department': 'IT', 'job_title_contains': 'Manager'}"
    )] = None
) -> dict:
    """
    List organization users with optional department/title filters.
    
    **Use cases:**
    - Browse directory: No filters → All users (paginated)
    - Department roster: filters={'department': 'Legal'} → All Legal dept
    - Find managers: filters={'job_title_contains': 'Manager'} → All managers
    - Specific group: filters={'department': 'IT', 'job_title_contains': 'Engineer'} → IT engineers
    
    **Filter behavior:**
    - department: EXACT match (case-sensitive). Must match Graph API field exactly.
    - job_title_contains: PARTIAL match (case-insensitive). Matches if title STARTS WITH value.
    - Multiple filters: AND logic (all must match)
    
    **Returns per user:**
    id, displayName, mail, userPrincipalName, jobTitle, department, officeLocation, phones
    
    **Performance tips:**
    - Department filter: Very fast (indexed field)
    - Job title filter: Slower (text search)
    - No filters + high max_results: Can be slow for large orgs (10k+ users)
    
    **Common patterns:**
    - "List Legal team": filters={'department': 'Legal'}, max_results=100
    - "Find all managers": filters={'job_title_contains': 'Manager'}, max_results=200
    - "IT directors": filters={'department': 'IT', 'job_title_contains': 'Director'}
    
    **Next steps:**
    - Get details: users_get_profile(target_email=result.mail)
    - Contact user: Use result.mail or result.userPrincipalName
    
    **Note:** User identity automatically extracted from JWT token.
    """
    try:
        # Fetch fresh access_token from TrustyVault
        access_token = await get_trustyvault_token(session_token, "microsoft_graph")
        
        # Extract UPN from JWT token
        microsoft_user = decode_jwt_upn(access_token)
        
        # Execute list operation
        params = {
            "access_token": access_token,
            "microsoft_user": microsoft_user,
            "max_results": max_results
        }
        if filters:
            params["filters"] = filters
        
        result = user_ops.execute(
            action="list",
            params=params
        )
        return result
    except TrustyVaultError as e:
        logger.error(f"TrustyVault error in users_list: {e.error_code}")
        return format_trustyvault_error(e)
    except Exception as e:
        logger.error(f"users_list error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8013))
    uvicorn.run(app, host="0.0.0.0", port=port)
