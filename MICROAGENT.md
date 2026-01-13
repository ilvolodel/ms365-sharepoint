# MS365-SharePoint MCP Server - Microagent

**Service**: ms365-sharepoint  
**Domain**: https://ms365-sharepoint.brainaihub.tech  
**Version**: 1.0.0  
**Status**: ✅ Ready for Deployment  
**Droplet**: 10.135.215.172 (VPC), 161.35.214.46 (Public)

---

## 🎯 PURPOSE

Microsoft 365 SharePoint operations MCP server for AI agents.

**Use cases:**
- Access SharePoint sites and get metadata
- List sites accessible to user
- Browse lists in a site
- Read, create, update list items

**Tools (6):**
- sharepoint_get_site
- sharepoint_list_sites
- sharepoint_list_lists
- sharepoint_get_list_items
- sharepoint_create_list_item
- sharepoint_update_list_item

---

## 📋 CONTEXT

### Server Information
- **Repository**: https://github.com/ilvolodel/ms365-sharepoint
- **Production URL**: https://ms365-sharepoint.brainaihub.tech
- **MCP Endpoint**: https://ms365-sharepoint.brainaihub.tech/mcp/sse
- **Health Check**: https://ms365-sharepoint.brainaihub.tech/health
- **Port**: 8046 (internal)
- **Container**: `ms365-sharepoint-app`
- **Location**: `/opt/ms365-sharepoint/`

### Infrastructure
- **Droplet**: 10.135.215.172 (VPC), 161.35.214.46 (Public)
- **User**: root
- **Password**: Fr3qu3nc1.
- **Network**: `proxy-nginx_proxy-network` (shared with proxy-nginx)
- **Reverse Proxy**: proxy-nginx (swissknife) routes HTTPS → app:8046
- **SSL**: Let's Encrypt via swissknife certbot

### Architecture
- **Type**: Standalone MCP server
- **Auth**: ENV-based API key (atomic)
- **Framework**: FastMCP + FastAPI
- **Python**: 3.12-slim
- **Token Cache**: SQLite (aiosqlite) for TrustyVault tokens
- **Cache Location**: `/app/data/tokens.db`

---

## 🔑 SSH ACCESS

```bash
# Install sshpass first
sudo apt-get install -y sshpass

# SSH command (VPC private IP)
sshpass -p 'Fr3qu3nc1.' ssh -o StrictHostKeyChecking=no root@10.135.215.172 "COMMAND"
```

---

## 🔧 DEPLOYMENT (USE deploy.sh!)

### Automated Deployment (RECOMMENDED)

```bash
cd /workspace/ms365-sharepoint
./deploy.sh
```

**What deploy.sh does:**
1. Verify port 8046 available
2. Update swissknife .env (add SHAREPOINT_MCP_DOMAIN)
3. Update certbot-entrypoint.sh (add SharePoint cert block)
4. Add HTTP block to proxy-nginx (ACME challenge)
5. Reload nginx
6. Rebuild certbot container (gets certificate)
7. Wait for certificate file
8. Add HTTPS block to proxy-nginx (full routing)
9. Test nginx -t
10. Reload nginx
11. Clone/pull repo to /opt/ms365-sharepoint
12. Build app container
13. Start app
14. Health check

### Manual Deployment (If deploy.sh fails)

See section "MANUAL DEPLOYMENT STEPS" below.

---

## 🔍 DEBUGGING

### Check Container Status
```bash
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 "docker ps | grep ms365-sharepoint"
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 "curl -s http://localhost:8046/health | jq"
```

### View Logs
```bash
# Last 50 lines
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 "docker logs ms365-sharepoint-app --tail 50"

# Follow logs
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 "docker logs -f ms365-sharepoint-app"

# Search errors
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 "docker logs ms365-sharepoint-app 2>&1 | grep -i error"
```

### Check Nginx Routing
```bash
# Test from droplet
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 "curl -v https://ms365-sharepoint.brainaihub.tech/health"

# Check nginx config
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 "docker exec swissknife-nginx nginx -t"

# Check certificate
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 "ls -la /opt/swissknife/data/letsencrypt/live/ms365-sharepoint.brainaihub.tech/"
```

