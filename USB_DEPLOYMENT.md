# 💾 USB Deployment Guide
## Copy Scripts to USB and Run on Rover Host Machine

Yes, you absolutely can copy the scripts to a USB drive and run them directly on the rover's host machine! This is often the most reliable method when you don't have network access.

---

## 🎯 **USB Deployment Overview**

**What We're Doing:**
1. **Copy scripts** to USB drive on your development machine
2. **Insert USB** into rover's Raspberry Pi
3. **Mount USB** and copy files to rover
4. **Run setup scripts** directly on the rover
5. **Remove USB** and let rover operate independently

**Advantages:**
- ✅ **No network required** - Works offline
- ✅ **Reliable transfer** - No connection issues
- ✅ **Fast deployment** - Direct file copy
- ✅ **Simple process** - Just copy and run
- ✅ **Portable** - Can deploy to multiple rovers

---

## 📁 **Phase 1: Prepare USB Drive on Development Machine**

### **Step 1.1: Format USB Drive**
```bash
# On your development machine (Windows/Mac/Linux)
# Format USB drive to FAT32 or exFAT for compatibility

# Windows: Right-click USB drive → Format → FAT32
# Mac: Disk Utility → Erase → MS-DOS (FAT)
# Linux: sudo mkfs.vfat /dev/sdX1
```

### **Step 1.2: Create Deployment Package**
```bash
# Navigate to your AWS-Dashboard project
cd AWS-Dashboard

# Create a clean deployment package (exclude unnecessary files)
tar -czf rover-usb-deployment.tar.gz \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='setup_log.txt' \
    --exclude='*.log' \
    --exclude='node_modules' \
    --exclude='.env' \
    .

# Verify package size
ls -lh rover-usb-deployment.tar.gz
```

### **Step 1.3: Create USB Installation Script**
```bash
# Create a simple installation script
cat > install-from-usb.sh << 'EOF'
#!/bin/bash
echo "🚀 USB Installation Script for Rover"
echo "====================================="
echo "Installing AWS Dashboard Sensor System..."
echo ""

# Check if we're in the right directory
if [ ! -f "setup_raspberry_pi.sh" ]; then
    echo "❌ Error: setup_raspberry_pi.sh not found!"
    echo "Please run this script from the AWS-Dashboard directory"
    exit 1
fi

# Make scripts executable
echo "🔧 Setting permissions..."
chmod +x setup_raspberry_pi.sh
chmod +x scripts/*.py
chmod +x test_sensors.py
chmod +x check_sensor_status.py

# Run the main setup
echo "🚀 Starting automated setup..."
./setup_raspberry_pi.sh

echo ""
echo "✅ Installation complete!"
echo "💡 Your rover is now ready with sensor automation!"
echo "🔍 Check status with: python check_sensor_status.py"
EOF

chmod +x install-from-usb.sh
```

### **Step 1.4: Copy Files to USB Drive**
```bash
# Mount USB drive (adjust path as needed)
# Linux: /media/username/USB_DRIVE
# Mac: /Volumes/USB_DRIVE
# Windows: Just copy to USB drive letter

# Copy deployment package and script
cp rover-usb-deployment.tar.gz /media/username/USB_DRIVE/
cp install-from-usb.sh /media/username/USB_DRIVE/

# Create a README file
cat > /media/username/USB_DRIVE/README.txt << 'EOF'
🚀 AWS Dashboard Rover Deployment

This USB drive contains the sensor automation system for your rover.

QUICK START:
1. Insert this USB into your rover's Raspberry Pi
2. Mount the USB drive
3. Copy files to rover: cp -r /media/usb/* ~/
4. Extract package: tar -xzf rover-usb-deployment.tar.gz
5. Run installer: cd AWS-Dashboard && ./install-from-usb.sh

FILES INCLUDED:
- rover-usb-deployment.tar.gz: Main deployment package
- install-from-usb.sh: Installation script
- README.txt: This file

After installation, remove USB and rover will operate independently.
EOF

# Safely eject USB drive
# Linux: sudo umount /media/username/USB_DRIVE
# Mac: Drag USB to trash
# Windows: Right-click USB → Eject
```

