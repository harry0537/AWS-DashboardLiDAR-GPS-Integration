#!/bin/bash
"""
Team Omega - Project Astra Service Deployment Script
Sets up all services on the NUC companion computer
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ASTRA_USER="astra"
ASTRA_GROUP="astra"
ASTRA_HOME="/opt/astra"
SERVICE_DIR="/etc/systemd/system"
LOG_DIR="/var/log/astra"

echo -e "${BLUE}🚀 Team Omega - Project Astra Service Deployment${NC}"
echo "=================================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ This script must be run as root${NC}"
   exit 1
fi

# Create astra user and group if they don't exist
echo -e "${YELLOW}📋 Setting up user and group...${NC}"
if ! id "$ASTRA_USER" &>/dev/null; then
    useradd -r -s /bin/bash -d "$ASTRA_HOME" -c "Team Omega Astra Services" "$ASTRA_USER"
    echo -e "${GREEN}✅ Created user: $ASTRA_USER${NC}"
else
    echo -e "${GREEN}✅ User $ASTRA_USER already exists${NC}"
fi

if ! getent group "$ASTRA_GROUP" &>/dev/null; then
    groupadd "$ASTRA_GROUP"
    echo -e "${GREEN}✅ Created group: $ASTRA_GROUP${NC}"
else
    echo -e "${GREEN}✅ Group $ASTRA_GROUP already exists${NC}"
fi

# Add user to group
usermod -a -G "$ASTRA_GROUP" "$ASTRA_USER"

# Create directories
echo -e "${YELLOW}📁 Creating directories...${NC}"
mkdir -p "$ASTRA_HOME"
mkdir -p "$ASTRA_HOME/companion"
mkdir -p "$ASTRA_HOME/cloud"
mkdir -p "$ASTRA_HOME/ops"
mkdir -p "$LOG_DIR"
mkdir -p "$LOG_DIR/mavproxy"
mkdir -p "$LOG_DIR/ntrip"
mkdir -p "$LOG_DIR/telemetry"
mkdir -p "$LOG_DIR/lidar"
mkdir -p "$LOG_DIR/camera"

# Set ownership
chown -R "$ASTRA_USER:$ASTRA_GROUP" "$ASTRA_HOME"
chown -R "$ASTRA_USER:$ASTRA_GROUP" "$LOG_DIR"

# Set permissions
chmod 755 "$ASTRA_HOME"
chmod 755 "$LOG_DIR"
chmod 755 "$LOG_DIR"/*

echo -e "${GREEN}✅ Directories created and permissions set${NC}"

# Copy service files
echo -e "${YELLOW}🔧 Installing systemd services...${NC}"

# Copy all service files
cp "$ASTRA_HOME/ops/deploy/"*.service "$SERVICE_DIR/"
cp "$ASTRA_HOME/ops/deploy/"*.target "$SERVICE_DIR/"

# Set proper permissions on service files
chmod 644 "$SERVICE_DIR"/*.service
chmod 644 "$SERVICE_DIR"/*.target

echo -e "${GREEN}✅ Service files installed${NC}"

# Reload systemd
echo -e "${YELLOW}🔄 Reloading systemd...${NC}"
systemctl daemon-reload

# Enable services
echo -e "${YELLOW}🚀 Enabling services...${NC}"

# Enable the main target
systemctl enable astra.target

# Enable core services
systemctl enable mavproxy.service
systemctl enable ntrip-client.service
systemctl enable enhanced-telemetry.service

echo -e "${GREEN}✅ Core services enabled${NC}"

# Create environment file template
echo -e "${YELLOW}📝 Creating environment configuration...${NC}"
cat > "$ASTRA_HOME/companion/.env" << 'EOF'
# Team Omega - Companion NUC Environment Configuration
# Edit these values for your deployment

# ===== MAVLink & Routing =====
MAVPROXY_MASTER_PORT=/dev/ttyS5
MAVPROXY_MASTER_BAUD=921600
MAVPROXY_LOCAL_PORT=14550
MAVPROXY_FUSION_PORT=14551
MAVPROXY_TELEMETRY_PORT=14552
MAVPROXY_GCS_IP=192.168.1.100
MAVPROXY_GCS_PORT=14550

# ===== RTK GNSS Configuration =====
NTRIP_CASTER_URL=your_ntrip_caster_url
NTRIP_USERNAME=your_username
NTRIP_PASSWORD=your_password
NTRIP_MOUNTPOINT=your_mountpoint
NTRIP_PORT=2101
GPS_SERIAL_PORT=/dev/ttyS5
GPS_BAUD_RATE=921600

# ===== LiDAR Configuration =====
LIDAR_SERIAL_PORT=/dev/ttyUSB0
LIDAR_BAUD_RATE=115200
LIDAR_SCAN_RATE_HZ=10
LIDAR_MAX_DISTANCE_MM=8000
LIDAR_MIN_DISTANCE_MM=100

# ===== Camera Configuration =====
CAMERA_DEVICE=/dev/video0
CAMERA_WIDTH=1920
CAMERA_HEIGHT=1080
CAMERA_FPS=30
CAMERA_CAPTURE_INTERVAL=2.0

# ===== Ultrasonic Configuration (Optional) =====
ULTRASONIC_I2C_ADDRESS=0x70
ULTRASONIC_ENABLED=true
ULTRASONIC_READ_INTERVAL=0.1

# ===== Telemetry Uplink =====
EC2_API_URL=http://your-ec2-instance:5000
DEVICE_ID=astra-rover-1
TELEMETRY_UPLINK_INTERVAL=2.0
TELEMETRY_RETRY_ATTEMPTS=3
TELEMETRY_RETRY_DELAY=1.0

# ===== Return-to-Base =====
RTB_ENABLED=true
RTB_LOW_BATTERY_THRESHOLD=15.0
RTB_LOW_BATTERY_VOLTAGE=10.5

# ===== System Configuration =====
LOG_LEVEL=INFO
LOG_FILE=/var/log/astra/astra.log
HEALTH_CHECK_INTERVAL=30.0

# ===== Network Configuration =====
ZEROTIER_NETWORK_ID=your_zerotier_network_id
REVERSE_SSH_ENABLED=true
REVERSE_SSH_HOST=your-ec2-instance
REVERSE_SSH_PORT=22
REVERSE_SSH_USER=ubuntu

# ===== Storage Configuration =====
IMAGE_STORAGE_PATH=/opt/astra/storage/images
TELEMETRY_STORAGE_PATH=/opt/astra/storage/telemetry
MAX_STORAGE_GB=100
EOF

# Set ownership of environment file
chown "$ASTRA_USER:$ASTRA_GROUP" "$ASTRA_HOME/companion/.env"
chmod 600 "$ASTRA_HOME/companion/.env"

echo -e "${GREEN}✅ Environment configuration created${NC}"

# Create Python virtual environment
echo -e "${YELLOW}🐍 Setting up Python virtual environment...${NC}"
if [[ ! -d "$ASTRA_HOME/venv" ]]; then
    python3 -m venv "$ASTRA_HOME/venv"
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${GREEN}✅ Virtual environment already exists${NC}"
fi

# Install Python dependencies
echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
"$ASTRA_HOME/venv/bin/pip" install --upgrade pip
"$ASTRA_HOME/venv/bin/pip" install -r "$ASTRA_HOME/companion/requirements.txt"

echo -e "${GREEN}✅ Python dependencies installed${NC}"

# Create startup script
echo -e "${YELLOW}📜 Creating startup script...${NC}"
cat > "$ASTRA_HOME/start_astra.sh" << 'EOF'
#!/bin/bash
"""
Team Omega - Project Astra Startup Script
Starts all Astra services
"""

echo "🚀 Starting Team Omega Project Astra services..."

# Start the main target
systemctl start astra.target

# Check service status
echo "📊 Service Status:"
systemctl status astra.target --no-pager -l

echo "✅ Astra services started!"
echo "📋 Use 'systemctl status astra.target' to check status"
echo "📋 Use 'journalctl -u astra.target -f' to follow logs"
EOF

chmod +x "$ASTRA_HOME/start_astra.sh"
chown "$ASTRA_USER:$ASTRA_GROUP" "$ASTRA_HOME/start_astra.sh"

# Create stop script
cat > "$ASTRA_HOME/stop_astra.sh" << 'EOF'
#!/bin/bash
"""
Team Omega - Project Astra Stop Script
Stops all Astra services
"""

echo "🛑 Stopping Team Omega Project Astra services..."

# Stop the main target
systemctl stop astra.target

echo "✅ Astra services stopped!"
EOF

chmod +x "$ASTRA_HOME/stop_astra.sh"
chown "$ASTRA_USER:$ASTRA_GROUP" "$ASTRA_HOME/stop_astra.sh"

# Create status script
cat > "$ASTRA_HOME/status_astra.sh" << 'EOF'
#!/bin/bash
"""
Team Omega - Project Astra Status Script
Shows status of all Astra services
"""

echo "📊 Team Omega Project Astra Service Status"
echo "=========================================="

# Show target status
echo -e "\n🎯 Main Target:"
systemctl status astra.target --no-pager -l

# Show individual service status
echo -e "\n🔧 Individual Services:"
services=("mavproxy" "ntrip-client" "enhanced-telemetry" "lidar-driver" "camera-capture" "obstacle-fusion")

for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service.service"; then
        echo -e "✅ $service.service: $(systemctl is-active $service.service)"
    else
        echo -e "❌ $service.service: $(systemctl is-active $service.service)"
    fi
done

# Show logs
echo -e "\n📋 Recent Logs:"
journalctl -u astra.target --no-pager -n 10
EOF

chmod +x "$ASTRA_HOME/status_astra.sh"
chown "$ASTRA_USER:$ASTRA_GROUP" "$ASTRA_HOME/status_astra.sh"

echo -e "${GREEN}✅ Management scripts created${NC}"

# Final instructions
echo -e "${BLUE}🎉 Team Omega Project Astra Services Deployment Complete!${NC}"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Edit $ASTRA_HOME/companion/.env with your configuration"
echo "2. Run: $ASTRA_HOME/start_astra.sh"
echo "3. Check status: $ASTRA_HOME/status_astra.sh"
echo "4. View logs: journalctl -u astra.target -f"
echo ""
echo -e "${YELLOW}🔧 Management Commands:${NC}"
echo "• Start: systemctl start astra.target"
echo "• Stop: systemctl stop astra.target"
echo "• Status: systemctl status astra.target"
echo "• Enable: systemctl enable astra.target"
echo "• Disable: systemctl disable astra.target"
echo ""
echo -e "${YELLOW}📁 Important Directories:${NC}"
echo "• Services: $SERVICE_DIR"
echo "• Logs: $LOG_DIR"
echo "• Code: $ASTRA_HOME"
echo "• Environment: $ASTRA_HOME/companion/.env"
echo ""
echo -e "${GREEN}✅ Ready to launch! 🚀${NC}"
