#!/bin/bash
"""
Team Omega - EC2 Deployment Script
Automates the deployment of the enhanced API on EC2
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Team Omega - EC2 Deployment Script${NC}"
echo "============================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}❌ This script should NOT be run as root${NC}"
   exit 1
fi

# Configuration
USER_HOME="/home/ubuntu"
SERVICE_NAME="enhanced-api"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo -e "${YELLOW}📋 Updating system packages...${NC}"
sudo apt update && sudo apt upgrade -y

echo -e "${YELLOW}🐍 Installing Python dependencies...${NC}"
sudo apt install python3-pip python3-venv python3-dev -y

echo -e "${YELLOW}📦 Installing system dependencies...${NC}"
sudo apt install nginx curl wget git -y

echo -e "${YELLOW}📁 Setting up application directory...${NC}"
mkdir -p $USER_HOME/astra
cd $USER_HOME/astra

# Copy application files
if [ -f "enhanced_api.py" ]; then
    echo -e "${GREEN}✅ Application files already present${NC}"
else
    echo -e "${YELLOW}📥 Copying application files...${NC}"
    # This assumes the script is run from the project directory
    cp ../cloud/enhanced_api.py ./
    cp ../cloud/requirements.txt ./
fi

echo -e "${YELLOW}🐍 Creating Python virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

echo -e "${YELLOW}📦 Installing Python packages...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${YELLOW}📝 Creating environment configuration...${NC}"
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# Team Omega - EC2 Environment Configuration
FLASK_PORT=5000
FLASK_HOST=0.0.0.0
FLASK_DEBUG=false

# AWS Configuration
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here

# DynamoDB Tables (existing infrastructure)
EXISTING_DDB_TABLE_NAME=UGVTelemetry
EXISTING_LIDAR_TABLE_NAME=UGVLidarScans
ULTRASONIC_TABLE_NAME=UGVUltrasonic
BATTERY_TABLE_NAME=UGVBattery
IMAGES_TABLE_NAME=UGVImages

# API Configuration
API_HOST=0.0.0.0
API_PORT=5000
API_DEBUG=false
API_RELOAD=false

# Dashboard Configuration
DASHBOARD_REFRESH_INTERVAL=2000
DASHBOARD_MAP_CENTER_LAT=37.7749
DASHBOARD_MAP_CENTER_LON=-122.4194
DASHBOARD_MAP_ZOOM=16

# Database Configuration
DATABASE_TYPE=dynamodb_local
DATABASE_URL=sqlite:///astra.db
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Image Storage
IMAGE_STORAGE_PATH=/home/ubuntu/astra/storage/images
IMAGE_MAX_SIZE_MB=10
IMAGE_FORMATS=jpg,jpeg,png
IMAGE_COMPRESSION_QUALITY=85

# Security Configuration
API_KEY_REQUIRED=false
API_KEY_HEADER=X-API-Key
JWT_SECRET_KEY=your_jwt_secret_here
JWT_ACCESS_TOKEN_EXPIRES=3600
CORS_ORIGINS=*

# Monitoring Configuration
HEALTH_CHECK_INTERVAL=30
LOG_LEVEL=INFO
LOG_FILE=/var/log/astra/api.log
METRICS_ENABLED=true
METRICS_PORT=9090

# EC2 Integration
EC2_INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
EC2_INSTANCE_TYPE=$(curl -s http://169.254.169.254/latest/meta-data/instance-type)
EC2_AVAILABILITY_ZONE=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)

# ZeroTier Configuration
ZEROTIER_ENABLED=false
ZEROTIER_NETWORK_ID=your_zerotier_network_id
ZEROTIER_INTERFACE=zt0
EOF
    echo -e "${GREEN}✅ Environment file created${NC}"
else
    echo -e "${GREEN}✅ Environment file already exists${NC}"
fi

echo -e "${YELLOW}🔧 Creating systemd service...${NC}"
sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=Team Omega Enhanced API
After=network.target
Wants=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=$USER_HOME/astra
Environment=PATH=$USER_HOME/astra/venv/bin
Environment=PYTHONPATH=$USER_HOME/astra
ExecStart=$USER_HOME/astra/venv/bin/python enhanced_api.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=enhanced-api

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$USER_HOME/astra
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictRealtime=true
RestrictSUIDSGID=true

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

echo -e "${YELLOW}🔧 Creating Nginx configuration...${NC}"
sudo tee /etc/nginx/sites-available/astra-api > /dev/null << EOF
server {
    listen 80;
    server_name _;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # API endpoints
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:5000/health;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        access_log off;
    }

    # Static files (if any)
    location /static/ {
        alias $USER_HOME/astra/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/javascript;
}
EOF

echo -e "${YELLOW}📁 Creating log directory...${NC}"
sudo mkdir -p /var/log/astra
sudo chown ubuntu:ubuntu /var/log/astra

echo -e "${YELLOW}📁 Creating storage directory...${NC}"
mkdir -p $USER_HOME/astra/storage/images
mkdir -p $USER_HOME/astra/static

echo -e "${YELLOW}🔧 Configuring firewall...${NC}"
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 5000/tcp

echo -e "${YELLOW}🔄 Reloading systemd...${NC}"
sudo systemctl daemon-reload

echo -e "${YELLOW}🚀 Enabling and starting services...${NC}"
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

sudo systemctl enable nginx
sudo systemctl restart nginx

# Enable Nginx site
sudo ln -sf /etc/nginx/sites-available/astra-api /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl reload nginx

echo -e "${YELLOW}⏳ Waiting for service to start...${NC}"
sleep 5

echo -e "${YELLOW}🧪 Testing service...${NC}"
if curl -f http://localhost:5000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API service is running${NC}"
else
    echo -e "${RED}❌ API service failed to start${NC}"
    sudo systemctl status $SERVICE_NAME
    exit 1
fi

if curl -f http://localhost/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Nginx proxy is working${NC}"
else
    echo -e "${RED}❌ Nginx proxy failed${NC}"
    sudo systemctl status nginx
    exit 1
fi

echo -e "${YELLOW}📊 Creating status script...${NC}"
cat > $USER_HOME/astra/status.sh << 'EOF'
#!/bin/bash
echo "🚀 Team Omega Enhanced API Status"
echo "=================================="

echo -e "\n📡 Service Status:"
sudo systemctl status enhanced-api --no-pager -l

echo -e "\n🌐 Nginx Status:"
sudo systemctl status nginx --no-pager -l

echo -e "\n🔗 API Health Check:"
curl -s http://localhost:5000/health | jq . 2>/dev/null || curl -s http://localhost:5000/health

echo -e "\n📋 Recent Logs:"
journalctl -u enhanced-api --no-pager -n 10

echo -e "\n🌍 External Access:"
echo "Dashboard: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/dashboard"
echo "API Health: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/health"
EOF

chmod +x $USER_HOME/astra/status.sh

echo -e "${YELLOW}📝 Creating management script...${NC}"
cat > $USER_HOME/astra/manage.sh << 'EOF'
#!/bin/bash
case "$1" in
    start)
        sudo systemctl start enhanced-api
        sudo systemctl start nginx
        echo "✅ Services started"
        ;;
    stop)
        sudo systemctl stop enhanced-api
        sudo systemctl stop nginx
        echo "🛑 Services stopped"
        ;;
    restart)
        sudo systemctl restart enhanced-api
        sudo systemctl restart nginx
        echo "🔄 Services restarted"
        ;;
    status)
        sudo systemctl status enhanced-api
        sudo systemctl status nginx
        ;;
    logs)
        journalctl -u enhanced-api -f
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
EOF

chmod +x $USER_HOME/astra/manage.sh

echo -e "${BLUE}🎉 Team Omega EC2 Deployment Complete!${NC}"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Edit $USER_HOME/astra/.env with your AWS credentials"
echo "2. Test the API: curl http://localhost:5000/health"
echo "3. Access dashboard: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/dashboard"
echo "4. Check status: $USER_HOME/astra/status.sh"
echo ""
echo -e "${YELLOW}🔧 Management Commands:${NC}"
echo "• Status: $USER_HOME/astra/status.sh"
echo "• Manage: $USER_HOME/astra/manage.sh {start|stop|restart|status|logs}"
echo "• Logs: journalctl -u enhanced-api -f"
echo ""
echo -e "${YELLOW}📁 Important Files:${NC}"
echo "• Config: $USER_HOME/astra/.env"
echo "• Logs: /var/log/astra/"
echo "• Service: $SERVICE_FILE"
echo "• Nginx: /etc/nginx/sites-available/astra-api"
echo ""
echo -e "${GREEN}✅ Ready to receive telemetry from your rover! 🚀${NC}"