---

## 📁 FILE STRUCTURE

```
/opt/ms365-sharepoint/
├── src/
│   ├── main.py                      # FastMCP server (6 tools, 3 prompts)
│   ├── sharepoint_operations.py     # SharePoint business logic
│   ├── graph_client.py              # MS Graph API client
│   ├── trustyvault_client.py        # TrustyVault integration
│   ├── token_cache.py               # SQLite token cache
│   ├── auth_provider.py             # API key validation
│   ├── base.py                      # Base operation class
│   └── prompts/
│       ├── __init__.py
│       ├── get_site_info.py
│       ├── list_items.py
│       └── create_item.py
├── data/                            # SQLite database (tokens.db)
├── logs/                            # Application logs
├── .env                             # Configuration (NOT in git)
├── .env.example                     # Template
├── deploy.sh                        # Deployment script ⚠️
├── docker-compose.yml               # Container definition
├── Dockerfile                       # Image definition
├── requirements.txt                 # Python dependencies
├── MICROAGENT.md                    # This file
├── AGENT_PROMPT.md                  # AI agent guide
├── README.md                        # Documentation
└── PROGRESS.md                      # Implementation status
```

---

## 🔄 MANUAL DEPLOYMENT STEPS

**Use this only if deploy.sh fails!**

### Step 1: DNS Verification
```bash
curl -s "https://dns.google/resolve?name=ms365-sharepoint.brainaihub.tech&type=A" | grep data
# Expected: "data":"161.35.214.46"
```

### Step 2: Update Swissknife .env
```bash
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 << 'EOF'
cd /opt/swissknife
cp .env .env.backup-$(date +%Y%m%d-%H%M%S)
echo "SHAREPOINT_MCP_DOMAIN=ms365-sharepoint.brainaihub.tech" >> .env
grep SHAREPOINT_MCP_DOMAIN .env
EOF
```

### Step 3: Update Certbot Script
```bash
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 << 'EOF'
cd /opt/swissknife/scripts

# Backup
cp certbot-entrypoint.sh certbot-entrypoint.sh.backup

# Add SharePoint block (before "echo Starting maintenance loop...")
# Insert this block after FILES_MCP_DOMAIN section:

cat >> certbot-entrypoint-sharepoint-block.txt << 'CERTBOT_BLOCK'

# Check and obtain MS365 SharePoint MCP certificate if domain is configured
if [ -n "${SHAREPOINT_MCP_DOMAIN}" ]; then
    SHAREPOINT_CERT_EXISTS=false
    if [ -f "/etc/letsencrypt/live/${SHAREPOINT_MCP_DOMAIN}/fullchain.pem" ]; then
        echo "✅ Certificate for ${SHAREPOINT_MCP_DOMAIN} already exists"
        SHAREPOINT_CERT_EXISTS=true
    fi

    if [ "$SHAREPOINT_CERT_EXISTS" = "false" ]; then
        echo "📋 Obtaining MS365 SharePoint MCP SSL certificate..."

        STAGING_FLAG=""
        if [ "${SSL_MODE}" = "staging" ]; then
            STAGING_FLAG="--staging"
            echo "🧪 Using staging environment"
        fi

        if certbot certonly \
            --webroot \
            --webroot-path=/var/www/certbot \
            --email "${SSL_EMAIL}" \
            --agree-tos \
            --no-eff-email \
            --non-interactive \
            ${STAGING_FLAG} \
            -d "${SHAREPOINT_MCP_DOMAIN}"; then
            echo "✅ MS365 SharePoint MCP SSL certificate obtained successfully!"
        else
            echo "❌ Failed to obtain MS365 SharePoint MCP SSL certificate"
            echo "💡 MS365 SharePoint MCP will not be available - check DNS and firewall"
        fi
    else
        echo "✅ MS365 SharePoint MCP SSL certificate already present"
    fi
fi
CERTBOT_BLOCK

# Now manually edit the file to insert this block
nano certbot-entrypoint.sh
# Insert the block from certbot-entrypoint-sharepoint-block.txt before the maintenance loop
EOF
```

