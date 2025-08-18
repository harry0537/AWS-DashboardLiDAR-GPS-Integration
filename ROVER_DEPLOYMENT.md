# 🚗 Rover Host Machine Deployment Guide
## Deploying AWS Dashboard Sensors on Your Autonomous Vehicle

This guide walks you through deploying the sensor automation scripts directly on your rover's host machine (Raspberry Pi Ubuntu) to enable real-time sensor data collection and dashboard monitoring.

---

## 🎯 **Deployment Overview**

**What We're Deploying:**
- GPS sensor bridge (simpleRTK2B)
- LiDAR sensor bridge (RPLIDAR)
- Dashboard API server
- Auto-starting system services
- Real-time data collection

**Expected Result:**
- Rover continuously collects GPS and LiDAR data
- Data streams to AWS DynamoDB in real-time
- Live dashboard shows rover position and sensor readings
- Services auto-restart on failures or reboots

---

## 🚀 **Phase 1: Prepare Rover Host Machine**

### **Step 1.1: Access Rover Host Machine**
```bash
# Option A: Direct connection (if you have monitor/keyboard)
# Boot the Raspberry Pi and login as 'ubuntu'

# Option B: SSH connection (recommended)
ssh ubuntu@<ROVER_IP_ADDRESS>

# Option C: Serial connection (if SSH not working)
sudo minicom -D /dev/ttyAMA0 -b 115200
```

### **Step 1.2: Verify System Status**
```bash
# Check system information
uname -a
cat /etc/os-release
df -h
free -h

# Check network connectivity
ip addr show
ping -c 3 google.com

# Check USB ports
lsusb
ls -la /dev/ttyUSB*
```

### **Step 1.3: Update System (if needed)**
```bash
# Update package lists
sudo apt update

# Check for available updates
sudo apt list --upgradable

# Install updates (optional, but recommended)
sudo apt upgrade -y
```

---

## 📁 **Phase 2: Deploy Project Files**

### **Step 2.1: Transfer Project to Rover**
```bash
# Option A: Clone from Git (if you have repository access)
cd ~
git clone <your-repo-url> AWS-Dashboard
cd AWS-Dashboard

# Option B: Transfer via SCP (from your development machine)
# On your dev machine, run:
# scp -r AWS-Dashboard ubuntu@<ROVER_IP>:~/

# Option C: Transfer via USB drive
# Copy files to USB, mount on rover, then copy to home directory
sudo mount /dev/sda1 /mnt/usb
cp -r /mnt/usb/AWS-Dashboard ~/
sudo umount /mnt/usb
```

### **Step 2.2: Verify Project Structure**
```bash
# Navigate to project directory
cd ~/AWS-Dashboard

# List all files
ls -la

# Verify key files exist
ls -la setup_raspberry_pi.sh
ls -la test_sensors.py
ls -la scripts/
ls -la requirements_rpi.txt
```

### **Step 2.3: Set Proper Permissions**
```bash
# Make scripts executable
chmod +x setup_raspberry_pi.sh
chmod +x scripts/*.py
chmod +x test_sensors.py
chmod +x check_sensor_status.py

# Verify permissions
ls -la *.sh *.py
ls -la scripts/
```

---

## 🔧 **Phase 3: Automated Setup Execution**

### **Step 3.1: Run the Main Setup Script**
```bash
# Navigate to project directory
cd ~/AWS-Dashboard

# Execute the automated setup
./setup_raspberry_pi.sh
```

**What the script does automatically:**
- ✅ Installs system dependencies
- ✅ Creates Python virtual environment
- ✅ Installs Python packages
- ✅ Creates configuration files
- ✅ Sets up systemd services
- ✅ Creates monitoring scripts

### **Step 3.2: Monitor Setup Progress**
```bash
# Watch the setup process
# The script will show progress with emojis and status messages

# If you need to see detailed output, you can redirect to a log file:
./setup_raspberry_pi.sh 2>&1 | tee setup_log.txt

# Monitor the log in real-time
tail -f setup_log.txt
```

