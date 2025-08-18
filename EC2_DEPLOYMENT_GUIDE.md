# 🚀 Team Omega Project Astra - EC2 Deployment Guide

**Complete Guide to Deploy Enhanced Telemetry System and Connect to EC2**

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [EC2 Setup](#ec2-setup)
4. [NUC Companion Setup](#nuc-companion-setup)
5. [Network Configuration](#network-configuration)
6. [Service Deployment](#service-deployment)
7. [Testing & Validation](#testing--validation)
8. [Troubleshooting](#troubleshooting)
9. [Glossary](#glossary)
10. [Project Checklist](#project-checklist)

---

## 🎯 Overview

This guide will help you deploy the **Team Omega Project Astra** enhanced telemetry system and connect it to your existing EC2 infrastructure. The system provides:

- **Enhanced Rover Data**: Position, speed, battery, obstacles, sensors
- **Real-time Dashboard**: Beautiful web interface with maps and visualizations
- **Production Services**: Systemd-managed services with proper logging
- **EC2 Integration**: Seamless connection to your existing infrastructure

---

## ✅ Prerequisites

### Hardware Requirements
- **Intel NUC** (Companion Computer)
- **Pixhawk 6C** (Flight Controller)
- **ZED-F9P GPS** (RTK-capable)
- **RPLIDAR A1/A2/N301** (360° LiDAR)
- **UVC/CSI Camera** (Image capture)
- **Maxbotix Ultrasonic** (Optional - blind spot detection)
- **5G/ZeroTier Network** (Remote connectivity)

### Software Requirements
- **Ubuntu 20.04+** on NUC
- **Python 3.10+**
- **ArduPilot** (latest stable)
- **MAVProxy** (latest version)
- **Docker** (for cloud deployment)

### Network Requirements
- **EC2 Instance** with public IP
- **DynamoDB Tables** (existing infrastructure)
- **ZeroTier VPN** (for secure remote access)
- **Reverse SSH** (for remote assistance)

---

## ☁️ EC2 Setup

### 1. Update Existing EC2 Instance

```bash
# SSH to your EC2 instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker (if not already installed)
sudo apt install docker.io docker-compose -y
sudo usermod -a -G docker ubuntu
```

### 2. Deploy Enhanced API

```bash
# Clone the repository (if not already done)
git clone https://github.com/harry0537/AWS-DashboardLiDAR-GPS-Integration.git
cd AWS-DashboardLiDAR-GPS-Integration

# Copy enhanced API to EC2
cp cloud/enhanced_api.py /home/ubuntu/
cp cloud/requirements.txt /home/ubuntu/
cp cloud/env.example /home/ubuntu/.env

# Install Python dependencies
sudo apt install python3-pip python3-venv -y
python3 -m venv /home/ubuntu/venv
source /home/ubuntu/venv/bin/activate
pip install -r /home/ubuntu/requirements.txt
```

### 3. Configure Environment

```bash
# Edit environment file
nano /home/ubuntu/.env

# Key configurations:
FLASK_PORT=5000
FLASK_HOST=0.0.0.0
FLASK_DEBUG=false
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

### 4. Create Systemd Service

```bash
# Create service file
sudo nano /etc/systemd/system/enhanced-api.service

[Unit]
Description=Team Omega Enhanced API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu
Environment=PATH=/home/ubuntu/venv/bin
ExecStart=/home/ubuntu/venv/bin/python enhanced_api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable enhanced-api
sudo systemctl start enhanced-api
```

### 5. Configure Nginx (Optional)

```bash
# Install Nginx
sudo apt install nginx -y

# Create Nginx configuration
sudo nano /etc/nginx/sites-available/astra-api

server {
    listen 80;
    server_name your-ec2-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Enable site
sudo ln -s /etc/nginx/sites-available/astra-api /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

---

## 🖥️ NUC Companion Setup

### 1. Initial Setup

```bash
# SSH to your NUC
ssh astra@your-nuc-ip

# Clone repository
git clone https://github.com/harry0537/AWS-DashboardLiDAR-GPS-Integration.git
cd AWS-DashboardLiDAR-GPS-Integration

# Run deployment script (as root)
sudo bash ops/deploy/setup_astra_services.sh
```

### 2. Configure Environment

```bash
# Edit companion environment
nano /opt/astra/companion/.env

# Key configurations:
EC2_API_URL=http://your-ec2-ip:5000
DEVICE_ID=astra-rover-1
MAVPROXY_MASTER_PORT=/dev/ttyS5
NTRIP_CASTER_URL=your_ntrip_caster
LIDAR_SERIAL_PORT=/dev/ttyUSB0
CAMERA_DEVICE=/dev/video0
```

### 3. Hardware Connections

#### GPS (ZED-F9P)
```bash
# Check GPS connection
ls -la /dev/ttyS5
sudo chmod 666 /dev/ttyS5

# Test GPS
python3 -c "
import serial
ser = serial.Serial('/dev/ttyS5', 921600, timeout=1)
print('GPS Connected:', ser.is_open)
ser.close()
"
```

#### LiDAR (RPLIDAR)
```bash
# Check LiDAR connection
ls -la /dev/ttyUSB0
sudo chmod 666 /dev/ttyUSB0

# Test LiDAR
python3 companion/sensing/lidar_rplidar.py --test
```

#### Camera
```bash
# Check camera
ls -la /dev/video*
v4l2-ctl --list-devices

# Test camera
python3 -c "
import cv2
cap = cv2.VideoCapture(0)
print('Camera Connected:', cap.isOpened())
cap.release()
"
```

### 4. Start Services

```bash
# Start all Astra services
sudo systemctl start astra.target

# Check service status
sudo systemctl status astra.target
journalctl -u astra.target -f

# Individual service status
sudo systemctl status mavproxy.service
sudo systemctl status ntrip-client.service
sudo systemctl status enhanced-telemetry.service
```

---

## 🌐 Network Configuration

### 1. ZeroTier Setup

```bash
# Install ZeroTier on NUC
curl -s https://install.zerotier.com | sudo bash

# Join network
sudo zerotier-cli join your_network_id

# Check status
sudo zerotier-cli status
sudo zerotier-cli listnetworks
```

### 2. Reverse SSH Setup

```bash
# On NUC - Create reverse SSH tunnel
ssh -R 2222:localhost:22 ubuntu@your-ec2-ip

# On EC2 - Connect to NUC
ssh -p 2222 astra@localhost
```

### 3. Firewall Configuration

```bash
# On EC2 - Allow API port
sudo ufw allow 5000
sudo ufw allow 80
sudo ufw allow 443

# On NUC - Allow MAVLink ports
sudo ufw allow 14550
sudo ufw allow 14551
sudo ufw allow 14552
```

---

## 🔧 Service Deployment

### 1. Service Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Pixhawk 6C    │    │   Intel NUC     │    │   EC2 Cloud     │
│                 │    │                 │    │                 │
│ • ArduPilot     │◄──►│ • MAVProxy      │◄──►│ • Enhanced API  │
│ • ZED-F9P GPS   │    │ • NTRIP Client  │    │ • Dashboard     │
│ • Sensors       │    │ • Fusion Engine │    │ • DynamoDB      │
└─────────────────┘    │ • Telemetry     │    └─────────────────┘
                       └─────────────────┘
```

### 2. Service Dependencies

```bash
# Service startup order
1. mavproxy.service      # MAVLink routing
2. ntrip-client.service  # RTK corrections
3. enhanced-telemetry.service # Data uplink
4. lidar-driver.service  # Obstacle detection
5. camera-capture.service # Image capture
```

### 3. Monitoring Services

```bash
# View all service logs
journalctl -u astra.target -f

# Individual service logs
journalctl -u mavproxy.service -f
journalctl -u enhanced-telemetry.service -f

# Service status
sudo systemctl status astra.target
```

---

## 🧪 Testing & Validation

### 1. Health Checks

```bash
# Test EC2 API health
curl http://your-ec2-ip:5000/health

# Test telemetry endpoint
curl -X POST http://your-ec2-ip:5000/api/telemetry \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Test dashboard
curl http://your-ec2-ip:5000/dashboard
```

### 2. Sensor Validation

```bash
# Test GPS
python3 companion/gnss/ntrip_client.py --test

# Test LiDAR
python3 companion/sensing/lidar_rplidar.py --test

# Test telemetry uplink
python3 companion/telemetry/ec2_uplink.py --test
```

### 3. Dashboard Verification

1. **Open Dashboard**: `http://your-ec2-ip:5000/dashboard`
2. **Check Data Flow**: Verify real-time updates
3. **Test Map**: Confirm rover location display
4. **Verify Obstacles**: Check 360° visualization

---

## 🔧 Troubleshooting

### Common Issues

#### 1. GPS Not Connecting
```bash
# Check serial port
ls -la /dev/ttyS*
sudo chmod 666 /dev/ttyS5

# Test serial communication
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

#### 2. LiDAR Not Detecting
```bash
# Check USB devices
lsusb | grep -i lidar
ls -la /dev/ttyUSB*

# Reset USB port
sudo usb-reset /dev/bus/usb/001/002
```

#### 3. Telemetry Not Sending
```bash
# Check network connectivity
ping your-ec2-ip
curl http://your-ec2-ip:5000/health

# Check service logs
journalctl -u enhanced-telemetry.service -f
```

#### 4. Dashboard Not Loading
```bash
# Check API service
sudo systemctl status enhanced-api
journalctl -u enhanced-api -f

# Check port availability
netstat -tlnp | grep 5000
```

### Debug Commands

```bash
# Check all services
sudo systemctl list-units --type=service | grep astra

# View recent logs
journalctl --since "10 minutes ago" -u astra.target

# Check disk space
df -h
du -sh /var/log/astra/*

# Check memory usage
free -h
top -p $(pgrep -f astra)
```

---

## 📚 Glossary

### Technical Terms

**ArduPilot**: Open-source autopilot software for autonomous vehicles
**MAVLink**: Communication protocol for drones and ground control stations
**MAVProxy**: Ground station software for MAVLink message routing
**RTK (Real-Time Kinematic)**: GPS technique for centimeter-level accuracy
**NTRIP**: Networked Transport of RTCM via Internet Protocol
**LiDAR**: Light Detection and Ranging for 360° obstacle detection
**UVC**: USB Video Class for camera interfaces
**CSI**: Camera Serial Interface for embedded cameras
**ZeroTier**: VPN solution for secure remote access
**Reverse SSH**: SSH tunnel for remote assistance
**Systemd**: Linux system and service manager
**DynamoDB**: AWS NoSQL database service

### Project Terms

**Team Omega**: Your project team name
**Project Astra**: The autonomous rover project
**NUC**: Intel Next Unit of Computing (companion computer)
**Pixhawk**: Flight controller hardware
**ZED-F9P**: RTK-capable GPS receiver
**RPLIDAR**: 360° LiDAR sensor
**EC2**: Amazon Elastic Compute Cloud
**Companion Computer**: Secondary computer for sensor processing
**Fusion Engine**: Multi-sensor data combination system
**Telemetry Uplink**: Data transmission to cloud dashboard

### Status Indicators

**Armed**: Vehicle is ready for autonomous operation
**RTK FIXED**: GPS has centimeter-level accuracy
**RTK FLOAT**: GPS has decimeter-level accuracy
**NO RTK**: Standard GPS accuracy (meter-level)
**MANUAL**: Human-controlled mode
**AUTO**: Autonomous navigation mode
**RTL**: Return-to-Launch mode
**LOITER**: Station-keeping mode

---

## ✅ Project Checklist

### Pre-Deployment
- [ ] Hardware assembled and connected
- [ ] Ubuntu 20.04+ installed on NUC
- [ ] ArduPilot firmware updated
- [ ] EC2 instance running
- [ ] DynamoDB tables created
- [ ] ZeroTier network configured

### EC2 Setup
- [ ] Enhanced API deployed
- [ ] Environment configured
- [ ] Systemd service created
- [ ] Nginx configured (optional)
- [ ] Firewall rules set
- [ ] Health check passing

### NUC Setup
- [ ] Repository cloned
- [ ] Services deployed
- [ ] Environment configured
- [ ] Hardware connections verified
- [ ] Services started
- [ ] Logs showing normal operation

### Network Configuration
- [ ] ZeroTier connected
- [ ] Reverse SSH working
- [ ] Ports accessible
- [ ] Firewall configured
- [ ] DNS resolved

### Testing & Validation
- [ ] GPS acquiring RTK fix
- [ ] LiDAR detecting obstacles
- [ ] Camera capturing images
- [ ] Telemetry sending to EC2
- [ ] Dashboard displaying data
- [ ] Map showing rover location

### Production Readiness
- [ ] Services auto-starting
- [ ] Logs being rotated
- [ ] Monitoring configured
- [ ] Backup strategy in place
- [ ] Documentation complete
- [ ] Team trained on operation

---

## 🚀 Quick Start Commands

### Deploy Everything
```bash
# On EC2
git clone https://github.com/harry0537/AWS-DashboardLiDAR-GPS-Integration.git
cd AWS-DashboardLiDAR-GPS-Integration
sudo bash cloud/deploy.sh

# On NUC
git clone https://github.com/harry0537/AWS-DashboardLiDAR-GPS-Integration.git
cd AWS-DashboardLiDAR-GPS-Integration
sudo bash ops/deploy/setup_astra_services.sh
```

### Check Status
```bash
# Check all services
sudo systemctl status astra.target

# View logs
journalctl -u astra.target -f

# Test dashboard
curl http://your-ec2-ip:5000/health
```

### Emergency Commands
```bash
# Stop all services
sudo systemctl stop astra.target

# Restart services
sudo systemctl restart astra.target

# View recent errors
journalctl -u astra.target --since "1 hour ago" | grep -i error
```

---

## 📞 Support

### Logs Location
- **NUC Logs**: `/var/log/astra/`
- **EC2 Logs**: `/var/log/syslog`
- **Service Logs**: `journalctl -u service-name`

### Configuration Files
- **NUC Config**: `/opt/astra/companion/.env`
- **EC2 Config**: `/home/ubuntu/.env`
- **Service Files**: `/etc/systemd/system/`

### Useful Commands
```bash
# Check service status
sudo systemctl status service-name

# View service logs
journalctl -u service-name -f

# Restart service
sudo systemctl restart service-name

# Check hardware
lsusb
ls -la /dev/tty*
```

---

**🎉 Congratulations! Your Team Omega Project Astra is now ready for autonomous operation!**

For additional support, check the project documentation or contact your team lead.
