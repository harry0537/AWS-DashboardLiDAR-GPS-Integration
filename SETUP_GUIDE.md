# 🚀 AWS Dashboard Sensor Setup Guide
## Complete Step-by-Step Instructions for Raspberry Pi Ubuntu

This guide provides detailed, step-by-step instructions to set up the AWS Dashboard sensors on your Ubuntu Raspberry Pi. Follow each step carefully to ensure successful sensor integration.

---

## 📋 **Prerequisites Checklist**

Before starting, ensure you have:

- [ ] **Hardware**: Raspberry Pi 4/5 with Ubuntu Server 22.04+
- [ ] **Storage**: 16GB+ SD card with Ubuntu installed
- [ ] **Power**: Stable 5V/3A power supply
- [ ] **Network**: Ethernet cable or WiFi connection
- [ ] **Sensors**: GPS module (simpleRTK2B) and LiDAR (RPLIDAR)
- [ ] **USB Cables**: High-quality USB cables for sensors
- [ ] **Internet**: Active internet connection for package installation

---

## 🔧 **Phase 1: System Preparation**

### **Step 1.1: Initial System Setup**
```bash
# 1. Boot your Raspberry Pi and connect via SSH or terminal
ssh ubuntu@<your-pi-ip>

# 2. Update system packages
sudo apt update
sudo apt upgrade -y

# 3. Install essential system tools
sudo apt install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    tree
```

### **Step 1.2: Install System Dependencies**
```bash
# Install Python and development tools
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential

# Install USB and serial communication libraries
sudo apt install -y \
    libudev-dev \
    libusb-1.0-0-dev \
    pkg-config \
    cmake

# Install serial communication tools
sudo apt install -y \
    minicom \
    screen \
    ttyd \
    usbutils
```

### **Step 1.3: Verify Python Installation**
```bash
# Check Python version (should be 3.8+)
python3 --version

# Check pip version
pip3 --version

# Verify virtual environment support
python3 -m venv --help
```

---

## 📁 **Phase 2: Project Setup**

### **Step 2.1: Clone Project Repository**
```bash
# Navigate to home directory
cd ~

# Clone the AWS Dashboard project
git clone <your-repository-url> AWS-Dashboard

# Navigate into project directory
cd AWS-Dashboard

# List project contents
ls -la
```

### **Step 2.2: Create Python Virtual Environment**
```bash
# Create virtual environment
python3 -m venv ~/aws_dashboard_env

# Activate virtual environment
source ~/aws_dashboard_env/bin/activate

# Verify activation (should show path to venv)
which python

# Upgrade pip
pip install --upgrade pip
```

### **Step 2.3: Install Python Dependencies**
```bash
# Install core requirements
pip install -r requirements_rpi.txt

# Install additional sensor packages
pip install \
    pyserial \
    pynmea2 \
    rplidar-roboticia \
    boto3 \
    python-dotenv

# Verify installations
pip list | grep -E "(serial|nmea|rplidar|boto3|dotenv)"
```

---

## ⚙️ **Phase 3: Configuration Setup**

### **Step 3.1: Create Configuration Directory**
```bash
# Create configuration directory
mkdir -p ~/.aws_dashboard

# Navigate to config directory
cd ~/.aws_dashboard

# Verify directory creation
pwd
ls -la
```

### **Step 3.2: Create Environment Configuration File**
```bash
# Create .env file with default settings
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

# GPS Configuration (will be updated after device detection)
GPS_SERIAL_PORT=/dev/ttyUSB0
GPS_BAUD=115200

# LiDAR Configuration (will be updated after device detection)
RPLIDAR_PORT=/dev/ttyUSB1
RPLIDAR_BAUD=256000
EOF

# Verify file creation
cat .env
```

### **Step 3.3: Set File Permissions**
```bash
# Set proper permissions
chmod 600 .env

# Verify permissions
ls -la .env
```

---

## 🔌 **Phase 4: Hardware Connection**

### **Step 4.1: Connect GPS Module**
```bash
# 1. Connect GPS module to any USB port
# 2. Wait 5-10 seconds for system detection
# 3. Check if device is recognized
lsusb | grep -i gps

# List serial devices
ls -la /dev/ttyUSB*
```

### **Step 4.2: Connect LiDAR Module**
```bash
# 1. Connect LiDAR module to any USB port
# 2. Wait 5-10 seconds for system detection
# 3. Check if device is recognized
lsusb | grep -i lidar

# List all serial devices again
ls -la /dev/ttyUSB*
```

### **Step 4.3: Verify Device Detection**
```bash
# Get detailed device information
for device in /dev/ttyUSB*; do
    echo "=== Device: $device ==="
    udevadm info -a -n "$device" | grep -E "(idVendor|idProduct|serial)" | head -3
    echo ""
done
```

---

## 🔍 **Phase 5: Device Detection and Configuration**

