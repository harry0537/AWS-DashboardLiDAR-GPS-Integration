# EC2 Integration Guide - AWS Dashboard

## Overview
This guide explains how to integrate your local development with the **existing EC2 infrastructure** that already has DynamoDB and ArduPilot configured by the previous team.

## Key Changes from Meeting with Artem

### ✅ **What's Already Working:**
- **DynamoDB**: Running on EC2 with live rover data
- **AWS Dashboard**: Already hosted on EC2
- **LiDAR + ArduPilot**: Basic object avoidance integration working
- **Hardware**: Sensors already connected to ArduPilot

### 🎯 **What We Need to Do:**
- Connect to existing EC2 instance
- Integrate with existing DynamoDB tables
- Add ultrasonic sensor (Maxbotix I2C EZ4)
- Implement battery monitoring (11V RTL threshold)
- Simplify LiDAR processing (distance-only for object avoidance)
- **Connect to existing EC2-hosted dashboard**
- **Verify complete data flow from sensors to dashboard**

## EC2 Connection Steps (from Artem)

### 1. AWS Console Access
```bash
# Login with Artem's credentials
# Navigate to: EC2 > Instances
# Select running instance and click "Connect"
```

### 2. RDP Connection
```
1. Choose "RDP Client" tab
2. Select "Connect using Fleet Manager"
3. Click "Fleet Manager Remote Desktop" button
4. Select Key Pair option
5. Choose the .pem file Artem sent
6. Click Connect
7. Note: May require instance restart if connection fails
```

### 3. Alternative: Systems Manager
```
- Systems Manager > Fleet Manager worked for Artem
- Similar steps as above
```

## Project Structure Updates

### **New Scripts Added:**
- `ultrasonic_integration.py` - Maxbotix I2C EZ4 integration
- `battery_monitor.py` - Pixhawk voltage monitoring
- Updated `rplidar_to_dynamodb.py` - Simplified for object avoidance
- Updated `gps_to_dynamodb.py` - Added battery monitoring

### **Configuration Changes:**
- `env.example` - Updated for EC2 integration
- `app.py` - New endpoints for ultrasonic and battery
- Frontend - New sensor data display sections

## Environment Configuration

### **Copy and Configure Environment:**
```bash
cp env.example .env
# Edit .env with your actual values
```

### **Key Environment Variables:**
```bash
# AWS Configuration
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here

# DynamoDB Tables (existing EC2 infrastructure)
EXISTING_DDB_TABLE_NAME=UGVTelemetry
EXISTING_LIDAR_TABLE_NAME=UGVLidarScans
ULTRASONIC_TABLE_NAME=UGVUltrasonic
BATTERY_TABLE_NAME=UGVBattery

# Hardware Configuration
DEVICE_ID=ugv-1  # Should match existing rover ID
```

## Hardware Integration

### **1. Ultrasonic Sensor (Maxbotix I2C EZ4)**
```bash
# ArduPilot Configuration:
RNGFND_TYPE = 2 (MaxbotixI2C)
RNGFND_MAX = 700 (cm)

# Run integration:
python scripts/ultrasonic_integration.py
```

### **2. Battery Monitoring (Pixhawk)**
```bash
# RTL Threshold: 11V
# Run monitoring:
python scripts/battery_monitor.py
```

### **3. LiDAR (Simplified)**
```bash
# Only distance data needed for object avoidance
# Run integration:
python scripts/rplidar_to_dynamodb.py
```

### **4. GPS (simpleRTK2B)**
```bash
# Already connected to ArduPilot
# Run integration:
python scripts/gps_to_dynamodb.py
```

## Connecting to Existing EC2 Dashboard

### **Step 1: Access Existing Dashboard**
```bash
# 1. Connect to EC2 instance using Artem's credentials
# 2. Navigate to the existing dashboard URL (ask Artem for the exact URL)
# 3. Verify you can see the existing dashboard with live data
```

### **Step 2: Identify Dashboard Configuration**
```bash
# In the EC2 instance, locate:
# - Dashboard configuration files
# - API endpoints being used
# - DynamoDB table names and structure
# - Existing sensor data flow
```

### **Step 3: Update Dashboard Configuration**
```bash
# 1. Find the dashboard config file (likely config.js or similar)
# 2. Update API endpoints to point to your local development
# 3. Or update your local config to point to EC2 dashboard
```

### **Step 4: Test Dashboard Integration**
```bash
# 1. Start your local API: python app.py
# 2. Verify dashboard can access your new endpoints
# 3. Check that sensor data appears in dashboard
```

## Complete System Integration

### **Phase 1: Local Development Setup**
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp env.example .env
# Edit .env with actual values

# 3. Test local API
python app.py
# Should show: "Connecting to existing EC2 DynamoDB infrastructure"
```

### **Phase 2: Hardware Connection**
```bash
# 1. Connect ultrasonic sensor to I2C bus
# 2. Verify LiDAR USB connection
# 3. Check GPS serial connection
# 4. Test Pixhawk communication

# Test individual sensors:
python scripts/ultrasonic_integration.py
python scripts/rplidar_to_dynamodb.py
python scripts/gps_to_dynamodb.py
python scripts/battery_monitor.py
```

### **Phase 3: Data Flow Verification**
```bash
# 1. Start all sensor scripts
# 2. Check DynamoDB for incoming data
# 3. Verify API endpoints return data
# 4. Test dashboard updates

