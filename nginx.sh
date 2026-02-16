#!/bin/bash

# AutoApply Nginx Setup Script
# Proxy:
#  /     -> localhost:3000 (Frontend)
#  /api/ -> localhost:8000 (Backend)

set -e

echo "======================================"
echo " AutoApply Nginx & SSL Setup"
echo "======================================"

# Must run as root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Run as root or sudo"
  exit 1
fi

DOMAIN="autoapply.haxcodes.dev"
EMAIL="bhuvanthirwani2208usa@gmail.com"

# Remove default if exists
rm -f /etc/nginx/sites-enabled/default

echo "🌐 Configuring Nginx reverse proxy for $DOMAIN..."

cat <<EOF >/etc/nginx/sites-available/$DOMAIN
server {
    listen 80;
    server_name $DOMAIN;

    # Frontend (Next.js)
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }

    # Backend API (FastAPI)
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        
        # Increase body size for file uploads
        client_max_body_size 50M;
    }
}
EOF

# Symlink
ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/

echo "🔍 Testing Nginx configuration..."
nginx -t

echo "🔄 Restarting Nginx..."
systemctl restart nginx

echo "📦 Installing Certbot (if needed)..."
if ! command -v certbot &> /dev/null; then
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
fi

echo "🔒 Obtaining SSL for $DOMAIN..."
certbot --nginx -d $DOMAIN --non-interactive --agree-tos -m $EMAIL --redirect

echo "✅ Nginx & SSL Setup Complete!"
