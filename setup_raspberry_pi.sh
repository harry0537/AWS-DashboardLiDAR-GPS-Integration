#!/bin/bash

# AWS Dashboard Sensor Setup for Raspberry Pi Ubuntu
# This script sets up the environment for GPS and LiDAR sensors

set -e

echo "🚀 Setting up AWS Dashboard Sensors on Raspberry Pi Ubuntu..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python and pip
echo "🐍 Installing Python and pip..."
sudo apt install -y python3 python3-pip python3-venv

# Install system dependencies for sensors
echo "🔧 Installing system dependencies..."
sudo apt install -y \
    build-essential \
    python3-dev \
    libudev-dev \
    libusb-1.0-0-dev \
    pkg-config \
    cmake \
    git \
    curl \
    wget

# Install serial communication tools
echo "📡 Installing serial communication tools..."
sudo apt install -y \
    minicom \
    screen \
    ttyd \
    usbutils

# Create virtual environment
echo "🏗️ Creating Python virtual environment..."
python3 -m venv ~/aws_dashboard_env
source ~/aws_dashboard_env/bin/activate

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install additional sensor-specific packages
echo "🔌 Installing sensor-specific packages..."
pip install \
    pyserial \
    pynmea2 \
    rplidar-roboticia \
    boto3 \
    python-dotenv

# Create configuration directory
echo "⚙️ Setting up configuration..."
mkdir -p ~/.aws_dashboard
cd ~/.aws_dashboard

# Create environment file
echo "📝 Creating environment configuration..."
cat > .env << 'EOF'
# AWS Configuration
AWS_REGION=us-west-2
DDB_ENDPOINT_URL=http://localhost:8000
DDB_TABLE_NAME=UGVTelemetry
LIDAR_TABLE_NAME=UGVLidarScans
DEVICE_ID=ugv-1

# Flask Configuration
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# GPS Configuration (will be auto-detected)
GPS_SERIAL_PORT=/dev/ttyUSB0
GPS_BAUD=115200

# LiDAR Configuration (will be auto-detected)
RPLIDAR_PORT=/dev/ttyUSB1
RPLIDAR_BAUD=256000
EOF

# Create systemd service files
echo "🔄 Creating systemd services..."

# GPS Service
sudo tee /etc/systemd/system/gps-sensor.service > /dev/null << 'EOF'
[Unit]
Description=GPS Sensor Bridge
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/AWS-Dashboard
Environment=PATH=/home/ubuntu/aws_dashboard_env/bin
ExecStart=/home/ubuntu/aws_dashboard_env/bin/python scripts/gps_to_dynamodb.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# LiDAR Service
sudo tee /etc/systemd/system/lidar-sensor.service > /dev/null << 'EOF'
[Unit]
Description=LiDAR Sensor Bridge
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/AWS-Dashboard
Environment=PATH=/home/ubuntu/aws_dashboard_env/bin
ExecStart=/home/ubuntu/aws_dashboard_env/bin/python scripts/rplidar_to_dynamodb.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Dashboard API Service
sudo tee /etc/systemd/system/dashboard-api.service > /dev/null << 'EOF'
[Unit]
Description=AWS Dashboard API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/AWS-Dashboard
Environment=PATH=/home/ubuntu/aws_dashboard_env/bin
ExecStart=/home/ubuntu/aws_dashboard_env/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable services
echo "🔄 Enabling systemd services..."
sudo systemctl daemon-reload
sudo systemctl enable gps-sensor.service
sudo systemctl enable lidar-sensor.service
sudo systemctl enable dashboard-api.service

# Create USB device detection script
echo "🔍 Creating USB device detection script..."
cat > ~/detect_usb_devices.sh << 'EOF'
#!/bin/bash

echo "🔍 Detecting USB devices..."
echo "================================"

# List all USB devices
echo "📱 All USB devices:"
lsusb

echo ""
echo "🔌 Serial devices:"
ls -la /dev/ttyUSB* 2>/dev/null || echo "No USB serial devices found"

echo ""
echo "📡 Available serial ports:"
ls -la /dev/tty* | grep -E "(ttyUSB|ttyACM|ttyAMA)" || echo "No serial ports found"

echo ""
echo "🔧 Device details:"
for device in /dev/ttyUSB* /dev/ttyACM*; do
    if [ -e "$device" ]; then
        echo "Device: $device"
        udevadm info -a -n "$device" | grep -E "(idVendor|idProduct|serial)" | head -3
        echo "---"
    fi
done

echo ""
echo "💡 To find your specific devices:"
echo "1. Connect your GPS module and run: ls /dev/ttyUSB*"
echo "2. Connect your LiDAR and run: ls /dev/ttyUSB*"
echo "3. Update the .env file with the correct ports"
EOF