### Step 4: Add HTTP Block to Proxy-Nginx (ACME Challenge)
```bash
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 << 'EOF'
cd /opt/swissknife/nginx-swissknife/conf.d

# Backup
cp default.conf default.conf.backup-$(date +%Y%m%d-%H%M%S)

# Add HTTP block for ACME challenge (before last closing brace)
cat >> default.conf << 'NGINX_HTTP'

# MS365-SharePoint - HTTP only (for ACME challenge)
server {
    listen 80;
    server_name ms365-sharepoint.brainaihub.tech;

    # Let's Encrypt webroot
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect to HTTPS (will work after cert obtained)
    location / {
        return 301 https://$server_name$request_uri;
    }
}
NGINX_HTTP

# Test nginx config
docker exec swissknife-nginx nginx -t

# If OK, reload
if [ $? -eq 0 ]; then
    docker exec swissknife-nginx nginx -s reload
    echo "✅ Nginx reloaded (HTTP block added)"
else
    echo "❌ Nginx config error - FIX BEFORE PROCEEDING!"
    exit 1
fi
EOF
```

### Step 5: Rebuild Certbot (Gets Certificate)
```bash
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 << 'EOF'
cd /opt/swissknife

# Rebuild certbot container
docker compose up -d --force-recreate certbot

# Wait and watch logs
echo "Waiting for certificate..."
sleep 10
docker logs swissknife-certbot | tail -30
EOF
```

### Step 6: Verify Certificate
```bash
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 << 'EOF'
# Check certificate files
ls -la /opt/swissknife/data/letsencrypt/live/ms365-sharepoint.brainaihub.tech/

# Expected files:
# cert.pem, chain.pem, fullchain.pem, privkey.pem
EOF
```

### Step 7: Add HTTPS Block to Proxy-Nginx
```bash
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 << 'EOF'
cd /opt/swissknife/nginx-swissknife/conf.d

# Add HTTPS block (after HTTP block)
cat >> default.conf << 'NGINX_HTTPS'

# MS365-SharePoint - HTTPS
server {
    listen 443 ssl http2;
    server_name ms365-sharepoint.brainaihub.tech;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/ms365-sharepoint.brainaihub.tech/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ms365-sharepoint.brainaihub.tech/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Proxy to app container (shared network)
    location / {
        proxy_pass http://ms365-sharepoint-app:8046;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE support
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
        
        # CORS
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type' always;
        
        if ($request_method = OPTIONS) {
            return 204;
        }
    }
}
NGINX_HTTPS

# Test nginx config
docker exec swissknife-nginx nginx -t

# If OK, reload
if [ $? -eq 0 ]; then
    docker exec swissknife-nginx nginx -s reload
    echo "✅ Nginx reloaded (HTTPS block added)"
else
    echo "❌ Nginx config error - FIX BEFORE PROCEEDING!"
    exit 1
fi
EOF
```

### Step 8: Deploy App
```bash
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 << 'EOF'
# Clone or pull repo
if [ -d "/opt/ms365-sharepoint" ]; then
    cd /opt/ms365-sharepoint
    git pull origin main
else
    cd /opt
    git clone https://github.com/ilvolodel/ms365-sharepoint.git
    cd ms365-sharepoint
fi

# Create .env if missing
if [ ! -f ".env" ]; then
    cp .env.example .env
    # Generate API key
    API_KEY="ms365-sharepoint-prod-$(openssl rand -hex 24)"
    sed -i "s/YOUR_GENERATED_KEY_HERE/$API_KEY/" .env
    echo "✅ Generated API key: $API_KEY"
fi

# Create data directory
mkdir -p data logs

# Build and start
docker compose build
docker compose up -d

# Wait for health
echo "Waiting for health check..."
sleep 10

# Check health
curl -f http://localhost:8046/health || echo "❌ Health check failed"
EOF
```

