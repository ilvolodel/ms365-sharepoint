"""Create SharePoint list item workflow"""
from mcp.server.fastmcp.prompts import base

async def create_item_workflow(site_url: str, list_id: str, fields: dict) -> list[base.Message]:
    """Create item in SharePoint list"""
    return [
        base.UserMessage(
            f"Create item in SharePoint list: {list_id}\n"
            f"Site: {site_url}\n"
            f"Fields: {fields}\n\n"
            "Use sharepoint_create_list_item with session_token, site_url, list_id, and fields."
        )
    ]
