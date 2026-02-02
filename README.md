# MS365-SharePoint MCP Server

Microsoft SharePoint operations MCP server for AI agents.

## Features

- 6 SharePoint tools (sites, lists, items operations)
- TrustyVault OAuth integration
- Token caching (SQLite)
- FastMCP + FastAPI

## Quick Start

```bash
# Setup
cp .env.example .env
# Edit .env and add MCP_API_KEY

# Run with Docker
docker compose up -d

# Health check
curl http://localhost:8046/health
```

## For AI Agents

**See [AGENT_PROMPT.md](AGENT_PROMPT.md)** for complete usage instructions.

## Tools

1. `sharepoint_list_sites` - List accessible SharePoint sites
2. `sharepoint_get_site` - Get site information
3. `sharepoint_list_lists` - List lists in a site
4. `sharepoint_get_list_items` - Get items from a list
5. `sharepoint_create_list_item` - Create new item
6. `sharepoint_update_list_item` - Update existing item

## Authentication

- **MCP Server**: Requires `MCP_API_KEY` (Bearer token)
- **Tools**: Require `session_token` from TrustyVault

## Stack

- Python 3.12
- FastMCP (MCP protocol)
- Microsoft Graph API
- SQLite (token cache)

## Version

1.0.0
