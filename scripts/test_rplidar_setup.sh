#!/bin/bash
# Quick RPLIDAR Setup Test Script for Raspberry Pi
# This script tests if the basic setup is working

echo "🔍 RPLIDAR Setup Test Script"
echo "============================"
echo ""

# Test 1: Check if we're in the right directory
echo "✅ Test 1: Directory Check"
if [ -f "rplidar_build_linux.sh" ]; then
    echo "   Found rplidar_build_linux.sh"
else
    echo "   ❌ rplidar_build_linux.sh not found"
    echo "   Make sure you're in the AWS-Dashboard/scripts directory"
    exit 1
fi

if [ -f "rplidar_s3_capture_linux.sh" ]; then
    echo "   Found rplidar_s3_capture_linux.sh"
else
    echo "   ❌ rplidar_s3_capture_linux.sh not found"
    exit 1
fi
echo ""

# Test 2: Check dependencies
echo "✅ Test 2: Dependencies Check"
if command -v make &> /dev/null; then
    echo "   Found make: $(which make)"
else
    echo "   ❌ make not found - run: sudo apt install build-essential"
    exit 1
fi

if command -v g++ &> /dev/null; then
    echo "   Found g++: $(which g++)"
else
    echo "   ❌ g++ not found - run: sudo apt install build-essential"
    exit 1
fi

if command -v git &> /dev/null; then
    echo "   Found git: $(which git)"
else
    echo "   ❌ git not found - run: sudo apt install git"
    exit 1
fi
echo ""

# Test 3: Check permissions
echo "✅ Test 3: Script Permissions"
if [ -x "rplidar_build_linux.sh" ]; then
    echo "   rplidar_build_linux.sh is executable"
else
    echo "   ❌ rplidar_build_linux.sh is not executable"
    echo "   Run: chmod +x rplidar_build_linux.sh"
    exit 1
fi

if [ -x "rplidar_s3_capture_linux.sh" ]; then
    echo "   rplidar_s3_capture_linux.sh is executable"
else
    echo "   ❌ rplidar_s3_capture_linux.sh is not executable"
    echo "   Run: chmod +x rplidar_s3_capture_linux.sh"
    exit 1
fi
echo ""

# Test 4: Check RPLIDAR SDK directory
echo "✅ Test 4: RPLIDAR SDK Check"
if [ -d "../rplidar_sdk_dev" ]; then
    echo "   Found RPLIDAR SDK directory"
    if [ -f "../rplidar_sdk_dev/Makefile" ]; then
        echo "   Found Makefile"
    else
        echo "   ❌ Makefile not found in SDK directory"
    fi
else
    echo "   ❌ RPLIDAR SDK directory not found"
    echo "   Make sure you cloned the complete repository"
    exit 1
fi
echo ""

# Test 5: Check serial devices
echo "✅ Test 5: Serial Device Check"
echo "   Available serial devices:"
if ls /dev/ttyUSB* 1> /dev/null 2>&1; then
    for device in /dev/ttyUSB*; do
        if [ -c "$device" ]; then
            echo "     ✅ $device (USB Serial)"
        fi
    done
else
    echo "     ❌ No /dev/ttyUSB* devices found"
fi

if ls /dev/ttyACM* 1> /dev/null 2>&1; then
    for device in /dev/ttyACM*; do
        if [ -c "$device" ]; then
            echo "     ✅ $device (ACM Serial)"
        fi
    done
else
    echo "     ❌ No /dev/ttyACM* devices found"
fi
echo ""

# Test 6: Check user groups
echo "✅ Test 6: User Permissions Check"
if groups $USER | grep -q dialout; then
    echo "   User $USER is in dialout group"
else
    echo "   ❌ User $USER is NOT in dialout group"
    echo "   Run: sudo usermod -a -G dialout $USER"
    echo "   Then logout and login again"
fi
echo ""

echo "🎯 All tests completed!"
echo ""
echo "Next steps:"
echo "1. If all tests passed, run: ./rplidar_build_linux.sh"
echo "2. After building, run: ./rplidar_s3_capture_linux.sh --list-ports"
echo "3. Connect your RPLIDAR and start capturing data!"
echo ""
echo "🏁 Test script completed!"