### **Step 5.1: Run Device Detection Script**
```bash
# Navigate back to project directory
cd ~/AWS-Dashboard

# Make detection script executable
chmod +x setup_raspberry_pi.sh

# Run device detection
~/detect_usb_devices.sh
```

### **Step 5.2: Update Configuration with Detected Ports**
```bash
# Based on detection results, update .env file
nano ~/.aws_dashboard/.env

# Example of what to update:
# GPS_SERIAL_PORT=/dev/ttyUSB0  # or whatever port GPS is on
# RPLIDAR_PORT=/dev/ttyUSB1     # or whatever port LiDAR is on
```

### **Step 5.3: Test Individual Sensor Connections**
```bash
# Test GPS module
python test_sensors.py

# Or test GPS specifically
python -c "
import serial
import time
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
print('GPS connected successfully')
for i in range(5):
    if ser.in_waiting:
        data = ser.readline().decode('utf-8', errors='ignore').strip()
        if data.startswith('$'):
            print(f'GPS Data: {data}')
    time.sleep(1)
ser.close()
"
```

---

## 🗄️ **Phase 6: Database Setup**

### **Step 6.1: Create DynamoDB Tables**
```bash
# Ensure virtual environment is activated
source ~/aws_dashboard_env/bin/activate

# Create database tables
python scripts/create_dynamodb_table.py

# Verify table creation
python -c "
import boto3
from dotenv import load_dotenv
load_dotenv('~/.aws_dashboard/.env')

dynamodb = boto3.resource('dynamodb', 
                         region_name=os.getenv('AWS_REGION'), 
                         endpoint_url=os.getenv('DDB_ENDPOINT_URL'))

tables = list(dynamodb.tables.all())
print(f'Available tables: {[t.name for t in tables]}')
"
```

### **Step 6.2: Test Database Connectivity**
```bash
# Test database write operation
python -c "
import boto3
import time
from dotenv import load_dotenv
load_dotenv('~/.aws_dashboard/.env')

dynamodb = boto3.resource('dynamodb', 
                         region_name=os.getenv('AWS_REGION'), 
                         endpoint_url=os.getenv('DDB_ENDPOINT_URL'))

table = dynamodb.Table(os.getenv('DDB_TABLE_NAME'))
item = {
    'device_id': 'test-device',
    'timestamp': int(time.time()),
    'lat': 0.0,
    'lon': 0.0,
    'speed': 0.0,
    'heading': 0.0
}
table.put_item(Item=item)
print('Test data written successfully')
"
```

---

## 🚀 **Phase 7: Service Setup**

### **Step 7.1: Create Systemd Service Files**
```bash
# Create GPS service
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

# Create LiDAR service
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

# Create Dashboard API service
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
```

### **Step 7.2: Enable and Start Services**
```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable gps-sensor.service
sudo systemctl enable lidar-sensor.service
sudo systemctl enable dashboard-api.service

# Start services
sudo systemctl start gps-sensor.service
sudo systemctl start lidar-sensor.service
sudo systemctl start dashboard-api.service

# Check service status
sudo systemctl status gps-sensor.service
sudo systemctl status lidar-sensor.service
sudo systemctl status dashboard-api.service
```

---

## 🧪 **Phase 8: Testing and Validation**

### **Step 8.1: Run Comprehensive Sensor Test**
```bash
# Navigate to project directory
cd ~/AWS-Dashboard

# Activate virtual environment
source ~/aws_dashboard_env/bin/activate

# Run full sensor test
python test_sensors.py
```

### **Step 8.2: Test Individual Components**
```bash
# Test GPS data collection
python scripts/gps_to_dynamodb.py &
GPS_PID=$!

# Wait 10 seconds for data collection
sleep 10

# Stop GPS test
kill $GPS_PID

# Test LiDAR data collection
python scripts/rplidar_to_dynamodb.py &
LIDAR_PID=$!

# Wait 10 seconds for data collection
sleep 10

# Stop LiDAR test
kill $LIDAR_PID
```

### **Step 8.3: Verify Data in Database**
```bash
# Check if data was collected
python -c "
import boto3
import time
from dotenv import load_dotenv
load_dotenv('~/.aws_dashboard/.env')

dynamodb = boto3.resource('dynamodb', 
                         region_name=os.getenv('AWS_REGION'), 
                         endpoint_url=os.getenv('DDB_ENDPOINT_URL'))

# Check telemetry table
telem_table = dynamodb.Table(os.getenv('DDB_TABLE_NAME'))
telem_response = telem_table.scan(Limit=5)
print(f'Telemetry items: {len(telem_response.get(\"Items\", []))}')

# Check LiDAR table
lidar_table = dynamodb.Table(os.getenv('LIDAR_TABLE_NAME'))
lidar_response = lidar_table.scan(Limit=5)
print(f'LiDAR items: {len(lidar_response.get(\"Items\", []))}')
"
```

