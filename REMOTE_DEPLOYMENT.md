# 🌐 Remote Deployment Guide
## Deploying AWS Dashboard Sensors Without Direct Access

Since you don't have direct connection to the rover's host machine, here are several remote deployment strategies to get your sensor automation running.

---

## 🔍 **Available Remote Access Options**

### **Option 1: SSH Access (Most Common)**
```bash
# If you have SSH access to the rover
ssh ubuntu@<ROVER_IP_ADDRESS>

# Check if SSH is working
ssh -o ConnectTimeout=10 ubuntu@<ROVER_IP_ADDRESS> "echo 'SSH connection successful'"
```

### **Option 2: Network Discovery**
```bash
# Find rover on network
nmap -sn <NETWORK_RANGE>
# Example: nmap -sn 192.168.1.0/24

# Scan for open ports
nmap -p 22,5000 <ROVER_IP>
```

### **Option 3: Existing Remote Management**
- **TeamViewer/AnyDesk** - If already installed
- **VNC Server** - Remote desktop access
- **Web-based management** - If available
- **Cloud management platform** - AWS IoT, Azure IoT, etc.

---

## 🚀 **Strategy 1: SSH-Based Remote Deployment**

### **Prerequisites Check**
```bash
# Test SSH connectivity
ssh -o ConnectTimeout=10 ubuntu@<ROVER_IP> "whoami && hostname"

# Test if Python is available
ssh ubuntu@<ROVER_IP> "python3 --version"

# Check available disk space
ssh ubuntu@<ROVER_IP> "df -h"
```

### **Step 1: Transfer Project Files**
```bash
# Option A: Git clone (if rover has internet access)
ssh ubuntu@<ROVER_IP> "cd ~ && git clone <your-repo-url> AWS-Dashboard"

# Option B: SCP transfer (from your development machine)
scp -r AWS-Dashboard ubuntu@<ROVER_IP>:~/

# Option C: Wget/curl download (if you have a web server)
ssh ubuntu@<ROVER_IP> "cd ~ && wget <your-file-url> && tar -xzf AWS-Dashboard.tar.gz"
```

### **Step 2: Remote Setup Execution**
```bash
# Execute setup commands remotely
ssh ubuntu@<ROVER_IP> "cd ~/AWS-Dashboard && chmod +x setup_raspberry_pi.sh && ./setup_raspberry_pi.sh"
```

### **Step 3: Monitor Remote Setup**
```bash
# Watch setup progress
ssh ubuntu@<ROVER_IP> "tail -f ~/setup_log.txt"

# Check setup status
ssh ubuntu@<ROVER_IP> "ps aux | grep setup_raspberry_pi"
```

---

## 📦 **Strategy 2: Package-Based Deployment**

### **Create Deployment Package**
```bash
# On your development machine, create a deployment package
cd AWS-Dashboard
tar -czf rover-deployment.tar.gz \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='setup_log.txt' \
    .

# Create installation script
cat > install-remote.sh << 'EOF'
#!/bin/bash
echo "🚀 Remote Installation Script for Rover"
echo "========================================"

# Extract package
tar -xzf rover-deployment.tar.gz
cd AWS-Dashboard

# Make scripts executable
chmod +x setup_raspberry_pi.sh
chmod +x scripts/*.py
chmod +x test_sensors.py

# Run setup
./setup_raspberry_pi.sh

echo "✅ Installation complete!"
EOF

chmod +x install-remote.sh

# Create final package
tar -czf rover-complete.tar.gz rover-deployment.tar.gz install-remote.sh
```

### **Deploy Package to Rover**
```bash
# Transfer complete package
scp rover-complete.tar.gz ubuntu@<ROVER_IP>:~/

# Execute remote installation
ssh ubuntu@<ROVER_IP> "cd ~ && tar -xzf rover-complete.tar.gz && chmod +x install-remote.sh && ./install-remote.sh"
```

---

## 🌐 **Strategy 3: Web-Based Deployment**

