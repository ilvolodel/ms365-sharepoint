# MS365-SharePoint MCP Server - Deployment & Architecture

**Version**: 1.0.0  
**Status**: ✅ Production  
**Last Updated**: 2026-02-02

---

## 🎯 Overview

MCP server for Microsoft SharePoint operations via TrustyVault authentication.

**Service**: ms365-sharepoint  
**Domain**: https://ms365-sharepoint.brainaihub.tech  
**Container**: ms365-sharepoint-app (port 8046)  
**Network**: proxy-nginx_proxy-network (shared)  
**Deploy Path**: /opt/ms365-sharepoint

---

## 🏗️ Architecture

```
Internet (HTTPS:443) → DNS (161.35.214.46) → Droplet
    ↓
[proxy-nginx/swissknife-nginx]
    ├─ Port 80: ACME challenge + redirect HTTPS
    ├─ Port 443: SSL termination → proxy to app
    └─ Config: /opt/swissknife/nginx-swissknife/conf.d/default.conf
        ↓
[ms365-sharepoint-app:8046] on proxy-nginx_proxy-network
    ├─ FastMCP + FastAPI (Uvicorn)
    ├─ 6 SharePoint tools + 3 prompts
    ├─ Token cache: SQLite (/app/data/tokens.db)
    └─ TrustyVault OAuth integration
```

**Key Components**:
1. **DNS**: ms365-sharepoint.brainaihub.tech → 161.35.214.46 (public)
2. **SSL**: Let's Encrypt cert via certbot (auto-renew)
3. **Reverse Proxy**: swissknife-nginx handles HTTPS → http://ms365-sharepoint-app:8046
4. **App Container**: FastMCP server with SharePoint operations
5. **Shared Network**: All services on `proxy-nginx_proxy-network`

---

## 🚀 Production Deployment

### Prerequisites

- [x] DNS A record: ms365-sharepoint.brainaihub.tech → 161.35.214.46
- [x] SSH access: root@10.135.215.172
- [x] Port 8046 available
- [x] Docker network exists: proxy-nginx_proxy-network
- [x] TrustyVault permissions: Sites.Read.All, Sites.ReadWrite.All

### Quick Deployment

**1. Clone & Configure**
```bash
ssh root@10.135.215.172
cd /opt
git clone https://github.com/ilvolodel/ms365-sharepoint.git
cd ms365-sharepoint

# Create .env file
cat > .env << 'EOF'
# MCP API Security
MCP_API_KEY=ms365-sharepoint-prod-[GENERATE_KEY]

# TrustyVault Integration
TRUSTYVAULT_URL=https://trustyvault.brainaihub.tech

# Server Configuration
PORT=8046
LOG_LEVEL=INFO

# Microsoft Graph (optional, for reference)
MICROSOFT_CLIENT_ID=22ef08fc-5d2c-4bcc-8a64-0b2feb48f946
MICROSOFT_TENANT_ID=e159c0a6-837c-4629-bf29-5ae43de9fb34
EOF

# Generate API key
sed -i "s/\[GENERATE_KEY\]/$(openssl rand -hex 32)/" .env

mkdir -p data logs
```

**2. Configure SSL (Certbot)**
```bash
cd /opt/swissknife
echo "SHAREPOINT_MCP_DOMAIN=ms365-sharepoint.brainaihub.tech" >> .env

# Add HTTP config for ACME challenge
cat >> nginx-swissknife/conf.d/default.conf << 'EOF'
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
EOF

# Get certificate
docker compose up -d --force-recreate certbot
docker logs swissknife-certbot | grep -i sharepoint
```

**3. Deploy App**
```bash
cd /opt/ms365-sharepoint
docker compose build && docker compose up -d
```

**4. Configure HTTPS (after app starts)**
```bash
cd /opt/swissknife/nginx-swissknife/conf.d
cat >> default.conf << 'EOF'
server {
    listen 443 ssl http2;
    server_name ms365-sharepoint.brainaihub.tech;
    ssl_certificate /etc/letsencrypt/live/ms365-sharepoint.brainaihub.tech/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ms365-sharepoint.brainaihub.tech/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    
    location / {
        proxy_pass http://ms365-sharepoint-app:8046;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
        add_header 'Access-Control-Allow-Origin' '*' always;
    }
}
EOF

docker exec swissknife-nginx nginx -t && docker exec swissknife-nginx nginx -s reload
```

**5. Verify**
```bash
curl -s https://ms365-sharepoint.brainaihub.tech/health | jq
# Expected: {"status":"healthy","service":"ms365-sharepoint","version":"1.0.0","tools":6}
```

---

## 🔄 Updates & Maintenance

### Update Code
```bash
ssh root@10.135.215.172
cd /opt/ms365-sharepoint
git pull
docker compose build
docker compose up -d
```

### View Logs
```bash
docker logs ms365-sharepoint-app --tail 100 -f
```

### Restart Service
```bash
docker compose restart
```

### Check Status
```bash
docker ps | grep ms365-sharepoint
curl https://ms365-sharepoint.brainaihub.tech/health
```

---

## 🔍 Troubleshooting

**Container not responding**:
```bash
docker logs ms365-sharepoint-app --tail 50
docker exec ms365-sharepoint-app curl http://localhost:8046/health
```

**Nginx errors**:
```bash
docker exec swissknife-nginx nginx -t
docker logs swissknife-nginx | tail -50
```

**Certificate issues**:
```bash
docker exec swissknife-certbot ls -la /etc/letsencrypt/live/ms365-sharepoint.brainaihub.tech/
```

**Port conflicts**:
```bash
docker ps | grep 8046
ss -tlnp | grep 8046
```

---

## 📋 Key Files

- `/opt/ms365-sharepoint/.env` - API key & config
- `/opt/ms365-sharepoint/data/tokens.db` - Token cache (SQLite)
- `/opt/ms365-sharepoint/logs/` - Application logs
- `/opt/swissknife/nginx-swissknife/conf.d/default.conf` - Nginx config
- `/opt/swissknife/scripts/certbot-entrypoint.sh` - Certbot script

---

## 🔐 Production Values

| Item | Value |
|------|-------|
| Domain | https://ms365-sharepoint.brainaihub.tech |
| Public IP | 161.35.214.46 |
| VPC IP | 10.135.215.172 |
| SSH User | root |
| Container | ms365-sharepoint-app |
| Port | 8046 (internal) |
| Network | proxy-nginx_proxy-network |
| API Key | See /opt/ms365-sharepoint/.env |

---

## ⚠️ Critical Notes

1. **Container Name**: MUST be `ms365-sharepoint-app` (unique on shared network)
2. **Port Variable**: Dockerfile CMD uses `${PORT:-8046}` not hardcoded
3. **Nginx Container**: Name is `swissknife-nginx` NOT `nginx-swissknife`
4. **HTTPS Config**: Add AFTER app container starts (avoid "host not found")
5. **Token Cache**: SQLite reduces TrustyVault calls by 95%+
6. **No Internal Nginx**: proxy-nginx handles all SSL/routing

---

**Last Updated**: 2026-02-02  
**Status**: ✅ Fully Deployed & Operational