### **Step 3.3: Handle Any Setup Errors**
```bash
# If setup fails, check the log
cat setup_log.txt

# Common fixes:
# - Insufficient disk space: df -h
# - Network issues: ping google.com
# - Permission issues: sudo chown -R ubuntu:ubuntu ~/AWS-Dashboard

# Re-run setup after fixing issues
./setup_raspberry_pi.sh
```

---

## 🔌 **Phase 4: Connect Sensors to Rover**

### **Step 4.1: Physical Sensor Connection**
```bash
# 1. Connect GPS module (simpleRTK2B) to any USB port
# 2. Connect LiDAR module (RPLIDAR) to any USB port
# 3. Ensure stable power supply (LiDAR needs good 5V)
# 4. Wait 10-15 seconds for system detection

# Verify connections
lsusb
ls -la /dev/ttyUSB*
```

### **Step 4.2: Detect Connected Sensors**
```bash
# Run device detection script
~/detect_usb_devices.sh

# This will show:
# - All USB devices
# - Serial port assignments
# - Vendor/Product IDs
# - Device details
```

### **Step 4.3: Update Configuration with Detected Ports**
```bash
# Edit the environment configuration
nano ~/.aws_dashboard/.env

# Update these lines with your actual device ports:
# GPS_SERIAL_PORT=/dev/ttyUSB0  # or whatever port GPS is on
# RPLIDAR_PORT=/dev/ttyUSB1     # or whatever port LiDAR is on

# Save and exit (Ctrl+X, Y, Enter)
```

---

## 🧪 **Phase 5: Test Sensor Integration**

### **Step 5.1: Run Comprehensive Sensor Test**
```bash
# Navigate to project directory
cd ~/AWS-Dashboard

# Activate virtual environment
source ~/aws_dashboard_env/bin/activate

# Run full sensor test
python test_sensors.py
```

**Expected Output:**
```
🚀 AWS Dashboard Sensor Testing for Raspberry Pi
==================================================
🔍 Available Serial Ports:
============================
🔌 /dev/ttyUSB0 (Vendor: 0403, Product: 6001)
🔌 /dev/ttyUSB1 (Vendor: 10c4, Product: ea60)

🔍 Testing DynamoDB Connection...
🌐 Connecting to DynamoDB at http://localhost:8000 in us-west-2
✅ DynamoDB connection successful! Found 2 tables

🔍 Testing GPS Module on /dev/ttyUSB0...
📡 Listening for NMEA data (10 seconds)...
📡 Received: $GPGGA,123456.789,1234.5678,N,12345.6789,W,1,08,1.2,123.4,M,0.0,M,,
✅ GPS module working! Received 5 NMEA sentences

🔍 Testing LiDAR Module on /dev/ttyUSB1...
📡 LiDAR responded with 12 bytes
✅ LiDAR module working!

📊 Test Summary:
==============================
🔌 Serial Ports: ✅ (2 found)
🌐 DynamoDB: ✅
📡 GPS Module: ✅
🔍 LiDAR Module: ✅

🎉 All tests passed! Your sensors are ready to use.
```

### **Step 5.2: Test Individual Components**
```bash
# Test GPS data collection (run for 30 seconds)
python scripts/gps_to_dynamodb.py &
GPS_PID=$!
sleep 30
kill $GPS_PID

# Test LiDAR data collection (run for 30 seconds)
python scripts/rplidar_to_dynamodb.py &
LIDAR_PID=$!
sleep 30
kill $LIDAR_PID

# Check if data was collected
python -c "
import boto3
from dotenv import load_dotenv
load_dotenv('~/.aws_dashboard/.env')

dynamodb = boto3.resource('dynamodb', 
                         region_name=os.getenv('AWS_REGION'), 
                         endpoint_url=os.getenv('DDB_ENDPOINT_URL'))

telem_table = dynamodb.Table(os.getenv('DDB_TABLE_NAME'))
telem_response = telem_table.scan(Limit=5)
print(f'GPS telemetry items: {len(telem_response.get(\"Items\", []))}')

lidar_table = dynamodb.Table(os.getenv('LIDAR_TABLE_NAME'))
lidar_response = lidar_table.scan(Limit=5)
print(f'LiDAR items: {len(lidar_response.get(\"Items\", []))}')
"
```

