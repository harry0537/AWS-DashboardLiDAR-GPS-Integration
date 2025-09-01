#!/bin/bash
# Setup script for RPLIDAR S3 to AWS EC2 Dashboard
# Run this script on your remote client to configure the LiDAR data transmission

set -e

echo "🚀 Setting up RPLIDAR S3 to AWS EC2 Dashboard"
echo "=============================================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please don't run this script as root"
    exit 1
fi

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "🐍 Python version: $python_version"

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt update
sudo apt install -y python3-venv python3-pip git

# Create virtual environment
echo "🔧 Creating Python virtual environment..."
python3 -m venv lidar_env
source lidar_env/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install boto3 numpy matplotlib pyserial

# Create configuration directory
echo "📁 Creating configuration directory..."
mkdir -p ~/lidar_aws_config

# Create environment file
echo "⚙️ Creating environment configuration..."
cat > ~/lidar_aws_config/.env << EOF
# AWS Configuration
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here

# DynamoDB Configuration
DDB_ENDPOINT_URL=

# DynamoDB Table Names
EXISTING_DDB_TABLE_NAME=UGVTelemetry
EXISTING_LIDAR_TABLE_NAME=UGVLidarScans
ULTRASONIC_TABLE_NAME=UGVUltrasonic
BATTERY_TABLE_NAME=UGVBattery

# Device Configuration
DEVICE_ID=ugv-1

# LiDAR Configuration
RPLIDAR_PORT=/dev/ttyUSB0
RPLIDAR_BAUD=115200
EOF

# Create startup script
echo "📝 Creating startup script..."
cat > ~/lidar_aws_config/start_lidar_aws.sh << 'EOF'
#!/bin/bash
# Startup script for RPLIDAR S3 to AWS

# Activate virtual environment
source ~/lidar_env/bin/activate

# Load environment variables
export $(cat ~/lidar_aws_config/.env | xargs)

# Change to script directory
cd ~/lidar_aws_config

# Start LiDAR to AWS transmission
python rplidar_s3_to_aws.py
EOF

chmod +x ~/lidar_aws_config/start_lidar_aws.sh

# Create systemd service (optional)
echo "🔧 Creating systemd service (optional)..."
cat > ~/lidar_aws_config/lidar-aws.service << EOF
[Unit]
Description=RPLIDAR S3 to AWS EC2 Dashboard
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/lidar_aws_config
Environment=PATH=$HOME/lidar_env/bin
ExecStart=$HOME/lidar_aws_config/start_lidar_aws.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Setup completed!"
echo ""
echo "📋 Next steps:"
echo "1. Copy your AWS credentials to ~/lidar_aws_config/.env"
echo "2. Copy lidar_utils.py and rplidar_s3_to_aws.py to ~/lidar_aws_config/"
echo "3. Test the connection:"
echo "   cd ~/lidar_aws_config"
echo "   source ~/lidar_env/bin/activate"
echo "   python rplidar_s3_to_aws.py"
echo ""
echo "4. Optional: Install as systemd service:"
echo "   sudo cp ~/lidar_aws_config/lidar-aws.service /etc/systemd/system/"
echo "   sudo systemctl enable lidar-aws"
echo "   sudo systemctl start lidar-aws"
echo ""
echo "🔗 Your LiDAR data will be sent to AWS EC2 dashboard at:"
echo "   http://your-ec2-ip:5000"
