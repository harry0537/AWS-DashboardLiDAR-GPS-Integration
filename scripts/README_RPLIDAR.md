# 🔍 RPLIDAR S3 Build and Capture Scripts

This directory contains scripts for building and using the RPLIDAR S3 with your rover project. The scripts support both Windows and Linux/Raspberry Pi platforms.

## 📋 Files Overview

### Windows Scripts (PowerShell)
- **`rplidar_build.ps1`** - Builds the RPLIDAR SDK applications using Visual Studio/MSBuild
- **`rplidar_s3_capture.ps1`** - Easy-to-use data capture wrapper for Windows

### Linux/Raspberry Pi Scripts (Bash)
- **`rplidar_build_linux.sh`** - Builds the RPLIDAR SDK applications using make/g++
- **`rplidar_s3_capture_linux.sh`** - Easy-to-use data capture wrapper for Linux

## 🚀 Quick Start

### On Raspberry Pi

1. **Download and setup:**
   ```bash
   # Clone the repository
   git clone <your-repo-url>
   cd AWS-Dashboard/scripts
   
   # Make scripts executable
   chmod +x rplidar_build_linux.sh
   chmod +x rplidar_s3_capture_linux.sh
   ```

2. **Install dependencies:**
   ```bash
   sudo apt update
   sudo apt install build-essential
   
   # Add user to dialout group for serial access
   sudo usermod -a -G dialout $USER
   # Logout and login again after this step
   ```

3. **Build the applications:**
   ```bash
   ./rplidar_build_linux.sh
   ```

4. **Find your RPLIDAR device:**
   ```bash
   ./rplidar_s3_capture_linux.sh --list-ports
   ```

5. **Start capturing data:**
   ```bash
   # Basic capture
   ./rplidar_s3_capture_linux.sh --device /dev/ttyUSB0
   
   # Save to file for 30 seconds
   ./rplidar_s3_capture_linux.sh -d /dev/ttyUSB0 -t 30 -o lidar_data.txt
   ```

### On Windows

1. **Open PowerShell as Administrator and navigate to the scripts directory**

2. **Build the applications:**
   ```powershell
   .\rplidar_build.ps1
   ```

3. **Find your RPLIDAR COM port:**
   ```powershell
   .\rplidar_s3_capture.ps1 -ListPorts
   ```

4. **Start capturing data:**
   ```powershell
   # Basic capture
   .\rplidar_s3_capture.ps1 -COMPort COM4
   
   # Save to file for 30 seconds
   .\rplidar_s3_capture.ps1 -COMPort COM4 -Duration 30 -OutputFile lidar_data.txt
   ```

## 🔧 RPLIDAR S3 Specifications

- **Model:** SLAMTEC RPLIDAR S3
- **Baud Rate:** 1,000,000 bps
- **Range:** 0.2m - 25m
- **Sample Rate:** 15.5K Hz
- **Angular Resolution:** 0.25°
- **Power:** 5V (recommend >2A power supply)

## 📡 Available Applications

### `ultra_simple`
- Continuously outputs scan data to console
- Format: `theta: XXX.XX Dist: XXXX.XX Q: XX`
- Best for: Real-time monitoring, pipe to other applications

### `simple_grabber`
- Shows device info and health status
- Displays two rounds of scan data
- Interactive histogram display
- Best for: Testing and validation

## 🛠️ Troubleshooting

### Raspberry Pi Common Issues

**Permission Denied on /dev/ttyUSB0:**
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
# Logout and login again
```

**Device Not Found:**
```bash
# Check for connected devices
sudo dmesg | tail
ls -la /dev/ttyUSB* /dev/ttyACM*

# Check if device is recognized
lsusb | grep -i "serial\|cp210\|ftdi"
```

**Build Fails:**
```bash
# Install build dependencies
sudo apt update
sudo apt install build-essential git

# Check compiler versions
gcc --version
g++ --version
make --version
```

### Windows Common Issues

**MSBuild Not Found:**
- Install Visual Studio 2019 or later
- Or install Visual Studio Build Tools
- Ensure Windows SDK 10.0 is installed

**COM Port Issues:**
- Check Device Manager for the correct COM port
- Ensure RPLIDAR drivers are installed
- Try different USB ports

## 🎯 Integration with Your Rover

These scripts create executables that can be integrated with your existing rover telemetry system:

```bash
# Example: Stream data to your Python processing script
./rplidar_s3_capture_linux.sh -d /dev/ttyUSB0 | python3 ../scripts/rplidar_to_dynamodb.py
```

## 📊 Data Format

### Ultra Simple Output Format
```
S theta: 000.25 Dist: 1234.50 Q: 15
  theta: 000.50 Dist: 1235.75 Q: 14
  theta: 000.75 Dist: 1236.25 Q: 15
```

Where:
- `S` = Start of new scan (sync bit)
- `theta` = Angle in degrees (0-359.75°)
- `Dist` = Distance in millimeters
- `Q` = Quality (0-63, higher is better)

### Simple Grabber Output
Includes device information, health status, and histogram visualization of scan data.

## 🔗 References

- [SLAMTEC RPLIDAR SDK](https://github.com/Slamtec/rplidar_sdk) - Official SDK repository
- [RPLIDAR S3 Datasheet](https://www.slamtec.com/en/Lidar/S3) - Technical specifications
- Your rover project documentation in `../docs/`

## 📝 Notes

- Scripts automatically detect the correct baud rate for RPLIDAR S3 (1,000,000 bps)
- Built executables are placed in `../rplidar_sdk_dev/output/`
- All scripts include comprehensive error checking and user guidance
- Linux scripts include automatic dependency checking
