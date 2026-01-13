# MS365-SharePoint MCP Server - Inspector Testing Guide

**Purpose**: Test MS365-SharePoint MCP tools using MCP Inspector CLI  
**Version**: 1.0.0  
**Last Updated**: 2026-01-13

---

## 🎯 OVERVIEW

This guide shows how to test the MS365-SharePoint MCP server using the official MCP Inspector tool.

**What is MCP Inspector?**
- Official testing tool for MCP servers
- CLI-based interactive testing
- Supports SSE transport (Server-Sent Events)
- Requires Node.js 22.x or higher

**Service Details**:
- **Endpoint**: https://ms365-sharepoint.brainaihub.tech/mcp/sse
- **Transport**: SSE (Server-Sent Events)
- **Auth**: Bearer token (API key from .env)
- **Tools**: 6 SharePoint operations
- **Prompts**: 3 workflow templates

---

## 📋 PREREQUISITES

### 1. Node.js 22.x Installation

**Check current version**:
```bash
node --version
# If < v22, upgrade:
```

**Install Node.js 22.x** (Ubuntu/Debian):
```bash
# Remove old Node.js
sudo apt-get remove nodejs -y

# Install Node.js 22.x
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify
node --version
# Expected: v22.x.x
npm --version
# Expected: v10.x.x
```

### 2. Get API Key

```bash
# SSH to droplet
ssh root@10.135.215.172

# Get API key
grep MCP_API_KEY /opt/ms365-sharepoint/.env
# Output: MCP_API_KEY=ms365-sharepoint-prod-[GENERATED_KEY]

# Copy the key (everything after =)
```

### 3. Get TrustyVault Session Token

**You need a valid session token from TrustyVault**:

```bash
# Use trustyvault_verify_otp tool to get session_token
# Example (via another MCP client or direct API):
curl -X POST https://trustyvault.brainaihub.tech/api/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com",
    "otp_code": "123456"
  }'

# Response contains session_token (36-char UUID)
# Example: de1d1682-f81a-47f1-ab8c-21be0a0416af
```

---

## 🧪 TESTING WITH MCP INSPECTOR

### Basic Usage Pattern

```bash
npx @modelcontextprotocol/inspector@latest --cli \
  https://ms365-sharepoint.brainaihub.tech/mcp/sse \
  --transport sse \
  --header "Authorization: Bearer [YOUR_API_KEY]" \
  --method [METHOD]
```

### Test 1: List Available Tools

```bash
npx @modelcontextprotocol/inspector@latest --cli \
  https://ms365-sharepoint.brainaihub.tech/mcp/sse \
  --transport sse \
  --header "Authorization: Bearer ms365-sharepoint-prod-[YOUR_KEY]" \
  --method tools/list
```

**Expected Output**:
```json
{
  "tools": [
    {
      "name": "sharepoint_get_site",
      "description": "Get SharePoint site information. Provide either site_url OR site_id.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "session_token": {
            "type": "string",
            "description": "TrustyVault session token (from trustyvault_verify_otp)"
          },
          "site_url": {
            "type": "string",
            "description": "SharePoint site URL (e.g., https://contoso.sharepoint.com/sites/engineering)"
          },
          "site_id": {
            "type": "string",
            "description": "Site ID (alternative to site_url)"
          }
        },
        "required": ["session_token"]
      }
    },
    {
      "name": "sharepoint_list_sites",
      "description": "List accessible SharePoint sites. Optional search query.",
      "inputSchema": { ... }
    },
    {
      "name": "sharepoint_list_lists",
      "description": "List all lists in a SharePoint site.",
      "inputSchema": { ... }
    },
    {
      "name": "sharepoint_get_list_items",
      "description": "Get items from a SharePoint list. Supports filtering and field selection.",
      "inputSchema": { ... }
    },
    {
      "name": "sharepoint_create_list_item",
      "description": "Create a new item in a SharePoint list.",
      "inputSchema": { ... }
    },
    {
      "name": "sharepoint_update_list_item",
      "description": "Update an existing SharePoint list item.",
      "inputSchema": { ... }
    }
  ]
}
```

### Test 2: List Available Prompts

```bash
npx @modelcontextprotocol/inspector@latest --cli \
  https://ms365-sharepoint.brainaihub.tech/mcp/sse \
  --transport sse \
  --header "Authorization: Bearer ms365-sharepoint-prod-[YOUR_KEY]" \
  --method prompts/list
```

