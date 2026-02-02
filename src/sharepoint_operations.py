"""
SharePoint Operations Module.

Handles Microsoft SharePoint operations via Graph API:
- Sites (get, list, search)
- Lists (enumerate lists in sites)
- List Items (read, create, update)
"""

import logging
from typing import Dict, Any, Optional
from .graph_client import GraphClient, GraphAPIError

logger = logging.getLogger(__name__)


class SharePointOperations:
    """SharePoint business logic."""
    
    def __init__(self):
        pass
    
    def execute(self, action: str, params: dict) -> dict:
        """
        Execute a SharePoint operation.
        
        Args:
            action: Operation name (get_site, list_sites, list_lists, get_list_items, create_list_item, update_list_item)
            params: Operation parameters
        
        Returns:
            dict: Operation result with success flag
        """
        actions = {
            "get_site": self._get_site,
            "list_sites": self._list_sites,
            "list_lists": self._list_lists,
            "get_list_items": self._get_list_items,
            "create_list_item": self._create_list_item,
            "update_list_item": self._update_list_item,
        }
        
        if action not in actions:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }
        
        try:
            return actions[action](params)
        except GraphAPIError as e:
            logger.error(f"Graph API error in {action}: {e}")
            return {
                "success": False,
                "error": str(e),
                "status_code": e.status_code
            }
        except Exception as e:
            logger.error(f"Unexpected error in {action}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_site(self, params: dict) -> dict:
        """
        Get SharePoint site information by URL or ID.
        
        Args:
            params: Must contain:
                - access_token: Microsoft Graph access token
                - microsoft_user: User UPN (for logging)
                - site_url (optional): Full SharePoint site URL
                - site_id (optional): Site ID
        
        Returns:
            Site metadata
        """
        access_token = params["access_token"]
        site_url = params.get("site_url")
        site_id = params.get("site_id")
        
        if not site_url and not site_id:
            return {
                "success": False,
                "error": "Either site_url or site_id must be provided"
            }
        
        # Convert site URL to site ID if URL provided
        if site_url:
            # Parse SharePoint URL: https://contoso.sharepoint.com/sites/engineering
            # → contoso.sharepoint.com:/sites/engineering:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(site_url)
                hostname = parsed.netloc
                path = parsed.path.rstrip('/')
                
                # Format: hostname:path:
                site_path = f"{hostname}:{path}:"
                
                logger.info(f"Resolving site URL to path: {site_path}")
                
                # GET /sites/{hostname}:{path}:
                response = GraphClient(access_token).get(
                    endpoint=f"/sites/{site_path}",
                )
            except Exception as e:
                logger.error(f"Error parsing site URL: {e}")
                return {
                    "success": False,
                    "error": f"Invalid site URL format: {str(e)}"
                }
        else:
            # Use site ID directly
            response = GraphClient(access_token).get(
                endpoint=f"/sites/{site_id}",
            )
        
        return {
            "success": True,
            "site": {
                "id": response.get("id"),
                "name": response.get("name") or response.get("displayName"),
                "description": response.get("description"),
                "web_url": response.get("webUrl"),
                "created_date_time": response.get("createdDateTime"),
                "last_modified_date_time": response.get("lastModifiedDateTime"),
            }
        }
    
    def _list_sites(self, params: dict) -> dict:
        """
        List accessible SharePoint sites.
        
        Args:
            params: Must contain:
                - access_token: Microsoft Graph access token
                - microsoft_user: User UPN
                - max_results (optional): Max sites to return (default 50)
                - search (optional): Search query
        
        Returns:
            List of sites
        """
        access_token = params["access_token"]
        max_results = params.get("max_results", 50)
        search = params.get("search")
        
        # Build endpoint
        if search:
            # Search sites
            endpoint = f"/sites?search={search}&$top={max_results}"
        else:
            # List all accessible sites (root + subsites)
            endpoint = f"/sites?$top={max_results}"
        
        response = GraphClient(access_token).get(
            endpoint=endpoint,
        )
        
        sites = response.get("value", [])
        
        # If no followed sites found and no explicit search, try broad search
        if len(sites) == 0 and not search:
            logger.info("No followed sites found, attempting broad search for accessible sites")
            # Try searching with common keywords that often match site names
            # This helps discover sites the user has access to but hasn't followed
            search_terms = ["site", "team", "project", "department", "group"]
            all_sites = []
            seen_ids = set()
            
            for term in search_terms:
                try:
                    search_endpoint = f"/sites?search={term}&$top=100"
                    search_response = GraphClient(access_token).get(
                        endpoint=search_endpoint,
                    )
                    found_sites = search_response.get("value", [])
                    
                    # Deduplicate by site ID
                    for site in found_sites:
                        site_id = site.get("id")
                        if site_id and site_id not in seen_ids:
                            seen_ids.add(site_id)
                            all_sites.append(site)
                    
                    # Stop if we found enough sites
                    if len(all_sites) >= max_results:
                        break
                except Exception as e:
                    logger.warning(f"Search term '{term}' failed: {e}")
                    continue
            
            sites = all_sites[:max_results]
            
            if len(sites) > 0:
                logger.info(f"Broad search found {len(sites)} accessible sites")
        
        return {
            "success": True,
            "count": len(sites),
            "sites": [
                {
                    "id": site.get("id"),
                    "name": site.get("name") or site.get("displayName"),
                    "description": site.get("description"),
                    "web_url": site.get("webUrl"),
                    "created_date_time": site.get("createdDateTime"),
                }
                for site in sites
            ]
        }
    
    def _list_lists(self, params: dict) -> dict:
        """
        List all lists in a SharePoint site.
        
        Args:
            params: Must contain:
                - access_token: Microsoft Graph access token
                - site_url: SharePoint site URL
                - include_hidden (optional): Include hidden lists (default False)
        
        Returns:
            List of lists
        """
        access_token = params["access_token"]
        site_url = params["site_url"]
        include_hidden = params.get("include_hidden", False)
        
        # Get site ID from URL
        site_result = self._get_site({
            "access_token": access_token,
            "microsoft_user": params.get("microsoft_user"),
            "site_url": site_url
        })
        
        if not site_result["success"]:
            return site_result
        
        site_id = site_result["site"]["id"]
        
        # GET /sites/{site-id}/lists
        response = GraphClient(access_token).get(
            endpoint=f"/sites/{site_id}/lists",
        )
        
        lists = response.get("value", [])
        
        # Filter hidden lists if requested
        if not include_hidden:
            lists = [l for l in lists if not l.get("hidden", False)]
        
        return {
            "success": True,
            "site_id": site_id,
            "count": len(lists),
            "lists": [
                {
                    "id": lst.get("id"),
                    "name": lst.get("name"),
                    "display_name": lst.get("displayName"),
                    "description": lst.get("description"),
                    "web_url": lst.get("webUrl"),
                    "list_template": lst.get("list", {}).get("template"),
                    "hidden": lst.get("hidden", False),
                    "created_date_time": lst.get("createdDateTime"),
                }
                for lst in lists
            ]
        }
    
    def _get_list_items(self, params: dict) -> dict:
        """
        Get items from a SharePoint list.
        
        Args:
            params: Must contain:
                - access_token: Microsoft Graph access token
                - site_url: SharePoint site URL
                - list_id: List ID or title
                - max_results (optional): Max items (default 100, max 500)
                - filter (optional): OData filter query
                - select (optional): Comma-separated field names
        
        Returns:
            List items with fields
        """
        access_token = params["access_token"]
        site_url = params["site_url"]
        list_id = params["list_id"]
        max_results = min(params.get("max_results", 100), 500)
        odata_filter = params.get("filter")
        select_fields = params.get("select")
        
        # Get site ID
        site_result = self._get_site({
            "access_token": access_token,
            "microsoft_user": params.get("microsoft_user"),
            "site_url": site_url
        })
        
        if not site_result["success"]:
            return site_result
        
        site_id = site_result["site"]["id"]
        
        # Build query parameters
        query_params = [f"$expand=fields", f"$top={max_results}"]
        
        if odata_filter:
            query_params.append(f"$filter={odata_filter}")
        
        if select_fields:
            # Select specific fields: $select=fields(Title,Status,DueDate)
            query_params.append(f"$select=fields({select_fields})")
        
        query_string = "&".join(query_params)
        
        # GET /sites/{site-id}/lists/{list-id}/items
        response = GraphClient(access_token).get(
            endpoint=f"/sites/{site_id}/lists/{list_id}/items?{query_string}",
        )
        
        items = response.get("value", [])
        
        return {
            "success": True,
            "site_id": site_id,
            "list_id": list_id,
            "count": len(items),
            "items": [
                {
                    "id": item.get("id"),
                    "created_date_time": item.get("createdDateTime"),
                    "last_modified_date_time": item.get("lastModifiedDateTime"),
                    "fields": item.get("fields", {}),
                    "web_url": item.get("webUrl"),
                }
                for item in items
            ]
        }
    
    def _create_list_item(self, params: dict) -> dict:
        """
        Create a new item in a SharePoint list.
        
        Args:
            params: Must contain:
                - access_token: Microsoft Graph access token
                - site_url: SharePoint site URL
                - list_id: List ID or title
                - fields: Dictionary of field values
        
        Returns:
            Created item
        """
        access_token = params["access_token"]
        site_url = params["site_url"]
        list_id = params["list_id"]
        fields = params["fields"]
        
        if not isinstance(fields, dict):
            return {
                "success": False,
                "error": "fields must be a dictionary"
            }
        
        # Get site ID
        site_result = self._get_site({
            "access_token": access_token,
            "microsoft_user": params.get("microsoft_user"),
            "site_url": site_url
        })
        
        if not site_result["success"]:
            return site_result
        
        site_id = site_result["site"]["id"]
        
        # POST /sites/{site-id}/lists/{list-id}/items
        body = {"fields": fields}
        
        response = GraphClient(access_token).post(
            endpoint=f"/sites/{site_id}/lists/{list_id}/items",
            json_data=body
        )
        
        return {
            "success": True,
            "item": {
                "id": response.get("id"),
                "created_date_time": response.get("createdDateTime"),
                "fields": response.get("fields", {}),
                "web_url": response.get("webUrl"),
            }
        }
    
    def _update_list_item(self, params: dict) -> dict:
        """
        Update an existing SharePoint list item.
        
        Args:
            params: Must contain:
                - access_token: Microsoft Graph access token
                - site_url: SharePoint site URL
                - list_id: List ID or title
                - item_id: Item ID
                - fields: Dictionary of field values to update
        
        Returns:
            Updated item
        """
        access_token = params["access_token"]
        site_url = params["site_url"]
        list_id = params["list_id"]
        item_id = params["item_id"]
        fields = params["fields"]
        
        if not isinstance(fields, dict):
            return {
                "success": False,
                "error": "fields must be a dictionary"
            }
        
        # Get site ID
        site_result = self._get_site({
            "access_token": access_token,
            "microsoft_user": params.get("microsoft_user"),
            "site_url": site_url
        })
        
        if not site_result["success"]:
            return site_result
        
        site_id = site_result["site"]["id"]
        
        # PATCH /sites/{site-id}/lists/{list-id}/items/{item-id}/fields
        response = GraphClient(access_token).patch(
            endpoint=f"/sites/{site_id}/lists/{list_id}/items/{item_id}/fields",
            json_data=fields
        )
        
        return {
            "success": True,
            "item": {
                "id": item_id,
                "fields": response,
            }
        }
