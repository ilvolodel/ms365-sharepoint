"""Get SharePoint site information workflow"""
from mcp.server.fastmcp.prompts import base

async def get_site_info_workflow(site_url: str) -> list[base.Message]:
    """Get comprehensive SharePoint site information"""
    return [
        base.UserMessage(
            f"Get information about SharePoint site: {site_url}\n\n"
            "Use sharepoint_get_site tool with session_token and site_url.\n"
            "Then use sharepoint_list_lists to show available lists in the site."
        )
    ]