### **Set Up Web Server for Distribution**
```bash
# On your development machine, create a simple web server
cd AWS-Dashboard
python3 -m http.server 8080

# Or use Python Flask for more control
cat > deploy_server.py << 'EOF'
from flask import Flask, send_file, render_template_string
import os

app = Flask(__name__)

@app.route('/')
def index():
    return '''
    <h1>Rover Deployment Server</h1>
    <p>Download and install the sensor automation system:</p>
    <a href="/download" class="btn">Download Package</a>
    <a href="/install" class="btn">Install Script</a>
    '''

@app.route('/download')
def download():
    return send_file('rover-deployment.tar.gz')

@app.route('/install')
def install():
    return '''
    <h2>Installation Commands</h2>
    <pre>
# On your rover, run these commands:
cd ~
wget http://<YOUR_IP>:8080/download
tar -xzf rover-deployment.tar.gz
cd AWS-Dashboard
chmod +x setup_raspberry_pi.sh
./setup_raspberry_pi.sh
    </pre>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
EOF

python3 deploy_server.py
```

### **Deploy from Web Server**
```bash
# On rover (if it has internet access)
ssh ubuntu@<ROVER_IP> "cd ~ && wget http://<YOUR_DEV_MACHINE_IP>:8080/download && tar -xzf rover-deployment.tar.gz && cd AWS-Dashboard && chmod +x setup_raspberry_pi.sh && ./setup_raspberry_pi.sh"
```

---

## 🔄 **Strategy 4: Incremental Remote Deployment**

### **Phase 1: Basic System Setup**
```bash
# Install system dependencies remotely
ssh ubuntu@<ROVER_IP> "sudo apt update && sudo apt install -y python3 python3-pip python3-venv build-essential libudev-dev libusb-1.0-0-dev"
```

### **Phase 2: Python Environment Setup**
```bash
# Create virtual environment
ssh ubuntu@<ROVER_IP> "cd ~ && python3 -m venv aws_dashboard_env && source aws_dashboard_env/bin/activate && pip install --upgrade pip"
```

### **Phase 3: Package Installation**
```bash
# Install required packages
ssh ubuntu@<ROVER_IP> "source ~/aws_dashboard_env/bin/activate && pip install pyserial pynmea2 rplidar-roboticia boto3 python-dotenv"
```

### **Phase 4: Configuration Setup**
```bash
# Create configuration directory and files
ssh ubuntu@<ROVER_IP> "mkdir -p ~/.aws_dashboard && cd ~/.aws_dashboard"
```

### **Phase 5: Service Creation**
```bash
# Create systemd services remotely
ssh ubuntu@<ROVER_IP> "sudo tee /etc/systemd/system/gps-sensor.service > /dev/null << 'EOF'
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
EOF"
```

---

## 📱 **Strategy 5: Mobile/Tablet Deployment**

### **Use Mobile SSH Client**
```bash
# Apps like Termius, JuiceSSH, or ConnectBot
# Connect to rover via WiFi or mobile hotspot

# Execute deployment commands from mobile
ssh ubuntu@<ROVER_IP>
cd ~
wget <deployment-url>
tar -xzf rover-deployment.tar.gz
cd AWS-Dashboard
./setup_raspberry_pi.sh
```

### **Mobile-Friendly Deployment Commands**
```bash
# Create mobile-optimized script
cat > mobile-deploy.sh << 'EOF'
#!/bin/bash
echo "📱 Mobile Deployment Script"
echo "=========================="

# Check connectivity
ping -c 1 google.com > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Internet connection available"
else
    echo "❌ No internet connection"
    exit 1
fi

# Download and install
cd ~
wget <deployment-url>
tar -xzf rover-deployment.tar.gz
cd AWS-Dashboard
chmod +x setup_raspberry_pi.sh
./setup_raspberry_pi.sh

echo "✅ Mobile deployment complete!"
EOF
```

---