---

## 🚀 **Phase 6: Start Production Services**

### **Step 6.1: Start All Services**
```bash
# Start all services using the startup script
~/start_sensors.sh
```

**Expected Output:**
```
🚀 Starting AWS Dashboard Sensors...
📊 Checking DynamoDB tables...
📡 Starting GPS sensor bridge...
🔍 Starting LiDAR sensor bridge...
🌐 Starting dashboard API...
✅ All services started!
GPS PID: 12345
LiDAR PID: 12346
API PID: 12347

📊 Dashboard available at: http://192.168.1.100:5000
🔍 To stop all services, run: pkill -f 'python.*scripts/' && pkill -f 'python.*app.py'
```

### **Step 6.2: Verify Services Are Running**
```bash
# Check service status
sudo systemctl status gps-sensor.service
sudo systemctl status lidar-sensor.service
sudo systemctl status dashboard-api.service

# Check if processes are running
ps aux | grep python
ps aux | grep -E "(gps|lidar|app.py)"
```

### **Step 6.3: Test API Endpoints**
```bash
# Test telemetry endpoint
curl http://localhost:5000/api/telemetry/latest

# Test LiDAR endpoint
curl http://localhost:5000/api/lidar/latest

# Test with pretty formatting (if jq is installed)
curl http://localhost:5000/api/telemetry/latest | jq .
```

---

## 🌐 **Phase 7: Access Dashboard from Rover**

### **Step 7.1: Get Rover's Network Information**
```bash
# Get IP address
hostname -I

# Get network interface details
ip addr show

# Check if firewall allows port 5000
sudo ufw status
```

### **Step 7.2: Access Dashboard Locally**
```bash
# If you have a display on the rover:
# Open browser and go to: http://localhost:5000

# If accessing via SSH with X11 forwarding:
ssh -X ubuntu@<ROVER_IP>
firefox http://localhost:5000
```

### **Step 7.3: Access Dashboard from Network**
```bash
# From any device on the same network:
# http://<ROVER_IP_ADDRESS>:5000

# Example: http://192.168.1.100:5000
```

---

## 📊 **Phase 8: Monitor and Validate**

### **Step 8.1: Real-time Monitoring**
```bash
# Monitor all services
~/monitor_sensors.sh

# Or check individual components
python check_sensor_status.py
```

### **Step 8.2: Monitor Service Logs**
```bash
# Monitor GPS service logs
sudo journalctl -u gps-sensor.service -f

# Monitor LiDAR service logs
sudo journalctl -u lidar-sensor.service -f

# Monitor API service logs
sudo journalctl -u dashboard-api.service -f
```

### **Step 8.3: Verify Data Collection**
```bash
# Check data in DynamoDB
python -c "
import boto3
import time
from dotenv import load_dotenv
load_dotenv('~/.aws_dashboard/.env')

dynamodb = boto3.resource('dynamodb', 
                         region_name=os.getenv('AWS_REGION'), 
                         endpoint_url=os.getenv('DDB_ENDPOINT_URL'))

# Check recent telemetry
telem_table = dynamodb.Table(os.getenv('DDB_TABLE_NAME'))
telem_response = telem_table.scan(Limit=10)
items = telem_response.get('Items', [])
print(f'Recent telemetry items: {len(items)}')
if items:
    latest = max(items, key=lambda x: x['timestamp'])
    print(f'Latest GPS: {latest.get(\"lat\")}, {latest.get(\"lon\")}')
    print(f'Latest speed: {latest.get(\"speed\")} km/h')
    print(f'Latest accuracy: {latest.get(\"gps_accuracy_hdop\")} HDOP')

# Check recent LiDAR data
lidar_table = dynamodb.Table(os.getenv('LIDAR_TABLE_NAME'))
lidar_response = lidar_table.scan(Limit=10)
lidar_items = lidar_response.get('Items', [])
print(f'Recent LiDAR items: {len(lidar_items)}')
"
```

---

## 🔄 **Phase 9: Enable Auto-start**