**Expected Output**:
```json
{
  "prompts": [
    {
      "name": "get_site_info_workflow",
      "description": "Get comprehensive SharePoint site information",
      "arguments": [
        {
          "name": "site_url",
          "description": "SharePoint site URL",
          "required": true
        }
      ]
    },
    {
      "name": "list_items_workflow",
      "description": "Browse SharePoint list items",
      "arguments": [ ... ]
    },
    {
      "name": "create_item_workflow",
      "description": "Create item in SharePoint list",
      "arguments": [ ... ]
    }
  ]
}
```

### Test 3: List Accessible Sites

**Command**:
```bash
npx @modelcontextprotocol/inspector@latest --cli \
  https://ms365-sharepoint.brainaihub.tech/mcp/sse \
  --transport sse \
  --header "Authorization: Bearer ms365-sharepoint-prod-[YOUR_KEY]" \
  --method tools/call \
  --params '{
    "name": "sharepoint_list_sites",
    "arguments": {
      "session_token": "YOUR_SESSION_TOKEN",
      "max_results": 10
    }
  }'
```

**Expected Success Response**:
```json
{
  "content": [
    {
      "type": "text",
      "text": "{\"success\": true, \"count\": 3, \"sites\": [{\"id\": \"...\", \"name\": \"Engineering\", \"web_url\": \"https://contoso.sharepoint.com/sites/engineering\", ...}, ...]}"
    }
  ]
}
```

**Expected Error (no permissions)**:
```json
{
  "content": [
    {
      "type": "text",
      "text": "{\"success\": false, \"error\": \"Insufficient privileges to complete the operation.\"}"
    }
  ]
}
```

### Test 4: Get Site Information

**Command**:
```bash
npx @modelcontextprotocol/inspector@latest --cli \
  https://ms365-sharepoint.brainaihub.tech/mcp/sse \
  --transport sse \
  --header "Authorization: Bearer ms365-sharepoint-prod-[YOUR_KEY]" \
  --method tools/call \
  --params '{
    "name": "sharepoint_get_site",
    "arguments": {
      "session_token": "YOUR_SESSION_TOKEN",
      "site_url": "https://contoso.sharepoint.com/sites/engineering"
    }
  }'
```

**Expected Response**:
```json
{
  "content": [
    {
      "type": "text",
      "text": "{\"success\": true, \"site\": {\"id\": \"contoso.sharepoint.com,...\", \"name\": \"Engineering\", \"description\": \"Engineering team site\", \"web_url\": \"https://contoso.sharepoint.com/sites/engineering\", \"created_date_time\": \"2024-01-15T10:30:00Z\", \"last_modified_date_time\": \"2026-01-10T14:20:00Z\"}}"
    }
  ]
}
```

### Test 5: List Lists in Site

**Command**:
```bash
npx @modelcontextprotocol/inspector@latest --cli \
  https://ms365-sharepoint.brainaihub.tech/mcp/sse \
  --transport sse \
  --header "Authorization: Bearer ms365-sharepoint-prod-[YOUR_KEY]" \
  --method tools/call \
  --params '{
    "name": "sharepoint_list_lists",
    "arguments": {
      "session_token": "YOUR_SESSION_TOKEN",
      "site_url": "https://contoso.sharepoint.com/sites/engineering",
      "include_hidden": false
    }
  }'
```

**Expected Response**:
```json
{
  "content": [
    {
      "type": "text",
      "text": "{\"success\": true, \"site_id\": \"...\", \"count\": 5, \"lists\": [{\"id\": \"...\", \"name\": \"Documents\", \"display_name\": \"Shared Documents\", \"web_url\": \"https://contoso.sharepoint.com/sites/engineering/Shared%20Documents\", \"list_template\": \"documentLibrary\", \"hidden\": false}, ...]}"
    }
  ]
}
```

### Test 6: Get List Items

**Command**:
```bash
npx @modelcontextprotocol/inspector@latest --cli \
  https://ms365-sharepoint.brainaihub.tech/mcp/sse \
  --transport sse \
  --header "Authorization: Bearer ms365-sharepoint-prod-[YOUR_KEY]" \
  --method tools/call \
  --params '{
    "name": "sharepoint_get_list_items",
    "arguments": {
      "session_token": "YOUR_SESSION_TOKEN",
      "site_url": "https://contoso.sharepoint.com/sites/engineering",
      "list_id": "Tasks",
      "max_results": 10
    }
  }'
```

**Expected Response**:
```json
{
  "content": [
    {
      "type": "text",
      "text": "{\"success\": true, \"site_id\": \"...\", \"list_id\": \"Tasks\", \"count\": 5, \"items\": [{\"id\": \"1\", \"fields\": {\"Title\": \"Design new feature\", \"Status\": \"In Progress\", \"AssignedTo\": \"user@contoso.com\", \"DueDate\": \"2026-01-20\"}, \"web_url\": \"...\", \"created_date_time\": \"...\", \"last_modified_date_time\": \"...\"}, ...]}"
    }
  ]
}
```