## 🚨 **Strategy 6: Emergency Remote Access**

### **If SSH is Not Working**
```bash
# 1. Check if rover is powered and networked
ping <ROVER_IP>

# 2. Try alternative ports
ssh -p 2222 ubuntu@<ROVER_IP>  # Common alternative SSH port

# 3. Check if rover has any web interface
curl http://<ROVER_IP>:80
curl http://<ROVER_IP>:8080
curl http://<ROVER_IP>:5000

# 4. Use existing services
ssh ubuntu@<ROVER_IP> "sudo systemctl status"  # Check running services
```

### **Network Troubleshooting**
```bash
# Check network configuration
ssh ubuntu@<ROVER_IP> "ip addr show"
ssh ubuntu@<ROVER_IP> "route -n"
ssh ubuntu@<ROVER_IP> "cat /etc/network/interfaces"

# Check firewall settings
ssh ubuntu@<ROVER_IP> "sudo ufw status"
ssh ubuntu@<ROVER_IP> "sudo iptables -L"
```

---

## 📋 **Remote Deployment Checklist**

### **Before Starting:**
- [ ] **Network Access**: Verify rover is reachable
- [ ] **Authentication**: Ensure SSH keys or passwords work
- [ ] **Permissions**: Check if you can execute commands
- [ ] **Resources**: Verify sufficient disk space and memory
- [ ] **Dependencies**: Check if basic tools are available

### **During Deployment:**
- [ ] **File Transfer**: Successfully transfer project files
- [ ] **Setup Execution**: Run automated setup script
- [ ] **Error Handling**: Monitor and resolve any issues
- [ ] **Progress Tracking**: Log all deployment steps
- [ ] **Verification**: Test each component after setup

### **After Deployment:**
- [ ] **Service Status**: Verify all services are running
- [ ] **Sensor Connection**: Test GPS and LiDAR connectivity
- [ ] **Dashboard Access**: Confirm web interface works
- [ ] **Data Flow**: Verify data collection and storage
- [ ] **Auto-start**: Test reboot functionality

---

## 🎯 **Recommended Approach**

### **For Most Scenarios:**
1. **Start with SSH** - Most reliable and secure
2. **Use package deployment** - Reduces network issues
3. **Monitor remotely** - Watch logs and progress
4. **Test incrementally** - Verify each component

### **If SSH Fails:**
1. **Check network connectivity**
2. **Verify rover power and network**
3. **Try alternative access methods**
4. **Use existing management tools**

### **Emergency Fallback:**
1. **Physical access** (if possible)
2. **Network reset** (power cycle rover)
3. **Factory reset** (last resort)
4. **Contact support** (if available)

---

## 💡 **Pro Tips for Remote Deployment**

1. **Use screen/tmux** for long-running processes
   ```bash
   ssh ubuntu@<ROVER_IP> "screen -S deployment"
   # Run your commands
   # Detach with Ctrl+A, D
   # Reattach with: screen -r deployment
   ```

2. **Log everything** for troubleshooting
   ```bash
   ssh ubuntu@<ROVER_IP> "script deployment.log"
   # All commands and output will be logged
   # Exit script with: exit
   ```

3. **Test connectivity** before starting
   ```bash
   ssh ubuntu@<ROVER_IP> "echo 'Connection test successful'"
   ```

4. **Have fallback plans** ready
   - Alternative network paths
   - Different deployment methods
   - Emergency access procedures

---

## 🎉 **Success Indicators**

Your remote deployment is successful when:
- ✅ **SSH connection** is stable and responsive
- ✅ **Project files** are transferred completely
- ✅ **Setup script** runs without errors
- ✅ **Services start** automatically
- ✅ **Sensors connect** and provide data
- ✅ **Dashboard responds** to web requests
- ✅ **Data flows** to DynamoDB continuously

---

**🚀 Ready to deploy remotely? Choose your strategy and start with the connectivity test!**

The key is to start simple and build up complexity as you verify each step works in your remote environment. 