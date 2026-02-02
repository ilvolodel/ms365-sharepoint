#!/bin/bash
set -e

echo "🚀 Deploying MS365-SharePoint MCP Server..."

# Navigate to ms365-sharepoint directory
cd "$(dirname "$0")"

# Pull latest code
echo "📥 Pulling latest code from Git..."
git pull origin main

# Build Docker image
echo "🏗️ Building Docker image..."
docker compose build --no-cache

# Restart container
echo "🔄 Restarting container..."
docker compose up -d

# Wait for health check
echo "⏳ Waiting for health check..."
sleep 5

# Check container status
if docker ps | grep -q ms365-sharepoint-app; then
    echo "✅ MS365-SharePoint MCP deployed successfully!"
    docker logs ms365-sharepoint-app --tail 20
else
    echo "❌ Deployment failed!"
    docker logs ms365-sharepoint-app --tail 50
    exit 1
fi
