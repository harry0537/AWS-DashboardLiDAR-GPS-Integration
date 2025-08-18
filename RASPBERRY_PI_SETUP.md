# 🍓 Raspberry Pi Ubuntu Sensor Setup Guide

This guide will help you set up the AWS Dashboard sensors on your Ubuntu Raspberry Pi with USB-connected GPS and LiDAR modules.

## 📋 Prerequisites

- **Hardware**: Raspberry Pi 4/5 with Ubuntu Server 22.04+
- **Storage**: At least 16GB SD card
- **Power**: Stable 5V/3A power supply
- **Network**: Ethernet or WiFi connection
- **Sensors**: 
  - GPS Module (simpleRTK2B or similar)
  - LiDAR Module (RPLIDAR A1/A2 or similar)

## 🚀 Quick Setup (Automated)

### Step 1: Clone and Setup
```bash
# Clone the project
cd ~
git clone <your-repo-url> AWS-Dashboard
cd AWS-Dashboard

# Make setup script executable
chmod +x setup_raspberry_pi.sh

# Run the automated setup
./setup_raspberry_pi.sh
```

### Step 2: Connect Sensors
1. **GPS Module**: Connect via USB to any USB port
2. **LiDAR Module**: Connect via USB to any USB port
3. **Power**: Ensure stable power supply

### Step 3: Detect Devices
```bash
# Run device detection
~/detect_usb_devices.sh

# Update configuration if needed
nano ~/.aws_dashboard/.env
```

### Step 4: Test Sensors
```bash
# Run comprehensive sensor test
python test_sensors.py

# Or test individual components
python scripts/gps_to_dynamodb.py  # Test GPS
python scripts/rplidar_to_dynamodb.py  # Test LiDAR
```

### Step 5: Start Services
```bash
# Start all services manually
~/start_sensors.sh

# Or start systemd services
sudo systemctl start gps-sensor.service
sudo systemctl start lidar-sensor.service
sudo systemctl start dashboard-api.service
```

## 🔧 Manual Setup (Step-by-Step)

### 1. System Preparation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y \
    python3 python3-pip python3-venv \
    build-essential python3-dev \
    libudev-dev libusb-1.0-0-dev \
    pkg-config cmake git curl wget \
    minicom screen ttyd usbutils
```

### 2. Python Environment
```bash
# Create virtual environment
python3 -m venv ~/aws_dashboard_env
source ~/aws_dashboard_env/bin/activate

# Install packages
pip install --upgrade pip
pip install -r requirements_rpi.txt
```

### 3. USB Device Configuration
```bash
# Check USB devices
lsusb

# List serial ports
ls -la /dev/ttyUSB*

# Get device details
udevadm info -a -n /dev/ttyUSB0
```

### 4. Environment Configuration
```bash
# Create config directory
mkdir -p ~/.aws_dashboard

# Create .env file
cat > ~/.aws_dashboard/.env << 'EOF'
AWS_REGION=us-west-2
DDB_ENDPOINT_URL=http://localhost:8000
DDB_TABLE_NAME=UGVTelemetry
LIDAR_TABLE_NAME=UGVLidarScans
DEVICE_ID=ugv-1

FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# Update these with your actual device ports
GPS_SERIAL_PORT=/dev/ttyUSB0
GPS_BAUD=115200
RPLIDAR_PORT=/dev/ttyUSB1
RPLIDAR_BAUD=256000
EOF
```

## 🔍 Troubleshooting

### Common Issues

#### 1. USB Device Not Found
```bash
# Check USB connections
lsusb

# Check kernel messages
dmesg | tail -20

# Check udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

#### 2. Permission Denied
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER

# Set device permissions
sudo chmod 666 /dev/ttyUSB*

# Logout and login again
```

#### 3. GPS No Data
```bash
# Check baud rate
sudo minicom -D /dev/ttyUSB0 -b 115200

# Test with different baud rates: 9600, 38400, 57600, 115200
```

#### 4. LiDAR Not Responding
```bash
# Check power supply (LiDAR needs stable 5V)
# Check USB cable quality
# Try different USB ports
```

### Debug Commands
```bash
# Monitor system logs
sudo journalctl -u gps-sensor.service -f
sudo journalctl -u lidar-sensor.service -f
sudo journalctl -u dashboard-api.service -f

# Check device status
ls -la /dev/ttyUSB*
udevadm info -a -n /dev/ttyUSB0

# Test serial communication
sudo minicom -D /dev/ttyUSB0 -b 115200
```

## 📊 Monitoring and Testing

### Real-time Monitoring
```bash
# Monitor all services
~/monitor_sensors.sh

# Check individual service status
sudo systemctl status gps-sensor.service
sudo systemctl status lidar-sensor.service
sudo systemctl status dashboard-api.service
```

### Data Verification
```bash
# Check DynamoDB tables
python scripts/create_dynamodb_table.py

# Test API endpoints
curl http://localhost:5000/api/telemetry/latest
curl http://localhost:5000/api/lidar/latest
```

### Dashboard Access
```bash
# Get Pi's IP address
hostname -I

# Access dashboard
# http://<PI_IP>:5000
```

## 🔄 Auto-start Configuration

### Enable Services on Boot
```bash
# Enable all services
sudo systemctl enable gps-sensor.service
sudo systemctl enable lidar-sensor.service
sudo systemctl enable dashboard-api.service

# Check enabled status
sudo systemctl is-enabled gps-sensor.service
```

### Manual Start/Stop
```bash
# Start all services
sudo systemctl start gps-sensor.service
sudo systemctl start lidar-sensor.service
sudo systemctl start dashboard-api.service

# Stop all services
sudo systemctl stop gps-sensor.service
sudo systemctl stop lidar-sensor.service
sudo systemctl stop dashboard-api.service

# Restart all services
sudo systemctl restart gps-sensor.service
sudo systemctl restart lidar-sensor.service
sudo systemctl restart dashboard-api.service
```

## 📱 Dashboard Features

Once running, your dashboard will show:

- **Real-time GPS**: Current position, speed, heading, accuracy
- **LiDAR Data**: Distance measurements and obstacle detection
- **Live Updates**: 2-second refresh rate
- **Interactive Map**: Leaflet-based mapping with vehicle tracking
- **Control Panel**: Manual controls and system status

## 🎯 Next Steps

1. **Field Testing**: Test sensors in real-world conditions
2. **Calibration**: Fine-tune GPS and LiDAR parameters
3. **Integration**: Connect to your autonomous vehicle
4. **Customization**: Modify dashboard for your specific needs
5. **Deployment**: Move to production environment

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review system logs: `sudo journalctl -u <service-name> -f`
3. Test individual components with the test scripts
4. Verify USB connections and power supply
5. Check device compatibility and drivers

---

**Happy Sensor Integration! 🚀** 