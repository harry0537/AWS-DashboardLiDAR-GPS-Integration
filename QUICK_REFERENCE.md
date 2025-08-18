# 🚀 Team Omega Project Astra - Quick Reference

**Essential Commands and Information for Your Autonomous Rover Project**

---

## 🎯 **Project Overview**

**Team Omega Project Astra** is a complete autonomous rover system with:
- **Enhanced Telemetry**: Rich data uplink to EC2 dashboard
- **Multi-Sensor Fusion**: LiDAR, GPS, camera, ultrasonic integration
- **Real-time Dashboard**: Beautiful web interface with maps
- **Production Services**: Systemd-managed with proper logging

---

## 📋 **Quick Start Commands**

### **EC2 Deployment**
```bash
# SSH to EC2
ssh -i your-key.pem ubuntu@your-ec2-ip

# Deploy everything automatically
git clone https://github.com/harry0537/AWS-DashboardLiDAR-GPS-Integration.git
cd AWS-DashboardLiDAR-GPS-Integration
bash cloud/deploy.sh

# Check status
/home/ubuntu/astra/status.sh

# Manage services
/home/ubuntu/astra/manage.sh {start|stop|restart|status|logs}
```

### **NUC Companion Setup**
```bash
# SSH to NUC
ssh astra@your-nuc-ip

# Deploy services
git clone https://github.com/harry0537/AWS-DashboardLiDAR-GPS-Integration.git
cd AWS-DashboardLiDAR-GPS-Integration
sudo bash ops/deploy/setup_astra_services.sh

# Start all services
sudo systemctl start astra.target

# Check status
sudo systemctl status astra.target
```

---

## 🔧 **Essential Commands**

### **Service Management**
```bash
# Start all Astra services
sudo systemctl start astra.target

# Stop all services
sudo systemctl stop astra.target

# Restart services
sudo systemctl restart astra.target

# Check status
sudo systemctl status astra.target

# View logs
journalctl -u astra.target -f
```

### **Individual Services**
```bash
# MAVProxy (MAVLink routing)
sudo systemctl status mavproxy.service
journalctl -u mavproxy.service -f

# NTRIP Client (RTK corrections)
sudo systemctl status ntrip-client.service
journalctl -u ntrip-client.service -f

# Enhanced Telemetry (Data uplink)
sudo systemctl status enhanced-telemetry.service
journalctl -u enhanced-telemetry.service -f

# LiDAR Driver
sudo systemctl status lidar-driver.service
journalctl -u lidar-driver.service -f
```

### **Hardware Testing**
```bash
# Test GPS connection
ls -la /dev/ttyS5
python3 -c "import serial; ser = serial.Serial('/dev/ttyS5', 921600, timeout=1); print('GPS OK' if ser.is_open else 'GPS Error'); ser.close()"

# Test LiDAR connection
ls -la /dev/ttyUSB0
python3 companion/sensing/lidar_rplidar.py --test

# Test camera
ls -la /dev/video*
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera Error'); cap.release()"
```

---

## 🌐 **Network Configuration**

### **ZeroTier Setup**
```bash
# Install ZeroTier
curl -s https://install.zerotier.com | sudo bash

# Join network
sudo zerotier-cli join your_network_id

# Check status
sudo zerotier-cli status
sudo zerotier-cli listnetworks
```

### **Reverse SSH**
```bash
# On NUC - Create tunnel
ssh -R 2222:localhost:22 ubuntu@your-ec2-ip

# On EC2 - Connect to NUC
ssh -p 2222 astra@localhost
```

### **Firewall Rules**
```bash
# EC2 - Allow API ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 5000/tcp

# NUC - Allow MAVLink ports
sudo ufw allow 14550/tcp
sudo ufw allow 14551/tcp
sudo ufw allow 14552/tcp
```

---

## 🧪 **Testing & Validation**

### **API Health Checks**
```bash
# Test EC2 API
curl http://your-ec2-ip:5000/health

# Test telemetry endpoint
curl -X POST http://your-ec2-ip:5000/api/telemetry \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Test dashboard
curl http://your-ec2-ip:5000/dashboard
```

### **Sensor Validation**
```bash
# Test GPS
python3 companion/gnss/ntrip_client.py --test

# Test LiDAR
python3 companion/sensing/lidar_rplidar.py --test

# Test telemetry uplink
python3 companion/telemetry/ec2_uplink.py --test
```

### **Dashboard Verification**
1. Open: `http://your-ec2-ip:5000/dashboard`
2. Check real-time data updates
3. Verify rover location on map
4. Test 360° obstacle visualization

---

## 🔧 **Troubleshooting**

### **Common Issues**

