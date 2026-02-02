"""List SharePoint list items workflow"""
from mcp.server.fastmcp.prompts import base

async def list_items_workflow(site_url: str, list_id: str) -> list[base.Message]:
    """Browse SharePoint list items"""
    return [
        base.UserMessage(
            f"Get items from SharePoint list: {list_id} in site: {site_url}\n\n"
            "Use sharepoint_get_list_items with session_token, site_url, and list_id."
        )
    ]
