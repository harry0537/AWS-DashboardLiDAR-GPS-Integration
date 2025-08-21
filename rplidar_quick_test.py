#!/usr/bin/env python3
"""
Quick RPLIDAR Test - Simple diagnostic for /dev/ttyUSB0
"""

import os
import sys
import time
import serial

def test_rplidar_simple():
    """Simple RPLIDAR test"""
    port = "/dev/ttyUSB0"
    baudrates = [115200, 256000, 230400, 460800, 921600]
    
    print("🚀 Quick RPLIDAR Test")
    print("=" * 30)
    print(f"Testing port: {port}")
    
    for baudrate in baudrates:
        print(f"\n📡 Testing {baudrate} baud...")
        
        try:
            # Test basic serial communication
            ser = serial.Serial(port, baudrate, timeout=2)
            print(f"   ✅ Serial connection OK")
            
            # Send RESET command
            ser.write(b'\xA5\x40')
            time.sleep(1)
            
            # Send GET_INFO command  
            ser.write(b'\xA5\x50')
            time.sleep(1)
            
            # Check for response
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"   📊 Response: {len(response)} bytes")
                print(f"   📋 Data: {response.hex()[:40]}...")
            else:
                print(f"   ❌ No response")
            
            ser.close()
            
        except Exception as e:
            print(f"   ❌ Error: {e}")

def test_with_library():
    """Test with rplidar library"""
    print(f"\n📚 Testing with rplidar library...")
    
    try:
        from rplidar import RPLidar
    except ImportError:
        print("   ❌ rplidar library not installed")
        print("   💡 Install with: pip3 install rplidar-roboticia")
        return False
    
    port = "/dev/ttyUSB0"
    baudrates = [115200, 256000, 230400]
    
    for baudrate in baudrates:
        print(f"\n🔧 Library test {baudrate} baud...")
        
        try:
            lidar = RPLidar(port, baudrate=baudrate, timeout=3)
            
            # Get device info
            info = lidar.get_info()
            print(f"   ✅ Device Info: Model {info.model}, FW {info.firmware}")
            
            # Get health
            health = lidar.get_health()
            print(f"   🏥 Health: Status {health.status}")
            
            # Try scanning
            print(f"   📡 Testing scan...")
            lidar.start_motor()
            time.sleep(2)
            
            try:
                scan = next(lidar.iter_scans(max_buf_meas=1000))
                valid_points = [p for p in scan if p[2] > 0]
                print(f"   🎉 SUCCESS! Got {len(valid_points)} scan points")
                
                # Show sample points
                if valid_points:
                    for i in range(min(3, len(valid_points))):
                        quality, angle, distance = valid_points[i]
                        print(f"      Point {i+1}: {angle:.1f}°, {distance:.0f}mm, Q{quality}")
                
                lidar.stop_motor()
                lidar.disconnect()
                
                print(f"\n✅ WORKING CONFIGURATION FOUND!")
                print(f"   Port: {port}")
                print(f"   Baudrate: {baudrate}")
                return True
                
            except Exception as scan_error:
                print(f"   ❌ Scan failed: {scan_error}")
                lidar.stop_motor()
                lidar.disconnect()
                
        except Exception as e:
            print(f"   ❌ Library error: {e}")
    
    return False

if __name__ == "__main__":
    print("Testing RPLIDAR on Raspberry Pi")
    
    # Test 1: Raw serial communication
    test_rplidar_simple()
    
    # Test 2: Python library
    success = test_with_library()
    
    if success:
        print(f"\n🎉 RPLIDAR is working!")
    else:
        print(f"\n❌ RPLIDAR tests failed")
        print(f"💡 This is likely the 'descriptor length mismatch' issue")
