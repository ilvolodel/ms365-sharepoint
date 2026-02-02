#!/bin/bash

# MS365-SharePoint MCP Inspector Test Script
# Usage: ./test-mcp-inspector.sh <session_token>

# Configuration
ENDPOINT="https://ms365-sharepoint.brainaihub.tech/mcp/sse"
API_KEY="ms365-sharepoint-prod-ms365-sharepoint-prod-ac5a8af23a7e98b06ea9ed4358198f434efd7057bc72b327"

# Check if session_token provided
if [ -z "$1" ]; then
    echo "❌ Error: Session token required"
    echo "Usage: $0 <session_token>"
    exit 1
fi

SESSION_TOKEN="$1"

echo "=========================================="
echo "MS365-SharePoint MCP Inspector Tests"
echo "=========================================="
echo ""
echo "Endpoint: $ENDPOINT"
echo "Session Token: ${SESSION_TOKEN:0:20}..."
echo ""

# Test 1: List Tools
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 1: List Available Tools"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
npx @modelcontextprotocol/inspector@latest --cli \
  "$ENDPOINT" \
  --transport sse \
  --header "Authorization: Bearer $API_KEY" \
  --method tools/list 2>/dev/null | jq -r '.tools[] | "✓ \(.name) - \(.description)"'
echo ""

# Test 2: List Prompts
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 2: List Available Prompts"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
npx @modelcontextprotocol/inspector@latest --cli \
  "$ENDPOINT" \
  --transport sse \
  --header "Authorization: Bearer $API_KEY" \
  --method prompts/list 2>/dev/null | jq -r '.prompts[] | "✓ \(.name) - \(.description)"'
echo ""

# Test 3: List Sites
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 3: List SharePoint Sites"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
RESULT=$(npx @modelcontextprotocol/inspector@latest --cli \
  "$ENDPOINT" \
  --transport sse \
  --header "Authorization: Bearer $API_KEY" \
  --method tools/call \
  --params "{\"name\":\"sharepoint_list_sites\",\"arguments\":{\"session_token\":\"$SESSION_TOKEN\",\"max_results\":10}}" 2>/dev/null)

echo "$RESULT" | jq -r '.content[0].text' | jq .

# Save site URL for next tests if available
SITE_URL=$(echo "$RESULT" | jq -r '.content[0].text' | jq -r '.sites[0].web_url // empty')

if [ -n "$SITE_URL" ]; then
    echo ""
    echo "✓ Found site: $SITE_URL"
    echo ""
    
    # Test 4: Get Site Info
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Test 4: Get Site Information"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    npx @modelcontextprotocol/inspector@latest --cli \
      "$ENDPOINT" \
      --transport sse \
      --header "Authorization: Bearer $API_KEY" \
      --method tools/call \
      --params "{\"name\":\"sharepoint_get_site\",\"arguments\":{\"session_token\":\"$SESSION_TOKEN\",\"site_url\":\"$SITE_URL\"}}" 2>/dev/null | jq -r '.content[0].text' | jq .
    echo ""
    
    # Test 5: List Lists in Site
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Test 5: List Lists in Site"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    LISTS_RESULT=$(npx @modelcontextprotocol/inspector@latest --cli \
      "$ENDPOINT" \
      --transport sse \
      --header "Authorization: Bearer $API_KEY" \
      --method tools/call \
      --params "{\"name\":\"sharepoint_list_lists\",\"arguments\":{\"session_token\":\"$SESSION_TOKEN\",\"site_url\":\"$SITE_URL\"}}" 2>/dev/null)
    
    echo "$LISTS_RESULT" | jq -r '.content[0].text' | jq .
    
    # Get first list ID
    LIST_ID=$(echo "$LISTS_RESULT" | jq -r '.content[0].text' | jq -r '.lists[0].id // empty')
    
    if [ -n "$LIST_ID" ]; then
        echo ""
        echo "✓ Found list: $LIST_ID"
        echo ""
        
        # Test 6: Get List Items
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Test 6: Get List Items"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        npx @modelcontextprotocol/inspector@latest --cli \
          "$ENDPOINT" \
          --transport sse \
          --header "Authorization: Bearer $API_KEY" \
          --method tools/call \
          --params "{\"name\":\"sharepoint_get_list_items\",\"arguments\":{\"session_token\":\"$SESSION_TOKEN\",\"site_url\":\"$SITE_URL\",\"list_id\":\"$LIST_ID\",\"max_results\":5}}" 2>/dev/null | jq -r '.content[0].text' | jq .
    fi
else
    echo "⚠️  No sites found or error occurred"
fi

echo ""
echo "=========================================="
echo "Tests Complete"
echo "=========================================="
