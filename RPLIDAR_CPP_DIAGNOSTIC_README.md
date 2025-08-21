# RPLIDAR C++ Hardware Diagnostic Tool

This C++ diagnostic tool bypasses Python library issues by communicating directly with the RPLIDAR hardware using low-level serial communication. It exports results to JSON for Python analysis.

## Why C++ Approach?

The "Descriptor length mismatch" error you're seeing is a common issue with Python RPLIDAR libraries. This C++ tool:

1. **Direct Hardware Communication**: Bypasses Python library protocol issues
2. **Raw Serial Access**: Tests fundamental hardware communication
3. **Comprehensive Testing**: Tests multiple baudrates and communication modes
4. **Detailed Diagnostics**: Provides specific failure points
5. **JSON Export**: Results can be analyzed by Python scripts

## Files Created

- `rplidar_cpp_diagnostic.cpp` - Main C++ diagnostic tool
- `rplidar_results_analyzer.py` - Python script to analyze results
- `build_rplidar_diagnostic.bat` - Windows build script
- `build_rplidar_diagnostic.sh` - Linux build script

## Quick Start

### 1. Build the Diagnostic Tool

**On Windows:**
```bash
# Using the batch file
build_rplidar_diagnostic.bat

# Or manually
g++ -std=c++11 -O2 -o rplidar_cpp_diagnostic.exe rplidar_cpp_diagnostic.cpp
```

**On Linux:**
```bash
# Using the shell script
./build_rplidar_diagnostic.sh

# Or manually
g++ -std=c++11 -O2 -o rplidar_cpp_diagnostic rplidar_cpp_diagnostic.cpp
```

### 2. Run the Diagnostic

```bash
# Windows
rplidar_cpp_diagnostic.exe

# Linux
./rplidar_cpp_diagnostic
```

### 3. Analyze Results

```bash
python rplidar_results_analyzer.py
```

## What the Diagnostic Tests

### 1. Port Discovery
- Automatically finds all available serial ports
- Tests common RPLIDAR ports (COM ports on Windows, /dev/ttyUSB* on Linux)

### 2. Communication Tests (per port/baudrate combination)
- **Raw Communication**: Basic serial read/write test
- **Device Info Request**: Gets RPLIDAR model, firmware, hardware info
- **Health Check**: Checks device status and error codes
- **Scan Start**: Attempts to start scanning and receive data points

### 3. Baudrate Testing
Tests common RPLIDAR baudrates:
- 115200 (standard)
- 256000 (common for newer models)
- 230400
- 460800
- 921600

## Understanding Results

### ✅ Working Configuration
- All tests pass
- Scan data is successfully received
- Ready for use in Python scripts

### ⚠️ Partial Configuration
- Basic communication works
- Device responds to info/health requests
- Scanning fails (protocol issue)

### ❌ Failed Configuration
- No communication detected
- Hardware or connection issue

## Generated Files

After running the diagnostic, you'll get:

1. **`rplidar_diagnostic_results.json`** - Raw diagnostic data
2. **`rplidar_config.py`** - Python configuration with working settings
3. **`rplidar_verified_test.py`** - Test script using verified settings

## Common Issues and Solutions

### Issue: "Descriptor length mismatch"
**Cause**: Python library protocol handling issue
**Solution**: The C++ tool bypasses this by using raw serial communication

### Issue: No serial ports found
**Cause**: Device not connected or drivers missing
**Solutions**:
- Check USB connection
- Install device drivers
- Check Device Manager (Windows) or `dmesg` (Linux)

### Issue: Partial communication only
**Cause**: Wrong baudrate or protocol timing
**Solutions**:
- Use the C++ tool's working configuration
- Add delays between commands in Python code
- Reset device between attempts

### Issue: Build fails
**Solutions**:
- **Windows**: Install MinGW-w64 or MSYS2
- **Linux**: Install build-essential (`sudo apt install build-essential`)
- Check that g++ is in your PATH

## Integration with Existing Code

Once you have working settings from the diagnostic:

### Update Environment Variables
```python
import os
from rplidar_config import RPLIDAR_PORT, RPLIDAR_BAUD

os.environ["RPLIDAR_PORT"] = RPLIDAR_PORT
os.environ["RPLIDAR_BAUD"] = str(RPLIDAR_BAUD)
```

### Use in Your Scripts
```python
# In your existing RPLIDAR scripts
from rplidar_config import RPLIDAR_PORT, RPLIDAR_BAUD
from rplidar import RPLidar

lidar = RPLidar(RPLIDAR_PORT, baudrate=RPLIDAR_BAUD, timeout=2)
```

### Recommended Python Code Improvements
Based on diagnostic results, add these to your Python code:

```python
import time
from rplidar import RPLidar

def connect_rplidar_robust(port, baudrate, max_retries=3):
    """Robust RPLIDAR connection with retries"""
    for attempt in range(max_retries):
        try:
            lidar = RPLidar(port, baudrate=baudrate, timeout=2)
            
            # Test connection
            info = lidar.get_info()
            health = lidar.get_health()
            
            print(f"✅ RPLIDAR connected: {info.model}")
            return lidar
            
        except Exception as e:
            print(f"❌ Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait before retry
            else:
                raise
    
    return None
```

## Advanced Usage

### Custom Port Testing
```bash
# Test specific port only
echo '{"target_ports": ["/dev/ttyUSB0"], "baudrates": [256000]}' > test_config.json
```

### Verbose Output
The C++ tool automatically provides detailed output and saves everything to JSON for later analysis.

### Integration with CI/CD
The tool returns appropriate exit codes and can be integrated into automated testing pipelines.

## Troubleshooting Hardware

If the C++ diagnostic finds no working configurations:

1. **Check Physical Connection**
   - USB cable integrity
   - Power supply (5V, adequate current)
   - Try different USB port

2. **Check System Recognition**
   - Windows: Device Manager > Ports (COM & LPT)
   - Linux: `dmesg | grep -i usb` and `ls -la /dev/ttyUSB*`

3. **Test with Different Computer**
   - Rule out host system issues

4. **Contact Manufacturer**
   - If device is new and no configurations work

## Next Steps

1. **Run the diagnostic**: `rplidar_cpp_diagnostic.exe`
2. **Analyze results**: `python rplidar_results_analyzer.py`
3. **Update your Python scripts** with the working configuration
4. **Test with verified script**: `python rplidar_verified_test.py`

The C++ approach should resolve the "Descriptor length mismatch" issue by providing direct hardware access and generating verified working configurations for your Python code.
