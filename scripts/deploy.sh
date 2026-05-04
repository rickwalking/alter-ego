#!/bin/bash
set -e

echo "=== Alter-Ego Deployment Script ==="
echo "Target: DigitalOcean Droplet"
echo "Domain: marinssolutions.com"
echo ""

# Check if running as root (not recommended)
if [ "$EUID" -eq 0 ]; then
  echo "Warning: Running as root. It's better to use a non-root user with sudo."
fi

# Configuration
APP_DIR="/opt/alter-ego"
REPO_URL="https://github.com/pmarins/alter-ego.git"  # Update this
DOMAIN="marinssolutions.com"

# Install dependencies
echo "[1/8] Installing dependencies..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
  apt-transport-https \
  ca-certificates \
  curl \
  gnupg \
  lsb-release \
  git \
  nginx \
  certbot \
  python3-certbot-nginx

# Install Docker
echo "[2/8] Installing Docker..."
if ! command -v docker &> /dev/null; then
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
  echo "Docker installed. You may need to log out and back in for group changes."
fi

# Install Docker Compose
echo "[3/8] Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
  sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  sudo chmod +x /usr/local/bin/docker-compose
fi

# Clone repository
echo "[4/8] Setting up application directory..."
if [ ! -d "$APP_DIR" ]; then
  sudo mkdir -p "$APP_DIR"
  sudo git clone "$REPO_URL" "$APP_DIR"
fi
sudo chown -R "$USER:$USER" "$APP_DIR"

# Create environment file
echo "[5/8] Creating environment file..."
cd "$APP_DIR"
if [ ! -f .env ]; then
  cat > .env << EOF
POSTGRES_USER=rag_user
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_DB=rag_db
PINECONE_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
SECRET_KEY=$(openssl rand -hex 32)
ANON_SECRET_KEY=$(openssl rand -hex 32)
ALLOWED_ORIGINS=https://$DOMAIN
EOF
  echo "Environment file created. Please edit $APP_DIR/.env and add your API keys."
fi

# SSL certificate
echo "[6/8] Setting up SSL certificate..."
if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
  echo "Obtaining SSL certificate for $DOMAIN..."
  sudo certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" --non-interactive --agree-tos --email admin@$DOMAIN
fi

# Firewall
echo "[7/8] Configuring firewall..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Deploy
echo "[8/8] Deploying application..."
cd "$APP_DIR"
docker compose -f docker-compose.prod.yml down 2>/dev/null || true
docker compose -f docker-compose.prod.yml up -d --build

echo ""
echo "=== Deployment Complete ==="
echo "Application: https://$DOMAIN"
echo "API Health:  https://$DOMAIN/health"
echo ""
echo "Next steps:"
echo "1. Edit $APP_DIR/.env and add your API keys"
echo "2. Run: docker compose -f docker-compose.prod.yml restart"
echo "3. Check logs: docker compose -f docker-compose.prod.yml logs -f"