### Test 7: Create List Item

**Command**:
```bash
npx @modelcontextprotocol/inspector@latest --cli \
  https://ms365-sharepoint.brainaihub.tech/mcp/sse \
  --transport sse \
  --header "Authorization: Bearer ms365-sharepoint-prod-[YOUR_KEY]" \
  --method tools/call \
  --params '{
    "name": "sharepoint_create_list_item",
    "arguments": {
      "session_token": "YOUR_SESSION_TOKEN",
      "site_url": "https://contoso.sharepoint.com/sites/engineering",
      "list_id": "Tasks",
      "fields": {
        "Title": "Test task created via MCP",
        "Status": "Not Started",
        "Priority": "Normal"
      }
    }
  }'
```

**Expected Response**:
```json
{
  "content": [
    {
      "type": "text",
      "text": "{\"success\": true, \"item\": {\"id\": \"42\", \"fields\": {\"Title\": \"Test task created via MCP\", \"Status\": \"Not Started\", \"Priority\": \"Normal\"}, \"web_url\": \"https://contoso.sharepoint.com/sites/engineering/Lists/Tasks/42_.000\", \"created_date_time\": \"2026-01-13T18:30:00Z\"}}"
    }
  ]
}
```

### Test 8: Update List Item

**Command**:
```bash
npx @modelcontextprotocol/inspector@latest --cli \
  https://ms365-sharepoint.brainaihub.tech/mcp/sse \
  --transport sse \
  --header "Authorization: Bearer ms365-sharepoint-prod-[YOUR_KEY]" \
  --method tools/call \
  --params '{
    "name": "sharepoint_update_list_item",
    "arguments": {
      "session_token": "YOUR_SESSION_TOKEN",
      "site_url": "https://contoso.sharepoint.com/sites/engineering",
      "list_id": "Tasks",
      "item_id": "42",
      "fields": {
        "Status": "Completed"
      }
    }
  }'
```

**Expected Response**:
```json
{
  "content": [
    {
      "type": "text",
      "text": "{\"success\": true, \"item\": {\"id\": \"42\", \"fields\": {\"Status\": \"Completed\", \"Modified\": \"2026-01-13T18:35:00Z\"}}}"
    }
  ]
}
```

### Test 9: Test Workflow Prompt

**Command**:
```bash
npx @modelcontextprotocol/inspector@latest --cli \
  https://ms365-sharepoint.brainaihub.tech/mcp/sse \
  --transport sse \
  --header "Authorization: Bearer ms365-sharepoint-prod-[YOUR_KEY]" \
  --method prompts/get \
  --params '{
    "name": "get_site_info_workflow",
    "arguments": {
      "site_url": "https://contoso.sharepoint.com/sites/engineering"
    }
  }'
```

**Expected Response**:
```json
{
  "messages": [
    {
      "role": "user",
      "content": {
        "type": "text",
        "text": "Get information about SharePoint site: https://contoso.sharepoint.com/sites/engineering\n\nUse sharepoint_get_site tool with session_token and site_url.\nThen use sharepoint_list_lists to show available lists in the site."
      }
    }
  ]
}
```

---

## 🔍 TROUBLESHOOTING

### Issue: "Authorization failed"

**Cause**: Invalid or missing API key

**Solution**:
```bash
# Get correct API key
ssh root@10.135.215.172 "grep MCP_API_KEY /opt/ms365-sharepoint/.env"

# Use full key in --header parameter
--header "Authorization: Bearer ms365-sharepoint-prod-[EXACT_KEY]"
```

### Issue: "session_expired" or "session_token invalid"

**Cause**: TrustyVault session token expired (30 min lifetime)

**Solution**:
```bash
# Get new session token via trustyvault_verify_otp
# Or use a recent token (< 30 minutes old)
```

### Issue: "provider_not_configured"

**Cause**: Microsoft 365 not configured in TrustyVault for this user

**Solution**:
1. User must add Microsoft 365 credentials in TrustyVault dashboard
2. Configure OAuth app with client ID and tenant ID
3. Grant permissions

### Issue: "Insufficient privileges"

**Cause**: Missing SharePoint permissions in Azure AD

**Solution**:
1. Update TrustyVault `microsoft.py` with:
   - `Sites.Read.All`
   - `Sites.ReadWrite.All`