### Step 9: Verify Deployment
```bash
# Test from outside
curl -v https://ms365-sharepoint.brainaihub.tech/health

# Expected: {"status":"healthy","service":"ms365-sharepoint","version":"1.0.0","tools":6,"prompts":3}
```

---

## 🧪 TESTING

### Health Check
```bash
curl https://ms365-sharepoint.brainaihub.tech/health
```

### MCP Inspector (Requires session_token from TrustyVault)
```bash
npx @modelcontextprotocol/inspector@latest --cli \
  https://ms365-sharepoint.brainaihub.tech/mcp/sse \
  --transport sse \
  --header "Authorization: Bearer [API_KEY_FROM_.env]" \
  --method tools/list
```

---

## 🔑 CONFIGURATION

### Environment Variables (.env)
```bash
PORT=8046
LOG_LEVEL=INFO
BASE_URL=https://ms365-sharepoint.brainaihub.tech
MCP_API_KEY=ms365-sharepoint-prod-[GENERATED]
TRUSTYVAULT_URL=https://trustyvault.brainaihub.tech
```

### Network
- **Container**: `ms365-sharepoint-app` (must be unique!)
- **Network**: `proxy-nginx_proxy-network` (shared)
- **Port**: 8046 (internal only, not exposed)

---

## 🐛 TROUBLESHOOTING

### Issue: Certificate not obtained
**Cause:** DNS not propagated or port 80 blocked

**Fix:**
```bash
# Check DNS
dig ms365-sharepoint.brainaihub.tech +short
# Should return: 161.35.214.46

# Check port 80 accessible
curl -v http://ms365-sharepoint.brainaihub.tech/.well-known/acme-challenge/test

# Check nginx HTTP block
docker exec swissknife-nginx cat /etc/nginx/conf.d/default.conf | grep -A 10 "ms365-sharepoint"
```

### Issue: nginx -t fails
**Cause:** Syntax error in config

**Fix:**
```bash
# View error
docker exec swissknife-nginx nginx -t

# Check config syntax
docker exec swissknife-nginx cat /etc/nginx/conf.d/default.conf

# Restore backup
cd /opt/swissknife/nginx-swissknife/conf.d
cp default.conf.backup-[TIMESTAMP] default.conf
docker exec swissknife-nginx nginx -s reload
```

### Issue: Container won't start
**Cause:** Port 8046 occupied or env misconfigured

**Fix:**
```bash
# Check port
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 "netstat -tulpn | grep 8046"

# Check logs
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 "docker logs ms365-sharepoint-app"

# Verify .env
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 "cat /opt/ms365-sharepoint/.env"
```

### Issue: Health check fails
**Cause:** App not responding on port 8046

**Fix:**
```bash
# Check container running
docker ps | grep ms365-sharepoint

# Check internal health
docker exec ms365-sharepoint-app curl -f http://localhost:8046/health

# Check logs
docker logs ms365-sharepoint-app --tail 100
```

---

## 📚 RELATED DOCUMENTATION

- **AGENT_PROMPT.md**: Guide for AI agents using the service
- **README.md**: Technical documentation
- **PROGRESS.md**: Implementation status
- **GitHub**: https://github.com/ilvolodel/ms365-sharepoint

---

## 🎯 QUICK REFERENCE

```bash
# Deploy (automated)
cd /workspace/ms365-sharepoint && ./deploy.sh

# Check status
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 "docker ps | grep sharepoint && curl -s http://localhost:8046/health"

# View logs
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 "docker logs ms365-sharepoint-app --tail 100"

# Restart
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 "cd /opt/ms365-sharepoint && docker compose restart"

# Check API key
sshpass -p 'Fr3qu3nc1.' ssh root@10.135.215.172 "grep MCP_API_KEY /opt/ms365-sharepoint/.env"
```

---

**Last Updated**: 2026-01-13  
**Status**: ✅ Ready for Production  
**Maintainer**: OpenHands AI Agent
