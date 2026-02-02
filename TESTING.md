# MS365-SharePoint MCP Server - Testing Guide

**Purpose**: Test MS365-SharePoint MCP using Inspector CLI  
**Version**: 1.0.0  
**Last Updated**: 2026-02-02

---

## 🎯 Overview

Test the MS365-SharePoint MCP server using the official MCP Inspector CLI tool.

**Endpoint**: https://ms365-sharepoint.brainaihub.tech/mcp/sse  
**Transport**: SSE (Server-Sent Events)  
**Auth**: Bearer token (API key from .env)  
**Tools**: 6 SharePoint operations  
**Prompts**: 3 workflow templates

---

## 📋 Prerequisites

### 1. Node.js 22.x

```bash
# Check version
node --version  # Should be v22.x.x

# Install if needed (Ubuntu/Debian)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### 2. Get API Key

```bash
# SSH to server
ssh root@10.135.215.172

# Get API key
grep MCP_API_KEY /opt/ms365-sharepoint/.env
# Copy the value after '='
```

### 3. Get TrustyVault Session Token

You need a valid session token from TrustyVault (lasts 7 days):

```bash
# Use trustyvault_verify_otp tool to get session_token
# The session_token is a 36-character UUID like:
# 9595ee0f-9263-4646-ae19-cd5a7cbd6da8
```

---

## 🧪 Basic Testing

### Command Template

```bash
yes | npx @modelcontextprotocol/inspector@latest \
  --cli https://ms365-sharepoint.brainaihub.tech/mcp/sse \
  --transport sse \
  --header "Authorization: Bearer <API_KEY>" \
  --method <METHOD> \
  [--tool-name <TOOL>] \
  [--tool-arg key=value]
```

### Test 1: List Tools

```bash
yes | npx @modelcontextprotocol/inspector@latest \
  --cli https://ms365-sharepoint.brainaihub.tech/mcp/sse \
  --transport sse \
  --header "Authorization: Bearer ms365-sharepoint-prod-YOUR_KEY" \
  --method tools/list
```

**Expected Output**:
```json
{
  "tools": [
    {"name": "sharepoint_get_site", "description": "Get SharePoint site information..."},
    {"name": "sharepoint_list_sites", "description": "List accessible SharePoint sites..."},
    {"name": "sharepoint_list_lists", "description": "List all lists in a SharePoint site..."},
    {"name": "sharepoint_get_list_items", "description": "Get items from a SharePoint list..."},
    {"name": "sharepoint_create_list_item", "description": "Create a new item..."},
    {"name": "sharepoint_update_list_item", "description": "Update an existing item..."}
  ]
}
```

### Test 2: List Prompts

```bash
yes | npx @modelcontextprotocol/inspector@latest \
  --cli https://ms365-sharepoint.brainaihub.tech/mcp/sse \
  --transport sse \
  --header "Authorization: Bearer ms365-sharepoint-prod-YOUR_KEY" \
  --method prompts/list
```

**Expected Output**:
```json
{
  "prompts": [
    {"name": "get_site_info_workflow", "description": "Get comprehensive SharePoint site information"},
    {"name": "list_items_workflow", "description": "Browse SharePoint list items"},
    {"name": "create_item_workflow", "description": "Create item in SharePoint list"}
  ]
}
```

---

## 🛠️ Testing Tools (Read-Only)

### List Sites

```bash
yes | npx @modelcontextprotocol/inspector@latest \
  --cli https://ms365-sharepoint.brainaihub.tech/mcp/sse \
  --transport sse \
  --header "Authorization: Bearer ms365-sharepoint-prod-YOUR_KEY" \
  --method tools/call \
  --tool-name sharepoint_list_sites \
  --tool-arg session_token="YOUR_SESSION_TOKEN" \
  --tool-arg max_results=10
```

**Expected Success**:
```json
{
  "content": [{
    "type": "text",
    "text": "{\"success\":true,\"count\":3,\"sites\":[{\"id\":\"...\",\"name\":\"Engineering\",\"web_url\":\"https://contoso.sharepoint.com/sites/engineering\"}]}"
  }]
}
```

**Expected if no sites**:
```json
{
  "content": [{
    "type": "text",
    "text": "{\"success\":true,\"count\":0,\"sites\":[]}"
  }]
}
```

### Get Site Info

```bash
yes | npx @modelcontextprotocol/inspector@latest \
  --cli https://ms365-sharepoint.brainaihub.tech/mcp/sse \
  --transport sse \
  --header "Authorization: Bearer ms365-sharepoint-prod-YOUR_KEY" \
  --method tools/call \
  --tool-name sharepoint_get_site \
  --tool-arg session_token="YOUR_SESSION_TOKEN" \
  --tool-arg site_url="https://contoso.sharepoint.com/sites/engineering"
```

### List Lists in Site

```bash
yes | npx @modelcontextprotocol/inspector@latest \
  --cli https://ms365-sharepoint.brainaihub.tech/mcp/sse \
  --transport sse \
  --header "Authorization: Bearer ms365-sharepoint-prod-YOUR_KEY" \
  --method tools/call \
  --tool-name sharepoint_list_lists \
  --tool-arg session_token="YOUR_SESSION_TOKEN" \
  --tool-arg site_url="https://contoso.sharepoint.com/sites/engineering" \
  --tool-arg include_hidden=false