2. User/admin must grant consent in Azure AD
3. Wait a few minutes for permissions to propagate

### Issue: "host not found in upstream"

**Cause**: App container not running

**Solution**:
```bash
ssh root@10.135.215.172
docker ps | grep ms365-sharepoint
# If not running:
cd /opt/ms365-sharepoint
docker compose up -d
```

### Issue: Connection timeout

**Cause**: Service not accessible or nginx misconfigured

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

## 📊 COMPLETE TEST SCRIPT

Save this as `test-sharepoint-mcp.sh`:

```bash
#!/bin/bash

# Configuration
API_KEY="ms365-sharepoint-prod-YOUR_KEY_HERE"
SESSION_TOKEN="YOUR_SESSION_TOKEN_HERE"
SITE_URL="https://contoso.sharepoint.com/sites/engineering"
ENDPOINT="https://ms365-sharepoint.brainaihub.tech/mcp/sse"

echo "=== MS365-SharePoint MCP Inspector Tests ==="
echo ""

# Test 1: List tools
echo "Test 1: List Tools"
npx @modelcontextprotocol/inspector@latest --cli $ENDPOINT \
  --transport sse \
  --header "Authorization: Bearer $API_KEY" \
  --method tools/list | jq '.tools[] | {name, description}'
echo ""

# Test 2: List prompts
echo "Test 2: List Prompts"
npx @modelcontextprotocol/inspector@latest --cli $ENDPOINT \
  --transport sse \
  --header "Authorization: Bearer $API_KEY" \
  --method prompts/list | jq '.prompts[] | {name, description}'
echo ""

# Test 3: List sites
echo "Test 3: List Sites"
npx @modelcontextprotocol/inspector@latest --cli $ENDPOINT \
  --transport sse \
  --header "Authorization: Bearer $API_KEY" \
  --method tools/call \
  --params "{\"name\":\"sharepoint_list_sites\",\"arguments\":{\"session_token\":\"$SESSION_TOKEN\",\"max_results\":5}}" \
  | jq '.content[0].text | fromjson'
echo ""

# Test 4: Get site info
echo "Test 4: Get Site Info"
npx @modelcontextprotocol/inspector@latest --cli $ENDPOINT \
  --transport sse \
  --header "Authorization: Bearer $API_KEY" \
  --method tools/call \
  --params "{\"name\":\"sharepoint_get_site\",\"arguments\":{\"session_token\":\"$SESSION_TOKEN\",\"site_url\":\"$SITE_URL\"}}" \
  | jq '.content[0].text | fromjson'
echo ""

# Test 5: List lists
echo "Test 5: List Lists in Site"
npx @modelcontextprotocol/inspector@latest --cli $ENDPOINT \
  --transport sse \
  --header "Authorization: Bearer $API_KEY" \
  --method tools/call \
  --params "{\"name\":\"sharepoint_list_lists\",\"arguments\":{\"session_token\":\"$SESSION_TOKEN\",\"site_url\":\"$SITE_URL\"}}" \
  | jq '.content[0].text | fromjson'
echo ""

echo "=== Tests Complete ==="
```

**Usage**:
```bash
chmod +x test-sharepoint-mcp.sh
# Edit file to add your API_KEY, SESSION_TOKEN, SITE_URL
./test-sharepoint-mcp.sh
```

---

## 🎯 EXPECTED RESULTS SUMMARY

| Test | Success Indicator |
|------|-------------------|
| tools/list | Returns 6 tools with schemas |
| prompts/list | Returns 3 prompts with arguments |
| sharepoint_list_sites | `{"success": true, "count": N, "sites": [...]}` |
| sharepoint_get_site | `{"success": true, "site": {...}}` |
| sharepoint_list_lists | `{"success": true, "count": N, "lists": [...]}` |
| sharepoint_get_list_items | `{"success": true, "count": N, "items": [...]}` |
| sharepoint_create_list_item | `{"success": true, "item": {"id": "..."}}` |
| sharepoint_update_list_item | `{"success": true, "item": {"id": "..."}}` |

**All successful responses include**: `"success": true`
**All error responses include**: `"success": false, "error": "..."`

---

## 📚 ADDITIONAL RESOURCES

- **MCP Inspector Docs**: https://modelcontextprotocol.io/docs/tools/inspector
- **SharePoint Graph API**: https://learn.microsoft.com/en-us/graph/api/resources/sharepoint
- **Service Repository**: https://github.com/ilvolodel/ms365-sharepoint
- **Deployment Guide**: See `deployment-architecture.md`

---

**Last Updated**: 2026-01-13  
**Author**: OpenHands AI Agent