# Test API endpoints:
curl http://localhost:5000/api/status
curl http://localhost:5000/api/telemetry/latest
curl http://localhost:5000/api/lidar/latest
curl http://localhost:5000/api/ultrasonic/latest
curl http://localhost:5000/api/battery/latest
```

### **Phase 4: Dashboard Integration**
```bash
# 1. Open existing EC2 dashboard
# 2. Verify new sensor data appears
# 3. Test real-time updates
# 4. Validate object avoidance displays
```

## Testing Integration

### **1. Check EC2 Connection:**
```bash
python app.py
# Should show: "Connecting to existing EC2 DynamoDB infrastructure"
```

### **2. Test API Endpoints:**
```bash
# System status
curl http://localhost:5000/api/status

# Sensor data
curl http://localhost:5000/api/telemetry/latest
curl http://localhost:5000/api/lidar/latest
curl http://localhost:5000/api/ultrasonic/latest
curl http://localhost:5000/api/battery/latest
```

### **3. Verify Dashboard:**
- Open existing EC2 dashboard URL
- Check sensor data sections
- Verify real-time updates
- Test new sensor displays

### **4. Test Complete Data Flow:**
```bash
# 1. Start sensor scripts
# 2. Check DynamoDB tables
# 3. Verify API returns data
# 4. Confirm dashboard updates
# 5. Test object avoidance logic
```

## Troubleshooting

### **Common Issues:**

#### **EC2 Connection Failed:**
```bash
# Try instance restart
# Check .pem file permissions
# Verify instance is running
# Use Systems Manager as alternative
```

#### **DynamoDB Access Denied:**
```bash
# Check AWS credentials
# Verify table names match existing infrastructure
# Check IAM permissions
# Confirm region settings
```

#### **Sensor Connection Issues:**
```bash
# Check USB ports and permissions
# Verify sensor addresses (I2C)
# Check serial port availability
# Test with individual sensor scripts
```

#### **Dashboard Not Updating:**
```bash
# Check API endpoint URLs
# Verify CORS settings
# Check browser console for errors
# Confirm data is reaching DynamoDB
```

### **Debug Commands:**
```bash
# Check sensor status
python check_sensor_status.py

# Test individual sensors
python test_sensors.py

# Monitor DynamoDB connection
python -c "import boto3; print('AWS SDK working')"

# Check API logs
tail -f app.log  # if logging enabled
```

## Next Steps

### **Immediate (Week 1):**
1. ✅ Get EC2 access using Artem's credentials
2. ✅ Examine existing infrastructure and dashboard
3. ✅ Configure environment variables
4. ✅ Test API connection to EC2 DynamoDB

### **Hardware (Week 2):**
1. 🔌 Connect ultrasonic sensor to I2C bus
2. 🔌 Verify LiDAR USB connection
3. 🔌 Check GPS serial connection
4. 🔌 Test Pixhawk communication

### **Integration (Week 3):**
1. 📡 Start sensor scripts
2. 📡 Verify data flow to DynamoDB
3. 📡 Test dashboard updates
4. 📡 Validate object avoidance logic

### **Production (Week 4):**
1. 🚀 Deploy to EC2 instance
2. 🚀 Configure production environment
3. 🚀 Test complete system
4. 🚀 Document final setup

## Notes from Meeting

### **LiDAR Requirements:**
- **No complex SLAM needed** - basic object detection sufficient
- **Distance data only** - ArduPilot handles avoidance logic
- **Simple integration** - already working with previous team

### **Ultrasonic Configuration:**
- **Model**: Maxbotix I2C EZ4
- **ArduPilot**: RNGFND_TYPE = 2, RNGFND_MAX = 700cm
- **Potential conflict**: Both LiDAR and ultrasonic use RNGFND_TYPE

### **Battery Monitoring:**
- **Source**: Pixhawk built-in voltage monitoring
- **Threshold**: 11V for RTL (Return to Launch)
- **Action**: Automatic RTL when threshold exceeded

### **No ROS/SLAM Required:**
- **Current approach**: Basic sensor integration sufficient
- **Future consideration**: ROS for advanced robotics (optional)

## Dashboard Integration Checklist

### **Before Starting:**
- [ ] EC2 access credentials received
- [ ] Existing dashboard URL identified
- [ ] DynamoDB table names confirmed
- [ ] Hardware sensors available

### **Local Development:**
- [ ] Environment configured (.env file)
- [ ] Dependencies installed
- [ ] API starts successfully
- [ ] Can connect to EC2 DynamoDB

### **Hardware Setup:**
- [ ] Ultrasonic sensor connected to I2C
- [ ] LiDAR connected via USB
- [ ] GPS connected via serial
- [ ] Pixhawk communication working

### **Data Flow:**
- [ ] Sensor scripts running
- [ ] Data reaching DynamoDB
- [ ] API endpoints returning data
- [ ] Dashboard receiving updates

### **Final Integration:**
- [ ] All sensors operational
- [ ] Dashboard showing real-time data
- [ ] Object avoidance working
- [ ] Battery monitoring active

## Support

For issues with existing EC2 infrastructure, contact the previous team or Artem.
For new sensor integration issues, check the troubleshooting section above.
For dashboard integration problems, verify API endpoints and data flow.

## Quick Start Commands

```bash
# 1. Setup environment
cp env.example .env
# Edit .env with your values

# 2. Install dependencies
pip install -r requirements.txt

# 3. Test EC2 connection
python app.py

# 4. Test individual sensors
python scripts/ultrasonic_integration.py
python scripts/rplidar_to_dynamodb.py
python scripts/gps_to_dynamodb.py
python scripts/battery_monitor.py

# 5. Check API endpoints
curl http://localhost:5000/api/status
```