```

### Get List Items

```bash
yes | npx @modelcontextprotocol/inspector@latest \
  --cli https://ms365-sharepoint.brainaihub.tech/mcp/sse \
  --transport sse \
  --header "Authorization: Bearer ms365-sharepoint-prod-YOUR_KEY" \
  --method tools/call \
  --tool-name sharepoint_get_list_items \
  --tool-arg session_token="YOUR_SESSION_TOKEN" \
  --tool-arg site_url="https://contoso.sharepoint.com/sites/engineering" \
  --tool-arg list_id="Tasks" \
  --tool-arg max_results=10
```

---

## 📊 Complete Test Script

Save as `test-sharepoint.sh`:

```bash
#!/bin/bash

# Configuration
API_KEY="ms365-sharepoint-prod-YOUR_KEY"
SESSION_TOKEN="YOUR_SESSION_TOKEN"
ENDPOINT="https://ms365-sharepoint.brainaihub.tech/mcp/sse"

echo "=== MS365-SharePoint MCP Tests ==="
echo ""

# Test 1: Health check
echo "Test 1: Health Check"
curl -s https://ms365-sharepoint.brainaihub.tech/health | jq
echo ""

# Test 2: List tools
echo "Test 2: List Tools"
yes | npx @modelcontextprotocol/inspector@latest \
  --cli $ENDPOINT \
  --transport sse \
  --header "Authorization: Bearer $API_KEY" \
  --method tools/list | jq '.tools[] | {name, description}' | head -20
echo ""

# Test 3: List prompts
echo "Test 3: List Prompts"
yes | npx @modelcontextprotocol/inspector@latest \
  --cli $ENDPOINT \
  --transport sse \
  --header "Authorization: Bearer $API_KEY" \
  --method prompts/list | jq '.prompts[] | {name, description}'
echo ""

# Test 4: List sites
echo "Test 4: List Sites"
yes | npx @modelcontextprotocol/inspector@latest \
  --cli $ENDPOINT \
  --transport sse \
  --header "Authorization: Bearer $API_KEY" \
  --method tools/call \
  --tool-name sharepoint_list_sites \
  --tool-arg session_token="$SESSION_TOKEN" \
  --tool-arg max_results=5
echo ""

echo "=== Tests Complete ==="
```

**Usage**:
```bash
chmod +x test-sharepoint.sh
# Edit file to add your API_KEY and SESSION_TOKEN
./test-sharepoint.sh
```

---

## 🔍 Troubleshooting

### Issue: "Authorization failed"

**Cause**: Invalid or missing API key

**Solution**:
```bash
# Get correct API key
ssh root@10.135.215.172 "grep MCP_API_KEY /opt/ms365-sharepoint/.env"
```

### Issue: "session_expired" or "session_token invalid"

**Cause**: TrustyVault session token expired (7 days lifetime)

**Solution**:
Get new session token via `trustyvault_verify_otp`

### Issue: "provider_not_configured"

**Cause**: Microsoft 365 not configured in TrustyVault for this user

**Solution**:
1. User must add Microsoft 365 credentials in TrustyVault
2. Configure OAuth app with correct permissions
3. Grant admin consent if needed

### Issue: Empty sites list

**Cause**: User has no SharePoint sites OR no permissions

**Solution**:
1. Verify user has access to SharePoint sites
2. Check Azure AD permissions: Sites.Read.All, Sites.ReadWrite.All
3. Test with Graph API directly:
```bash
# Get token from TrustyVault
TOKEN=$(curl -s -X POST https://trustyvault.brainaihub.tech/api/v1/session/get-credentials \
  -H "Content-Type: application/json" \
  -d '{"session_token":"YOUR_TOKEN","provider":"microsoft_graph"}' | jq -r '.access_token')

# Test Graph API
curl -s "https://graph.microsoft.com/v1.0/sites?\$top=5" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Issue: Connection timeout

**Cause**: Service not accessible

**Solution**:
```bash
# Test internal health
ssh root@10.135.215.172 "docker exec ms365-sharepoint-app curl http://localhost:8046/health"

# Test external health
curl https://ms365-sharepoint.brainaihub.tech/health

# Check nginx
ssh root@10.135.215.172 "docker exec swissknife-nginx nginx -t"
```

---

## ✅ Expected Results Summary

| Test | Success Indicator |
|------|-------------------|
| tools/list | Returns 6 tools with schemas |
| prompts/list | Returns 3 prompts |
| sharepoint_list_sites | `{"success": true, "count": N, "sites": [...]}` |
| sharepoint_get_site | `{"success": true, "site": {...}}` |
| sharepoint_list_lists | `{"success": true, "count": N, "lists": [...]}` |
| sharepoint_get_list_items | `{"success": true, "count": N, "items": [...]}` |

**All successful responses include**: `"success": true`  
**All error responses include**: `"success": false, "error": "..."`

---

## 📚 Additional Resources

- **MCP Inspector**: https://github.com/modelcontextprotocol/inspector
- **SharePoint Graph API**: https://learn.microsoft.com/en-us/graph/api/resources/sharepoint
- **Service Repository**: https://github.com/ilvolodel/ms365-sharepoint
- **Deployment Guide**: See DEPLOYMENT.md

---

**Last Updated**: 2026-02-02  
**Status**: ✅ Production Ready