### **Step 9.1: Verify Services Are Enabled**
```bash
# Check if services are enabled for auto-start
sudo systemctl is-enabled gps-sensor.service
sudo systemctl is-enabled lidar-sensor.service
sudo systemctl is-enabled dashboard-api.service

# If any are disabled, enable them
sudo systemctl enable gps-sensor.service
sudo systemctl enable lidar-sensor.service
sudo systemctl enable dashboard-api.service
```

### **Step 9.2: Test Auto-start Functionality**
```bash
# Restart the rover (if you have physical access)
sudo reboot

# After reboot, check if services started automatically
ssh ubuntu@<ROVER_IP>
sudo systemctl status gps-sensor.service
sudo systemctl status lidar-sensor.service
sudo systemctl status dashboard-api.service

# Check if data is being collected
python check_sensor_status.py
```

---

## ✅ **Phase 10: Final Validation**

### **Step 10.1: Complete System Check**
```bash
# Run comprehensive status check
python check_sensor_status.py

# Expected output shows all systems operational
```

### **Step 10.2: Dashboard Verification**
```bash
# Access dashboard and verify:
# - GPS position is updating
# - Speed and heading are showing
# - LiDAR data is being collected
# - Map shows current position
```

### **Step 10.3: Data Flow Verification**
```bash
# Verify continuous data collection
# Run this every few minutes to see new data
python -c "
import boto3
import time
from dotenv import load_dotenv
load_dotenv('~/.aws_dashboard/.env')

dynamodb = boto3.resource('dynamodb', 
                         region_name=os.getenv('AWS_REGION'), 
                         endpoint_url=os.getenv('DDB_ENDPOINT_URL'))

telem_table = dynamodb.Table(os.getenv('DDB_TABLE_NAME'))
response = telem_table.scan(Limit=1)
if response.get('Items'):
    latest = response['Items'][0]
    print(f'Latest data: {time.ctime(latest[\"timestamp\"])}')
    print(f'Position: {latest.get(\"lat\")}, {latest.get(\"lon\")}')
"
```

---

## 🎯 **What You Now Have on Your Rover:**

✅ **Real-time GPS tracking** - Continuous position updates  
✅ **LiDAR obstacle detection** - Distance measurements and mapping  
✅ **Live dashboard** - Web interface accessible from any device  
✅ **Auto-starting services** - Survives reboots and failures  
✅ **Data persistence** - All sensor data stored in DynamoDB  
✅ **Professional monitoring** - Comprehensive logging and status checking  

---

## 🚨 **Troubleshooting on Rover:**

### **Common Rover-Specific Issues:**

1. **Power Issues**
   ```bash
   # Check power supply stability
   dmesg | grep -i voltage
   dmesg | grep -i power
   
   # LiDAR is sensitive to power fluctuations
   # Use stable 5V/3A power supply
   ```

2. **USB Connection Issues**
   ```bash
   # Check USB device stability
   lsusb
   ls -la /dev/ttyUSB*
   
   # Reconnect sensors if devices disappear
   ```

3. **Network Issues**
   ```bash
   # Check network connectivity
   ip addr show
   ping -c 3 google.com
   
   # Ensure port 5000 is accessible
   sudo ufw allow 5000
   ```

4. **Service Failures**
   ```bash
   # Check service logs
   sudo journalctl -u gps-sensor.service -f
   sudo journalctl -u lidar-sensor.service -f
   
   # Restart failed services
   sudo systemctl restart gps-sensor.service
   ```

---

## 🎉 **Congratulations!**

Your rover now has a **fully automated sensor system** that:

- **Collects GPS data** every second with centimeter accuracy
- **Processes LiDAR scans** for obstacle detection
- **Streams data to the cloud** in real-time
- **Provides live monitoring** via web dashboard
- **Auto-recovers** from failures and reboots
- **Operates independently** without manual intervention

**Next Steps:**
1. **Field test** your rover with the new sensor system
2. **Calibrate** GPS and LiDAR parameters for your environment
3. **Integrate** with your autonomous navigation system
4. **Customize** the dashboard for your specific needs

Your rover is now ready for **autonomous operations** with professional-grade sensor monitoring! 🚗✨ 