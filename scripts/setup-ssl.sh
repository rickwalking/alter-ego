#!/bin/bash
set -e

echo "=== SSL Setup for marinssolutions.com ==="
echo "Make sure DNS A record points to 206.189.180.85 before running this script."
echo ""

# Stop nginx temporarily to free port 80 for certbot standalone
cd /opt/alter-ego
docker compose -f docker-compose.prod.yml stop nginx

# Get certificate
certbot certonly --standalone -d marinssolutions.com -d www.marinssolutions.com --non-interactive --agree-tos --email ph.marins@hotmail.com

# Verify certificate was created
if [ ! -f /etc/letsencrypt/live/marinssolutions.com/fullchain.pem ]; then
    echo "ERROR: Certificate not created. Check DNS and try again."
    docker compose -f docker-compose.prod.yml start nginx
    exit 1
fi

# Backup current nginx config
cp /opt/alter-ego/nginx/nginx.conf /opt/alter-ego/nginx/nginx.conf.http

# Switch to SSL config
cp /opt/alter-ego/nginx/nginx.conf.ssl /opt/alter-ego/nginx/nginx.conf

# Restart nginx with SSL
docker compose -f docker-compose.prod.yml up -d nginx

echo ""
echo "=== SSL Setup Complete ==="
echo "Test: https://marinssolutions.com/api/health"