---

## 🔌 **Phase 2: Deploy on Rover Host Machine**

### **Step 2.1: Insert USB into Rover**
```bash
# 1. Insert USB drive into rover's Raspberry Pi
# 2. Wait 5-10 seconds for system detection
# 3. Check if USB is detected
lsusb
ls -la /media/
```

### **Step 2.2: Mount USB Drive**
```bash
# Check available USB devices
lsblk
fdisk -l

# Mount USB drive (adjust device name as needed)
sudo mkdir -p /media/usb
sudo mount /dev/sda1 /media/usb

# Verify mount
ls -la /media/usb
df -h /media/usb
```

### **Step 2.3: Copy Files to Rover**
```bash
# Copy all files from USB to rover
cp -r /media/usb/* ~/

# Verify files were copied
ls -la ~/
ls -la ~/rover-usb-deployment.tar.gz
ls -la ~/install-from-usb.sh
```

### **Step 2.4: Extract Deployment Package**
```bash
# Extract the deployment package
cd ~
tar -xzf rover-usb-deployment.tar.gz

# Verify extraction
ls -la ~/AWS-Dashboard/
ls -la ~/AWS-Dashboard/setup_raspberry_pi.sh
```

---

## 🚀 **Phase 3: Run Installation on Rover**

### **Step 3.1: Execute Installation Script**
```bash
# Navigate to project directory
cd ~/AWS-Dashboard

# Run the USB installation script
./install-from-usb.sh
```

**Expected Output:**
```
🚀 USB Installation Script for Rover
=====================================
Installing AWS Dashboard Sensor System...

🔧 Setting permissions...
🚀 Starting automated setup...
🚀 Setting up AWS Dashboard Sensors on Raspberry Pi Ubuntu...
📦 Updating system packages...
🐍 Installing Python and pip...
🔧 Installing system dependencies...
...
✅ Installation complete!
💡 Your rover is now ready with sensor automation!
🔍 Check status with: python check_sensor_status.py
```

### **Step 3.2: Monitor Installation Progress**
```bash
# If you want to see detailed output, you can redirect to a log file:
./install-from-usb.sh 2>&1 | tee usb_install_log.txt

# Monitor progress in real-time
tail -f usb_install_log.txt
```

### **Step 3.3: Handle Installation Errors**
```bash
# If installation fails, check the log
cat usb_install_log.txt

# Common fixes:
# - Insufficient disk space: df -h
# - Permission issues: sudo chown -R ubuntu:ubuntu ~/AWS-Dashboard
# - Network issues: ping google.com

# Re-run installation after fixing issues
./install-from-usb.sh
```

---

## 🔍 **Phase 4: Verify Installation**

### **Step 4.1: Check System Status**
```bash
# Quick status check
python check_sensor_status.py

# Expected output shows all systems operational
```

### **Step 4.2: Test Sensor Connectivity**
```bash
# Run comprehensive sensor test
python test_sensors.py

# This will test GPS, LiDAR, and database connectivity
```

### **Step 4.3: Verify Services Are Running**
```bash
# Check if systemd services are active
sudo systemctl status gps-sensor.service
sudo systemctl status lidar-sensor.service
sudo systemctl status dashboard-api.service

# Check if processes are running
ps aux | grep python
ps aux | grep -E "(gps|lidar|app.py)"
```

---

## 🌐 **Phase 5: Test Dashboard Access**

### **Step 5.1: Check API Status**
```bash
# Test if dashboard API is responding
curl http://localhost:5000/api/telemetry/latest

# Test LiDAR endpoint
curl http://localhost:5000/api/lidar/latest
```

### **Step 5.2: Access Dashboard**
```bash
# Get rover's IP address
hostname -I

# Dashboard will be available at:
# http://<ROVER_IP>:5000
```

