#!/bin/bash

# MS365-SharePoint MCP - Automated Deployment Script
# Deploys SharePoint MCP service with certbot + proxy-nginx + app

set -e  # Exit on error

echo "========================================"
echo "MS365-SharePoint MCP - Deployment"
echo "========================================"
echo ""

# Configuration
DROPLET_IP="10.135.215.172"
DROPLET_PASS="Fr3qu3nc1."
SERVICE_NAME="ms365-sharepoint"
DOMAIN="ms365-sharepoint.brainaihub.tech"
PORT="8046"
CONTAINER_NAME="ms365-sharepoint-app"

echo "📋 Configuration:"
echo "  - Domain: $DOMAIN"
echo "  - Port: $PORT"
echo "  - Container: $CONTAINER_NAME"
echo ""

# Step 1: Verify DNS
echo "🔍 Step 1: Verifying DNS..."
DNS_IP=$(curl -s "https://dns.google/resolve?name=$DOMAIN&type=A" | grep -o '"data":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ "$DNS_IP" == "161.35.214.46" ]; then
    echo "✅ DNS OK: $DOMAIN → $DNS_IP"
else
    echo "❌ DNS Error: Expected 161.35.214.46, got $DNS_IP"
    echo "   Please create DNS A record first!"
    exit 1
fi
echo ""

# Step 2: Check port availability
echo "🔍 Step 2: Checking port $PORT availability..."
sshpass -p "$DROPLET_PASS" ssh -o StrictHostKeyChecking=no root@$DROPLET_IP "netstat -tulpn | grep :$PORT" && {
    echo "❌ Port $PORT is already in use!"
    exit 1
} || {
    echo "✅ Port $PORT is available"
}
echo ""

# Step 3: Update swissknife .env
echo "📝 Step 3: Updating swissknife .env..."
sshpass -p "$DROPLET_PASS" ssh -o StrictHostKeyChecking=no root@$DROPLET_IP << 'ENDSSH'
cd /opt/swissknife
cp .env .env.backup-$(date +%Y%m%d-%H%M%S)
if ! grep -q "SHAREPOINT_MCP_DOMAIN" .env; then
    echo "SHAREPOINT_MCP_DOMAIN=ms365-sharepoint.brainaihub.tech" >> .env
    echo "✅ Added SHAREPOINT_MCP_DOMAIN to .env"
else
    echo "✅ SHAREPOINT_MCP_DOMAIN already in .env"
fi
ENDSSH
echo ""

# Step 4: Update certbot script (if not already updated)
echo "📝 Step 4: Checking certbot script..."
sshpass -p "$DROPLET_PASS" ssh -o StrictHostKeyChecking=no root@$DROPLET_IP << 'ENDSSH'
cd /opt/swissknife/scripts
if ! grep -q "SHAREPOINT_MCP_DOMAIN" certbot-entrypoint.sh; then
    echo "⚠️  Certbot script needs manual update!"
    echo "   Please add SharePoint certificate block to certbot-entrypoint.sh"
    echo "   See MICROAGENT.md for the block to add"
    exit 1
else
    echo "✅ Certbot script already includes SharePoint"
fi
ENDSSH
echo ""

# Step 5: Add HTTP block to proxy-nginx (if not exists)
echo "📝 Step 5: Adding HTTP block to proxy-nginx..."
sshpass -p "$DROPLET_PASS" ssh -o StrictHostKeyChecking=no root@$DROPLET_IP << 'ENDSSH'
cd /opt/swissknife/nginx-swissknife/conf.d

# Check if already configured
if grep -q "ms365-sharepoint.brainaihub.tech" default.conf; then
    echo "✅ Nginx already configured for ms365-sharepoint"
    exit 0
fi

# Backup
cp default.conf default.conf.backup-$(date +%Y%m%d-%H%M%S)

# Add HTTP block (ACME challenge only, before last closing brace)
cat >> default.conf << 'NGINX_BLOCK'

# MS365-SharePoint - HTTP (ACME challenge)
server {
    listen 80;
    server_name ms365-sharepoint.brainaihub.tech;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}
NGINX_BLOCK

echo "✅ HTTP block added to nginx config"
ENDSSH
echo ""

# Step 6: Test and reload nginx
echo "🔧 Step 6: Testing and reloading nginx..."
sshpass -p "$DROPLET_PASS" ssh -o StrictHostKeyChecking=no root@$DROPLET_IP << 'ENDSSH'
if docker exec swissknife-nginx nginx -t 2>&1 | grep -q "successful"; then
    docker exec swissknife-nginx nginx -s reload
    echo "✅ Nginx reloaded successfully"
else
    echo "❌ Nginx config test failed!"
    docker exec swissknife-nginx nginx -t
    exit 1
fi
ENDSSH
echo ""

# Step 7: Rebuild certbot (gets certificate)
echo "🔐 Step 7: Rebuilding certbot to get certificate..."
sshpass -p "$DROPLET_PASS" ssh -o StrictHostKeyChecking=no root@$DROPLET_IP << 'ENDSSH'
cd /opt/swissknife
docker compose up -d --force-recreate certbot
echo "✅ Certbot container rebuilt"
ENDSSH
echo ""

# Step 8: Wait for certificate
echo "⏳ Step 8: Waiting for certificate (30 seconds)..."
sleep 30

sshpass -p "$DROPLET_PASS" ssh -o StrictHostKeyChecking=no root@$DROPLET_IP << 'ENDSSH'
if [ -f "/opt/swissknife/data/letsencrypt/live/ms365-sharepoint.brainaihub.tech/fullchain.pem" ]; then
    echo "✅ Certificate obtained successfully"
else
    echo "❌ Certificate not found!"
    echo "   Check certbot logs: docker logs swissknife-certbot"
    exit 1
fi
ENDSSH
echo ""

# Step 9: Add HTTPS block to proxy-nginx
echo "📝 Step 9: Adding HTTPS block to proxy-nginx..."
sshpass -p "$DROPLET_PASS" ssh -o StrictHostKeyChecking=no root@$DROPLET_IP << 'ENDSSH'
cd /opt/swissknife/nginx-swissknife/conf.d

# Check if HTTPS block already exists
if grep -q "ms365-sharepoint-app:8046" default.conf; then
    echo "✅ HTTPS block already configured"
    exit 0
fi

# Add HTTPS block
cat >> default.conf << 'NGINX_HTTPS'

# MS365-SharePoint - HTTPS
server {
    listen 443 ssl http2;
    server_name ms365-sharepoint.brainaihub.tech;

    ssl_certificate /etc/letsencrypt/live/ms365-sharepoint.brainaihub.tech/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ms365-sharepoint.brainaihub.tech/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    location / {
        proxy_pass http://ms365-sharepoint-app:8046;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
        
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type' always;
        
        if ($request_method = OPTIONS) {
            return 204;
        }
    }
}
NGINX_HTTPS

echo "✅ HTTPS block added"
ENDSSH
echo ""

# Step 10: Test and reload nginx again
echo "🔧 Step 10: Testing and reloading nginx (final)..."
sshpass -p "$DROPLET_PASS" ssh -o StrictHostKeyChecking=no root@$DROPLET_IP << 'ENDSSH'
if docker exec swissknife-nginx nginx -t 2>&1 | grep -q "successful"; then
    docker exec swissknife-nginx nginx -s reload
    echo "✅ Nginx reloaded with HTTPS config"
else
    echo "❌ Nginx config test failed!"
    docker exec swissknife-nginx nginx -t
    exit 1
fi
ENDSSH
echo ""

# Step 11: Deploy app
echo "🚀 Step 11: Deploying application..."
sshpass -p "$DROPLET_PASS" ssh -o StrictHostKeyChecking=no root@$DROPLET_IP << 'ENDSSH'
# Clone or pull
if [ -d "/opt/ms365-sharepoint" ]; then
    cd /opt/ms365-sharepoint
    git pull origin main
    echo "✅ Repository updated"
else
    cd /opt
    git clone https://github.com/ilvolodel/ms365-sharepoint.git
    cd ms365-sharepoint
    echo "✅ Repository cloned"
fi

# Create .env if missing
if [ ! -f ".env" ]; then
    cp .env.example .env
    API_KEY="ms365-sharepoint-prod-$(openssl rand -hex 24)"
    sed -i "s/YOUR_GENERATED_KEY_HERE/$API_KEY/" .env
    echo "✅ Generated API key"
    echo "   API_KEY: $API_KEY"
    echo "   (saved to .env)"
fi

# Create directories
mkdir -p data logs

# Build and start
docker compose build
docker compose up -d

echo "✅ Application deployed"
ENDSSH
echo ""

# Step 12: Health check
echo "🏥 Step 12: Health check..."
sleep 10

HEALTH=$(sshpass -p "$DROPLET_PASS" ssh -o StrictHostKeyChecking=no root@$DROPLET_IP "curl -s http://localhost:8046/health")
if echo "$HEALTH" | grep -q "healthy"; then
    echo "✅ Health check passed!"
    echo "   Response: $HEALTH"
else
    echo "❌ Health check failed!"
    echo "   Response: $HEALTH"
    echo "   Check logs: docker logs ms365-sharepoint-app"
    exit 1
fi
echo ""

# Step 13: External verification
echo "🌍 Step 13: External HTTPS verification..."
sleep 5
HTTPS_HEALTH=$(curl -s https://ms365-sharepoint.brainaihub.tech/health 2>&1)
if echo "$HTTPS_HEALTH" | grep -q "healthy"; then
    echo "✅ HTTPS endpoint working!"
    echo "   $HTTPS_HEALTH"
else
    echo "⚠️  HTTPS endpoint not responding yet"
    echo "   This may take a few more seconds..."
    echo "   Try: curl https://ms365-sharepoint.brainaihub.tech/health"
fi
echo ""

echo "========================================"
echo "✅ Deployment Complete!"
echo "========================================"
echo ""
echo "📋 Service Information:"
echo "  - URL: https://ms365-sharepoint.brainaihub.tech"
echo "  - Health: https://ms365-sharepoint.brainaihub.tech/health"
echo "  - MCP: https://ms365-sharepoint.brainaihub.tech/mcp/sse"
echo "  - Container: $CONTAINER_NAME"
echo "  - Port: $PORT (internal)"
echo ""
echo "🔑 Next Steps:"
echo "  1. Get API key: ssh root@$DROPLET_IP 'cat /opt/ms365-sharepoint/.env | grep MCP_API_KEY'"
echo "  2. Update TrustyVault permissions (see MICROAGENT.md)"
echo "  3. Azure AD: Add Sites.Read.All + Sites.ReadWrite.All"
echo "  4. Test with MCP Inspector"
echo ""
echo "📚 Documentation:"
echo "  - MICROAGENT.md: Complete deployment guide"
echo "  - AGENT_PROMPT.md: AI agent usage guide"
echo "  - README.md: Technical documentation"
echo ""
