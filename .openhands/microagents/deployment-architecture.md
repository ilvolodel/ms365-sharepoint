# MS365-SharePoint MCP Server - Deployment & Architecture

**Version**: 1.0.0  
**Status**: ✅ Production  
**Last Updated**: 2026-01-13

---

## 🎯 SUMMARY

Complete deployment and architecture knowledge for MS365-SharePoint MCP Server.

**Service**: ms365-sharepoint  
**Domain**: https://ms365-sharepoint.brainaihub.tech  
**Container**: ms365-sharepoint-app (port 8046)  
**Network**: proxy-nginx_proxy-network (shared)  
**Deploy Path**: /opt/ms365-sharepoint

---

## 🏗️ ARCHITECTURE

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

## 🚀 DEPLOYMENT CHECKLIST

### Pre-Deployment
- [x] DNS A record: ms365-sharepoint.brainaihub.tech → 161.35.214.46
- [x] SSH access: root@10.135.215.172 (password: Fr3qu3nc1.)
- [x] Port 8046 available
- [x] Docker network exists: proxy-nginx_proxy-network
- [ ] TrustyVault permissions: Sites.Read.All, Sites.ReadWrite.All
- [ ] Azure AD: User/admin consent for permissions

### Deployment Steps (Quick)

**1. Update Certbot** (add SHAREPOINT_MCP_DOMAIN):
```bash
ssh root@10.135.215.172
cd /opt/swissknife
echo "SHAREPOINT_MCP_DOMAIN=ms365-sharepoint.brainaihub.tech" >> .env
# certbot-entrypoint.sh already has SharePoint block!
```

**2. Configure Nginx HTTP** (ACME challenge):
```bash
cd /opt/swissknife/nginx-swissknife/conf.d
cat >> default.conf << 'EOF'
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
docker exec swissknife-nginx nginx -t && docker exec swissknife-nginx nginx -s reload
```

**3. Get Certificate**:
```bash
cd /opt/swissknife
docker compose up -d --force-recreate certbot
docker logs swissknife-certbot | grep -i sharepoint
# Expected: "✅ MS365 SharePoint MCP SSL certificate obtained successfully!"
```

**4. Deploy App**:
```bash
cd /opt
git clone https://github.com/ilvolodel/ms365-sharepoint.git
cd ms365-sharepoint
cp .env.example .env
sed -i "s/YOUR_GENERATED_KEY_HERE/ms365-sharepoint-prod-$(openssl rand -hex 24)/" .env
mkdir -p data logs
docker compose build && docker compose up -d
```

**5. Configure Nginx HTTPS** (after app starts):
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

**6. Verify**:
```bash
curl -s https://ms365-sharepoint.brainaihub.tech/health | jq
# Expected: {"status":"healthy","service":"ms365-sharepoint","version":"1.0.0","tools":6}
```

---

## 🔍 TROUBLESHOOTING

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
docker logs swissknife-certbot | grep -i error
```

**Port conflicts**:
```bash
docker ps | grep 8046
netstat -tlnp | grep 8046  # If available
```

---

## 📋 KEY FILES

- `/opt/ms365-sharepoint/.env` - API key & config
- `/opt/ms365-sharepoint/data/tokens.db` - Token cache
- `/opt/ms365-sharepoint/logs/` - Application logs
- `/opt/swissknife/nginx-swissknife/conf.d/default.conf` - Nginx config
- `/opt/swissknife/scripts/certbot-entrypoint.sh` - Certbot script

---

## 🔐 IMPORTANT VALUES

| Item | Value |
|------|-------|
| Domain | https://ms365-sharepoint.brainaihub.tech |
| Public IP | 161.35.214.46 |
| VPC IP | 10.135.215.172 |
| SSH User | root |
| SSH Pass | Fr3qu3nc1. |
| Container | ms365-sharepoint-app |
| Port | 8046 (internal) |
| Network | proxy-nginx_proxy-network |
| API Key | In /opt/ms365-sharepoint/.env |

---

## 🎯 CRITICAL NOTES FOR NEXT AGENT

1. **Container Name**: MUST be `ms365-sharepoint-app` (unique on shared network)
2. **Port Variable**: Dockerfile CMD uses `${PORT:-8046}` not hardcoded
3. **Nginx Container**: Name is `swissknife-nginx` NOT `nginx-swissknife`
4. **HTTPS Config**: Add AFTER app container starts (avoid "host not found")
5. **Certificate Path**: Inside certbot container, shared via volumes
6. **Token Cache**: SQLite reduces TrustyVault calls by 95%+
7. **No Internal Nginx**: proxy-nginx handles all SSL/routing

**Common Mistakes**:
- ❌ Adding HTTPS block before app starts
- ❌ Using wrong container name in commands
- ❌ Hardcoding port in Dockerfile
- ❌ Forgetting to create .env file
- ❌ Port conflict with other services

**Success Pattern**:
1. Certbot → Get cert
2. Deploy app → Container running
3. Nginx HTTPS → Reverse proxy configured
4. Test → Health check passes

---

**See MICROAGENT.md for full manual deployment guide**