---

## 🌐 **Phase 9: Dashboard Access**

### **Step 9.1: Start Dashboard API**
```bash
# Ensure API service is running
sudo systemctl status dashboard-api.service

# If not running, start it
sudo systemctl start dashboard-api.service

# Check if API is responding
curl http://localhost:5000/api/telemetry/latest
```

### **Step 9.2: Access Dashboard**
```bash
# Get Pi's IP address
hostname -I

# Open dashboard in browser
# http://<PI_IP_ADDRESS>:5000
```

### **Step 9.3: Test Dashboard Functionality**
```bash
# Test API endpoints
curl http://localhost:5000/api/telemetry/latest | jq .
curl http://localhost:5000/api/lidar/latest | jq .

# Check if jq is installed, if not:
sudo apt install -y jq
```

---

## 📊 **Phase 10: Monitoring and Maintenance**

### **Step 10.1: Create Monitoring Scripts**
```bash
# Create quick status checker
cat > ~/check_status.sh << 'EOF'
#!/bin/bash
echo "=== AWS Dashboard Status ==="
echo "Services:"
sudo systemctl is-active gps-sensor.service
sudo systemctl is-active lidar-sensor.service
sudo systemctl is-active dashboard-api.service

echo "USB Devices:"
ls -la /dev/ttyUSB*

echo "API Status:"
curl -s http://localhost:5000/api/telemetry/latest | jq . 2>/dev/null || echo "API not responding"
EOF

chmod +x ~/check_status.sh
```

### **Step 10.2: Set Up Log Monitoring**
```bash
# Monitor GPS service logs
sudo journalctl -u gps-sensor.service -f

# Monitor LiDAR service logs
sudo journalctl -u lidar-sensor.service -f

# Monitor API service logs
sudo journalctl -u dashboard-api.service -f
```

### **Step 10.3: Create Startup Script**
```bash
# Create manual startup script
cat > ~/start_all.sh << 'EOF'
#!/bin/bash
echo "Starting AWS Dashboard services..."
sudo systemctl start gps-sensor.service
sudo systemctl start lidar-sensor.service
sudo systemctl start dashboard-api.service

echo "Services started. Check status with: ~/check_status.sh"
echo "Dashboard available at: http://$(hostname -I | awk '{print $1}'):5000"
EOF

chmod +x ~/start_all.sh
```

---

## ✅ **Verification Checklist**

After completing all phases, verify:

- [ ] **System Services**: All 3 services are running (`systemctl status`)
- [ ] **USB Devices**: Sensors are detected (`ls /dev/ttyUSB*`)
- [ ] **Database**: Tables exist and are accessible
- [ ] **API**: Dashboard responds to HTTP requests
- [ ] **Data Flow**: GPS and LiDAR data is being collected
- [ ] **Dashboard**: Web interface loads and shows data
- [ ] **Auto-start**: Services start automatically on reboot

---

## 🚨 **Troubleshooting Quick Reference**

### **Common Issues and Solutions:**

1. **USB Device Not Found**
   ```bash
   lsusb                    # Check USB devices
   dmesg | tail -20        # Check kernel messages
   sudo udevadm trigger    # Reload udev rules
   ```

2. **Permission Denied**
   ```bash
   sudo usermod -a -G dialout $USER  # Add to dialout group
   sudo chmod 666 /dev/ttyUSB*       # Set permissions
   # Logout and login again
   ```

3. **Service Won't Start**
   ```bash
   sudo journalctl -u <service-name> -f  # Check logs
   sudo systemctl status <service-name>   # Check status
   ```

4. **No GPS Data**
   ```bash
   sudo minicom -D /dev/ttyUSB0 -b 115200  # Test serial
   # Try different baud rates: 9600, 38400, 57600, 115200
   ```

5. **API Not Responding**
   ```bash
   curl http://localhost:5000/api/telemetry/latest  # Test endpoint
   sudo systemctl restart dashboard-api.service      # Restart service
   ```

---

## 🎯 **Next Steps After Setup**

1. **Field Testing**: Test sensors in real-world conditions
2. **Calibration**: Fine-tune GPS and LiDAR parameters
3. **Integration**: Connect to your autonomous vehicle
4. **Customization**: Modify dashboard for specific needs
5. **Production**: Deploy to production environment

---

## 📞 **Support and Resources**

- **Project Documentation**: Check the `docs/` folder
- **System Logs**: Use `journalctl` for service debugging
- **Device Testing**: Use `test_sensors.py` for comprehensive testing
- **Status Monitoring**: Use `check_sensor_status.py` for quick checks

---

**🎉 Congratulations! Your Raspberry Pi sensor system is now set up and ready for autonomous vehicle operations!**

For additional help, refer to the troubleshooting section or check the system logs for specific error messages. 