chmod +x ~/detect_usb_devices.sh

# Create udev rules for persistent device naming
echo "📋 Creating udev rules for persistent device naming..."
sudo tee /etc/udev/rules.d/99-sensors.rules > /dev/null << 'EOF'
# GPS Module (simpleRTK2B) - adjust vendor/product IDs as needed
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", SYMLINK+="gps_module"
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="gps_module"

# LiDAR (RPLIDAR) - adjust vendor/product IDs as needed
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="lidar_module"
SUBSYSTEM=="tty", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="5740", SYMLINK+="lidar_module"

# Make devices accessible to ubuntu user
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", MODE="0666"
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", MODE="0666"
SUBSYSTEM=="tty", ATTRS{idVendor}=="0483", MODE="0666"
EOF

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Create startup script
echo "🚀 Creating startup script..."
cat > ~/start_sensors.sh << 'EOF'
#!/bin/bash

echo "🚀 Starting AWS Dashboard Sensors..."

# Activate virtual environment
source ~/aws_dashboard_env/bin/activate

# Change to project directory
cd ~/AWS-Dashboard

# Check if DynamoDB tables exist, create if not
echo "📊 Checking DynamoDB tables..."
python scripts/create_dynamodb_table.py

# Start sensor bridges in background
echo "📡 Starting GPS sensor bridge..."
python scripts/gps_to_dynamodb.py &
GPS_PID=$!

echo "🔍 Starting LiDAR sensor bridge..."
python scripts/rplidar_to_dynamodb.py &
LIDAR_PID=$!

# Start dashboard API
echo "🌐 Starting dashboard API..."
python app.py &
API_PID=$!

echo "✅ All services started!"
echo "GPS PID: $GPS_PID"
echo "LiDAR PID: $LIDAR_PID"
echo "API PID: $API_PID"
echo ""
echo "📊 Dashboard available at: http://$(hostname -I | awk '{print $1}'):5000"
echo "🔍 To stop all services, run: pkill -f 'python.*scripts/' && pkill -f 'python.*app.py'"

# Wait for user interrupt
trap "echo '🛑 Stopping services...'; kill $GPS_PID $LIDAR_PID $API_PID; exit" INT
wait
EOF

chmod +x ~/start_sensors.sh

# Create monitoring script
echo "📊 Creating monitoring script..."
cat > ~/monitor_sensors.sh << 'EOF'
#!/bin/bash

echo "📊 Monitoring AWS Dashboard Sensors..."
echo "======================================"

# Check service status
echo "🔍 Service Status:"
sudo systemctl status gps-sensor.service --no-pager -l
echo ""
sudo systemctl status lidar-sensor.service --no-pager -l
echo ""
sudo systemctl status dashboard-api.service --no-pager -l

echo ""
echo "📡 USB Device Status:"
ls -la /dev/ttyUSB* 2>/dev/null || echo "No USB serial devices found"

echo ""
echo "🌐 API Status:"
curl -s http://localhost:5000/api/telemetry/latest | jq . 2>/dev/null || echo "API not responding"

echo ""
echo "📊 DynamoDB Status:"
python3 -c "
import boto3
import os
from dotenv import load_dotenv
load_dotenv('~/.aws_dashboard/.env')

try:
    dynamodb = boto3.resource('dynamodb', 
                             region_name=os.getenv('AWS_REGION'), 
                             endpoint_url=os.getenv('DDB_ENDPOINT_URL'))
    table = dynamodb.Table(os.getenv('DDB_TABLE_NAME'))
    response = table.scan(Limit=1)
    print(f'Telemetry table accessible: {len(response.get(\"Items\", []))} items')
except Exception as e:
    print(f'DynamoDB error: {e}')
"
EOF

chmod +x ~/monitor_sensors.sh

echo ""
echo "✅ Setup complete! Here's what to do next:"
echo ""
echo "1. 🔌 Connect your sensors via USB"
echo "2. 🔍 Run device detection: ~/detect_usb_devices.sh"
echo "3. ⚙️ Update ~/.aws_dashboard/.env with correct device ports"
echo "4. 🚀 Start sensors: ~/start_sensors.sh"
echo "5. 📊 Monitor status: ~/monitor_sensors.sh"
echo ""
echo "📱 Dashboard will be available at: http://$(hostname -I | awk '{print $1}'):5000"
echo "🔧 Services will auto-start on boot"
echo ""
echo "💡 For troubleshooting, check:"
echo "   - sudo journalctl -u gps-sensor.service -f"
echo "   - sudo journalctl -u lidar-sensor.service -f"
echo "   - sudo journalctl -u dashboard-api.service -f" 