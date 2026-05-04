# Deployment Guide — DigitalOcean + CloudFlare

**Target:** `marinssolutions.com` on DigitalOcean Droplet  
**Droplet Spec:** Basic Premium Intel, 2 vCPU, 4 GB RAM, 120 GB SSD, 4 TB bandwidth  
**Cost:** ~$24-42/month (droplet) + CloudFlare Free ($0)

---

## 1. Prerequisites

Before deploying, ensure you have:

- [ ] DigitalOcean account with a Droplet provisioned
- [ ] `marinssolutions.com` configured in CloudFlare DNS
- [ ] GitHub repository with the Alter-Ego code
- [ ] SSH access to the droplet (root or sudo user)

---

## 2. GitHub Secrets (for CI/CD)

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Description |
|--------|-------------|
| `DO_HOST` | Your droplet's public IP address |
| `DO_USER` | SSH username (e.g. `root` or `deploy`) |
| `DO_SSH_KEY` | Private SSH key (pem format) |
| `POSTGRES_USER` | Database username (default: `rag_user`) |
| `POSTGRES_PASSWORD` | Strong random password |
| `POSTGRES_DB` | Database name (default: `rag_db`) |
| `PINECONE_API_KEY` | Pinecone API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `SECRET_KEY` | JWT signing key (`openssl rand -hex 32`) |
| `ANON_SECRET_KEY` | Anonymous token key (`openssl rand -hex 32`) |

---

## 3. Initial Server Setup

SSH into your droplet and run the automated deployment script:

```bash
ssh root@<DROPLET_IP>
curl -fsSL https://raw.githubusercontent.com/YOUR_USER/alter-ego/main/scripts/deploy.sh | bash
```

Or manually step-by-step:

### 3.1 Install Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git nginx certbot python3-certbot-nginx
```

### 3.2 Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

### 3.3 Clone Repository

```bash
git clone https://github.com/YOUR_USER/alter-ego.git /opt/alter-ego
cd /opt/alter-ego
```

### 3.4 Create Environment File

```bash
cat > /opt/alter-ego/.env << 'EOF'
POSTGRES_USER=rag_user
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_DB=rag_db
PINECONE_API_KEY=your_key
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
SECRET_KEY=$(openssl rand -hex 32)
ANON_SECRET_KEY=$(openssl rand -hex 32)
ALLOWED_ORIGINS=https://marinssolutions.com
EOF
```

### 3.5 Obtain SSL Certificate

```bash
sudo certbot --nginx -d marinssolutions.com -d www.marinssolutions.com
```

### 3.6 Deploy Application

```bash
cd /opt/alter-ego
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 4. CloudFlare DNS Configuration

1. Log in to [CloudFlare Dashboard](https://dash.cloudflare.com)
2. Select `marinssolutions.com`
3. Go to **DNS → Records**
4. Add an `A` record:
   - Name: `@` (root domain)
   - IPv4 address: `<your-droplet-ip>`
   - Proxy status: **Orange cloud** (Proxied)
5. Add another `A` record:
   - Name: `www`
   - IPv4 address: `<your-droplet-ip>`
   - Proxy status: **Orange cloud** (Proxied)
6. Go to **SSL/TLS → Overview**
7. Set encryption mode to **Full (strict)**

---

## 5. Verify Deployment

```bash
# Check application health
curl -s https://marinssolutions.com/health | jq .

# Check container status
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Check SSL certificate
openssl s_client -connect marinssolutions.com:443 -servername marinssolutions.com </dev/null
```

---

## 6. Updates & Rollbacks

### Automatic (GitHub Actions)

Push to `main` branch triggers automatic deployment:

```bash
git push origin main
```

### Manual

```bash
ssh root@<DROPLET_IP>
cd /opt/alter-ego
git pull origin main
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build
```

### Rollback

```bash
cd /opt/alter-ego
git log --oneline -5
git reset --hard <PREVIOUS_COMMIT>
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 7. Monitoring

### View Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Backend only
docker compose -f docker-compose.prod.yml logs -f backend

# Nginx access logs
docker compose -f docker-compose.prod.yml exec nginx tail -f /var/log/nginx/access.log
```

### Check Resource Usage

```bash
docker stats
```

### Database Backups

```bash
# Manual backup
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U rag_user rag_db > backup_$(date +%Y%m%d).sql

# Automated (add to crontab)
0 2 * * * cd /opt/alter-ego && docker compose -f docker-compose.prod.yml exec -T postgres pg_dump -U rag_user rag_db > /backups/rag_db_$(date +\%Y\%m\%d).sql
```

---

## 8. Troubleshooting

| Issue | Solution |
|-------|----------|
| SSL certificate error | Run `sudo certbot renew --force-renewal` |
| 502 Bad Gateway | Check backend health: `docker compose -f docker-compose.prod.yml ps` |
| WebSocket not connecting | Verify Nginx proxy config includes `upgrade` headers |
| CORS errors | Check `ALLOWED_ORIGINS` in `.env` matches domain |
| Database connection failed | Verify `.env` credentials match PostgreSQL container |
| Out of memory | Upgrade droplet or add swap: `sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile` |

---

## 9. Security Checklist

- [ ] UFW firewall enabled (`sudo ufw status`)
- [ ] SSH key authentication only (no password)
- [ ] Fail2Ban installed (`sudo apt install fail2ban`)
- [ ] Automatic security updates (`sudo apt install unattended-upgrades`)
- [ ] Docker socket not exposed
- [ ] `.env` file permissions: `chmod 600 .env`
- [ ] SSL certificate auto-renewal configured
- [ ] Database backups scheduled
- [ ] No secrets committed to git

---

## 10. Cost Breakdown

| Service | Monthly Cost |
|---------|-------------|
| DigitalOcean Droplet (2vCPU/4GB) | ~$24 |
| CloudFlare (DNS + SSL + CDN) | $0 |
| Pinecone (serverless, low traffic) | ~$0-5 |
| OpenAI API | ~$5-20 |
| Anthropic API | ~$5-20 |
| **Total** | **~$34-69/month** |

---

*Last updated: 2026-04-28*
