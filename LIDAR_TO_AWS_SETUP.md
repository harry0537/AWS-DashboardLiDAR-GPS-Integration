# LiDAR to AWS EC2 Dashboard Setup Guide

This guide will help you set up real-time LiDAR obstacle avoidance data transmission from your RPLIDAR S3 to your AWS EC2 dashboard.

## 🎯 Overview

The system consists of:
- **RPLIDAR S3** sensor for obstacle detection
- **Python script** that processes LiDAR data and sends to AWS
- **AWS DynamoDB** for data storage
- **EC2 Dashboard** for real-time visualization

## 📋 Prerequisites

- RPLIDAR S3 sensor connected to your system
- AWS account with DynamoDB access
- Python 3.8+ on your remote client
- Network connectivity to AWS

## 🚀 Quick Setup

### 1. On Your Remote Client (Ubuntu)

```bash
# Clone or download the scripts
cd ~
mkdir lidar_aws_setup
cd lidar_aws_setup

# Copy these files to your remote client:
# - rplidar_s3_to_aws.py
# - lidar_utils.py
# - setup_lidar_aws.sh
```

### 2. Run Setup Script

```bash
chmod +x setup_lidar_aws.sh
./setup_lidar_aws.sh
```

### 3. Configure AWS Credentials

Edit `~/lidar_aws_config/.env`:

```bash
nano ~/lidar_aws_config/.env
```

Update with your AWS credentials:

```env
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your_actual_access_key
AWS_SECRET_ACCESS_KEY=your_actual_secret_key
DEVICE_ID=your-device-name
RPLIDAR_PORT=/dev/ttyUSB0  # Adjust based on your system
```

### 4. Copy Scripts

```bash
cp rplidar_s3_to_aws.py ~/lidar_aws_config/
cp lidar_utils.py ~/lidar_aws_config/
```

### 5. Test Connection

```bash
cd ~/lidar_aws_config
source ~/lidar_env/bin/activate
python rplidar_s3_to_aws.py
```

## 📊 Dashboard Features

The enhanced dashboard displays:

### Real-time Obstacle Status
- **Critical** (< 30cm): Red alert with pulsing animation
- **Warning** (30-50cm): Orange warning indicator
- **Caution** (50-100cm): Yellow caution indicator
- **Clear** (> 100cm): Green normal status

### Sector-based Analysis
- **Front** (-45° to +45°): Forward obstacle detection
- **Left** (45° to 135°): Left-side obstacles
- **Right** (225° to 315°): Right-side obstacles
- **Rear** (135° to 225°): Backward obstacles

### Enhanced Visual Indicators
- Color-coded status cards
- Real-time distance measurements
- Quality metrics
- Critical obstacle alerts

## 🔧 Configuration Options

### LiDAR Parameters
```env
RPLIDAR_PORT=/dev/ttyUSB0    # Serial port
RPLIDAR_BAUD=115200          # Baud rate
MIN_QUALITY=10               # Minimum measurement quality
MAX_DISTANCE_MM=8000         # Maximum detection range
```

### AWS Configuration
```env
AWS_REGION=us-west-2
EXISTING_LIDAR_TABLE_NAME=UGVLidarScans
DEVICE_ID=ugv-1
```

### Obstacle Detection Thresholds
- **Critical**: < 300mm (30cm)
- **Warning**: 300-500mm (30-50cm)
- **Caution**: 500-1000mm (50-100cm)
- **Clear**: > 1000mm (100cm)

## 🏃‍♂️ Running the System

### Manual Start
```bash
cd ~/lidar_aws_config
source ~/lidar_env/bin/activate
python rplidar_s3_to_aws.py
```

### As System Service
```bash
sudo cp ~/lidar_aws_config/lidar-aws.service /etc/systemd/system/
sudo systemctl enable lidar-aws
sudo systemctl start lidar-aws
sudo systemctl status lidar-aws
```

### Using Startup Script
```bash
~/lidar_aws_config/start_lidar_aws.sh
```

## 📡 Data Flow

```
RPLIDAR S3 → Python Script → AWS DynamoDB → EC2 Dashboard
     ↓              ↓              ↓              ↓
  Raw Data    Obstacle Analysis   Storage    Real-time Display
```

### Data Structure
```json
{
  "device_id": "ugv-1",
  "timestamp": 1640995200,
  "object_avoidance": {
    "status": "warning",
    "closest_distance_cm": 35.2,
    "closest_distance_m": 0.35,
    "measurement_count": 245,
    "quality_avg": 85.3,
    "sectors": {
      "front": {
        "closest_cm": 35.2,
        "danger_level": "high",
        "count": 45
      },
      "left": {
        "closest_cm": 120.5,
        "danger_level": "low",
        "count": 52
      }
    }
  }
}
```

## 🔍 Troubleshooting

### Common Issues

**1. LiDAR Connection Failed**
```bash
# Check if device is detected
ls -la /dev/ttyUSB*
# Check permissions
sudo usermod -aG dialout $USER
# Reboot or reconnect device
```

**2. AWS Connection Failed**
```bash
# Verify credentials
aws sts get-caller-identity
# Check region and table names
aws dynamodb list-tables --region us-west-2
```

**3. No Data in Dashboard**
```bash
# Check if data is being sent
aws dynamodb scan --table-name UGVLidarScans --region us-west-2
# Verify API endpoint
curl http://your-ec2-ip:5000/api/lidar/latest
```

**4. Permission Denied**
```bash
# Fix file permissions
chmod +x ~/lidar_aws_config/*.py
chmod +x ~/lidar_aws_config/*.sh
```

### Debug Mode
Add debug logging to the script:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Performance Monitoring

### Check System Status
```bash
# Service status
sudo systemctl status lidar-aws

# Logs
sudo journalctl -u lidar-aws -f

# Resource usage
htop
```

### Monitor Data Flow
```bash
# Check DynamoDB items
aws dynamodb scan --table-name UGVLidarScans --region us-west-2 --max-items 5

# Check API response
curl -s http://your-ec2-ip:5000/api/lidar/latest | jq
```

## 🔒 Security Considerations

1. **AWS Credentials**: Store securely, rotate regularly
2. **Network Security**: Use VPC and security groups
3. **Data Encryption**: Enable DynamoDB encryption
4. **Access Control**: Use IAM roles and policies

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review logs: `sudo journalctl -u lidar-aws`
3. Verify AWS credentials and permissions
4. Test LiDAR connection separately

## 🎉 Success Indicators

You'll know it's working when:
- ✅ Script shows "RPLIDAR S3 connected and healthy"
- ✅ Console displays scan updates every 10 scans
- ✅ Dashboard shows real-time obstacle data
- ✅ DynamoDB contains recent entries
- ✅ No error messages in logs