#### **GPS Not Connecting**
```bash
# Check serial port
ls -la /dev/ttyS*
sudo chmod 666 /dev/ttyS5

# Test communication
python3 -c "
import serial
try:
    ser = serial.Serial('/dev/ttyS5', 921600, timeout=1)
    print('GPS OK')
    ser.close()
except Exception as e:
    print('GPS Error:', e)
"
```

#### **LiDAR Not Detecting**
```bash
# Check USB devices
lsusb | grep -i lidar
ls -la /dev/ttyUSB*

# Reset USB port
sudo usb-reset /dev/bus/usb/001/002
```

#### **Telemetry Not Sending**
```bash
# Check network
ping your-ec2-ip
curl http://your-ec2-ip:5000/health

# Check logs
journalctl -u enhanced-telemetry.service -f
```

#### **Dashboard Not Loading**
```bash
# Check API service
sudo systemctl status enhanced-api
journalctl -u enhanced-api -f

# Check port
netstat -tlnp | grep 5000
```

### **Debug Commands**
```bash
# Check all services
sudo systemctl list-units --type=service | grep astra

# View recent logs
journalctl --since "10 minutes ago" -u astra.target

# Check resources
df -h
free -h
top -p $(pgrep -f astra)
```

---

## 📁 **Important Files & Locations**

### **Configuration Files**
- **NUC Config**: `/opt/astra/companion/.env`
- **EC2 Config**: `/home/ubuntu/astra/.env`
- **Service Files**: `/etc/systemd/system/`

### **Log Files**
- **NUC Logs**: `/var/log/astra/`
- **EC2 Logs**: `/var/log/syslog`
- **Service Logs**: `journalctl -u service-name`

### **Application Files**
- **NUC App**: `/opt/astra/companion/`
- **EC2 App**: `/home/ubuntu/astra/`
- **Repository**: `https://github.com/harry0537/AWS-DashboardLiDAR-GPS-Integration.git`

---

## 🎯 **Key URLs & Endpoints**

### **Dashboard & API**
- **Dashboard**: `http://your-ec2-ip:5000/dashboard`
- **API Health**: `http://your-ec2-ip:5000/health`
- **Telemetry**: `http://your-ec2-ip:5000/api/telemetry`
- **Latest Data**: `http://your-ec2-ip:5000/api/telemetry/latest`

### **Management**
- **GitHub**: `https://github.com/harry0537/AWS-DashboardLiDAR-GPS-Integration.git`
- **Documentation**: `EC2_DEPLOYMENT_GUIDE.md`

---

## 🚨 **Emergency Procedures**

### **Stop Everything**
```bash
# Stop all services
sudo systemctl stop astra.target

# Emergency stop (if needed)
sudo pkill -f astra
sudo pkill -f mavproxy
```

### **Restart Everything**
```bash
# Restart all services
sudo systemctl restart astra.target

# Check status
sudo systemctl status astra.target
```

### **View Recent Errors**
```bash
# Check for errors in last hour
journalctl -u astra.target --since "1 hour ago" | grep -i error

# Check for failures
journalctl -u astra.target --since "1 hour ago" | grep -i fail
```

---

## 📞 **Support Information**

### **Log Locations**
- **Service Logs**: `journalctl -u service-name -f`
- **System Logs**: `/var/log/syslog`
- **Application Logs**: `/var/log/astra/`

### **Status Commands**
```bash
# Overall status
sudo systemctl status astra.target

# Individual services
sudo systemctl status mavproxy.service
sudo systemctl status enhanced-telemetry.service
sudo systemctl status ntrip-client.service

# Resource usage
htop
df -h
free -h
```

### **Useful Aliases**
```bash
# Add to ~/.bashrc
alias astra-status='sudo systemctl status astra.target'
alias astra-logs='journalctl -u astra.target -f'
alias astra-restart='sudo systemctl restart astra.target'
alias astra-stop='sudo systemctl stop astra.target'
alias astra-start='sudo systemctl start astra.target'
```

---

## 🎉 **Success Indicators**

### **System Health**
- ✅ All services running: `sudo systemctl status astra.target`
- ✅ GPS acquiring RTK fix: Check MAVProxy logs
- ✅ LiDAR detecting obstacles: Check LiDAR logs
- ✅ Telemetry sending: Check enhanced-telemetry logs
- ✅ Dashboard accessible: `curl http://your-ec2-ip:5000/health`

### **Data Flow**
- ✅ Position data updating on dashboard
- ✅ Obstacle visualization working
- ✅ Battery status showing
- ✅ Sensor status indicators active
- ✅ Map showing rover location

---

**🎯 Your Team Omega Project Astra is ready for autonomous operation!**

For detailed documentation, see `EC2_DEPLOYMENT_GUIDE.md`
For troubleshooting, check the guide's troubleshooting section
