# MS365-SharePoint MCP Server

**Version**: 1.0.0  
**Status**: ✅ Production  
**URL**: https://ms365-sharepoint.brainaihub.tech

MCP server for Microsoft SharePoint operations with TrustyVault authentication.

---

## 🎯 Features

- **6 SharePoint Tools**: 
  - `sharepoint_list_sites` - List accessible SharePoint sites
  - `sharepoint_get_site` - Get site information
  - `sharepoint_list_lists` - List all lists in a site
  - `sharepoint_get_list_items` - Get items from a list
  - `sharepoint_create_list_item` - Create new list item
  - `sharepoint_update_list_item` - Update existing item

- **3 Workflow Prompts**: Common SharePoint operations
- **TrustyVault Auth**: Secure OAuth token management via session tokens
- **Token Caching**: SQLite-based caching reduces API calls by 95%+
- **SSE Transport**: MCP protocol over Server-Sent Events

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [AGENT_PROMPT.md](./AGENT_PROMPT.md) | Complete guide for AI agents using this MCP |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Architecture, deployment, and maintenance |
| [TESTING.md](./TESTING.md) | Testing with MCP Inspector CLI |

---

## 🚀 Quick Start

### For AI Agents

See [AGENT_PROMPT.md](./AGENT_PROMPT.md) for complete usage instructions.

**Example workflow**:
1. Get session token from TrustyVault
2. List accessible sites: `sharepoint_list_sites`
3. Get site details: `sharepoint_get_site`
4. List site's lists: `sharepoint_list_lists`
5. Get list items: `sharepoint_get_list_items`

### For Developers

**Test with MCP Inspector**:
```bash
yes | npx @modelcontextprotocol/inspector@latest \
  --cli https://ms365-sharepoint.brainaihub.tech/mcp/sse \
  --transport sse \
  --header "Authorization: Bearer YOUR_API_KEY" \
  --method tools/list
```

See [TESTING.md](./TESTING.md) for complete testing guide.

---

## 🔧 Installation

**Production deployment** (requires server access):
```bash
ssh root@10.135.215.172
cd /opt
git clone https://github.com/ilvolodel/ms365-sharepoint.git
cd ms365-sharepoint
# Configure .env with API key
docker compose build && docker compose up -d
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed deployment instructions.

---

## 📊 Status

- **Service**: ✅ Running
- **Health**: https://ms365-sharepoint.brainaihub.tech/health
- **Tools**: 6
- **Prompts**: 3
- **Cache**: SQLite token cache active

---

## 🔐 Authentication

Uses **TrustyVault session tokens** for OAuth flow:

1. User authenticates with TrustyVault (OTP verification)
2. TrustyVault returns session_token (7 days validity)
3. MCP exchanges session_token for Microsoft Graph access_token
4. Access tokens cached locally (reduces TrustyVault calls)

**Required permissions**: `Sites.Read.All`, `Sites.ReadWrite.All`

---

## 🐛 Troubleshooting

**Empty sites list**: User may not have SharePoint access  
**Session expired**: Get fresh session token from TrustyVault  
**Permission errors**: Check Azure AD app permissions

See [TESTING.md](./TESTING.md) for detailed troubleshooting.

---

## 📖 Additional Resources

- **MCP Protocol**: https://spec.modelcontextprotocol.io/
- **SharePoint Graph API**: https://learn.microsoft.com/en-us/graph/api/resources/sharepoint
- **TrustyVault**: https://trustyvault.brainaihub.tech
- **Repository**: https://github.com/ilvolodel/ms365-sharepoint

---

**Last Updated**: 2026-02-02