### **Step 5.3: Verify Data Flow**
```bash
# Check if data is being collected
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

## 🔄 **Phase 6: Clean Up and Finalize**

### **Step 6.1: Unmount and Remove USB**
```bash
# Unmount USB drive
sudo umount /media/usb

# Remove USB drive from rover
# (Physically remove the USB drive)

# Verify USB is unmounted
ls -la /media/
```

### **Step 6.2: Test Auto-start Functionality**
```bash
# Verify services are enabled for auto-start
sudo systemctl is-enabled gps-sensor.service
sudo systemctl is-enabled lidar-sensor.service
sudo systemctl is-enabled dashboard-api.service

# Test reboot (if you have access)
sudo reboot

# After reboot, check if services started automatically
python check_sensor_status.py
```

### **Step 6.3: Final Verification**
```bash
# Complete system check
python check_sensor_status.py

# Expected result: All systems operational
```

---

## 📋 **USB Deployment Checklist**

### **On Development Machine:**
- [ ] **Format USB drive** to FAT32/exFAT
- [ ] **Create deployment package** (exclude unnecessary files)
- [ ] **Create installation script** with proper permissions
- [ ] **Copy files to USB** and safely eject
- [ ] **Test USB** on another machine if possible

### **On Rover Host Machine:**
- [ ] **Insert USB drive** and wait for detection
- [ ] **Mount USB drive** and copy files
- [ ] **Extract deployment package** to rover
- [ ] **Run installation script** and monitor progress
- [ ] **Handle any errors** and re-run if needed
- [ ] **Verify installation** with status checks
- [ ] **Test dashboard access** and data flow
- [ ] **Unmount USB** and remove drive
- [ ] **Test auto-start** functionality

---

## 🚨 **Troubleshooting USB Deployment**

### **Common Issues:**

1. **USB Not Detected**
   ```bash
   # Check USB devices
   lsusb
   dmesg | tail -20
   
   # Try different USB ports
   # Check USB drive format (FAT32/exFAT recommended)
   ```

2. **Permission Denied**
   ```bash
   # Fix file permissions
   sudo chown -R ubuntu:ubuntu ~/AWS-Dashboard
   chmod +x ~/AWS-Dashboard/*.sh
   chmod +x ~/AWS-Dashboard/scripts/*.py
   ```

3. **Installation Fails**
   ```bash
   # Check installation log
   cat usb_install_log.txt
   
   # Verify disk space
   df -h
   
   # Check network connectivity
   ping google.com
   ```

4. **Services Won't Start**
   ```bash
   # Check service logs
   sudo journalctl -u gps-sensor.service -f
   sudo journalctl -u lidar-sensor.service -f
   
   # Verify configuration
   cat ~/.aws_dashboard/.env
   ```

---

## 💡 **USB Deployment Pro Tips**

1. **Use high-quality USB drives** - More reliable for large transfers
2. **Format to FAT32/exFAT** - Best compatibility with Raspberry Pi
3. **Test USB on another machine** - Ensure files are accessible
4. **Keep USB as backup** - Don't delete until deployment is verified
5. **Use multiple USBs** - Deploy to multiple rovers simultaneously

---

## 🎯 **What You Achieve with USB Deployment:**

✅ **Offline deployment** - No network required  
✅ **Reliable transfer** - Direct file copy, no connection issues  
✅ **Fast setup** - Complete installation in minutes  
✅ **Portable** - Can deploy to multiple rovers  
✅ **Independent operation** - Rover works without USB after installation  
✅ **Professional automation** - Full sensor system with auto-start  

---

## 🎉 **Success Indicators:**

Your USB deployment is successful when:
- ✅ **Files transfer** completely from USB to rover
- ✅ **Installation script** runs without errors
- ✅ **All services start** automatically
- ✅ **Sensors connect** and provide data
- ✅ **Dashboard responds** to web requests
- ✅ **USB can be removed** and rover operates independently
- ✅ **Services auto-start** after reboot

---

**🚀 USB deployment is often the most reliable method! Just copy, insert, and run!**

This approach eliminates network issues and gives you direct control over the deployment process on the rover itself. 