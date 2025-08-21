#!/usr/bin/env python3
"""
Enhanced RPLIDAR Diagnostic - Comprehensive testing for Raspberry Pi
Tests multiple baudrates, protocols, and provides hardware diagnostics
"""

import os
import sys
import time
import serial
import subprocess

def check_hardware():
    """Check hardware connections and USB devices"""
    print("🔍 Hardware Diagnostics")
    print("=" * 40)
    
    # Check USB devices
    try:
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        if result.returncode == 0:
            print("📱 USB Devices:")
            for line in result.stdout.strip().split('\n'):
                if 'lidar' in line.lower() or 'slamtec' in line.lower() or 'cp2102' in line.lower():
                    print(f"   🔴 RPLIDAR: {line}")
                else:
                    print(f"   📱 {line}")
        else:
            print("   ❌ Could not list USB devices")
    except Exception as e:
        print(f"   ❌ USB check failed: {e}")
    
    # Check serial ports
    print("\n🔌 Serial Ports:")
    try:
        result = subprocess.run(['ls', '-la', '/dev/ttyUSB*'], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    print(f"   {line}")
        else:
            print("   ❌ No /dev/ttyUSB* ports found")
    except Exception as e:
        print(f"   ❌ Serial port check failed: {e}")
    
    # Check system logs
    print("\n📋 System Logs (USB):")
    try:
        result = subprocess.run(['dmesg'], capture_output=True, text=True)
        if result.returncode == 0:
            usb_lines = [line for line in result.stdout.split('\n') if 'ttyusb' in line.lower() or 'usb' in line.lower()]
            for line in usb_lines[-5:]:  # Last 5 USB-related lines
                print(f"   {line}")
        else:
            print("   ❌ Could not read system logs")
    except Exception as e:
        print(f"   ❌ System log check failed: {e}")

def test_raw_communication(port, baudrate):
    """Test raw serial communication with RPLIDAR commands"""
    print(f"\n📡 Raw Communication Test - {baudrate} baud")
    print("-" * 50)
    
    try:
        ser = serial.Serial(port, baudrate, timeout=2)
        print(f"   ✅ Serial connection established")
        
        # Test different RPLIDAR commands
        commands = [
            (b'\xA5\x40', 'RESET'),
            (b'\xA5\x50', 'GET_INFO'),
            (b'\xA5\x52', 'GET_HEALTH'),
            (b'\xA5\x25', 'START_SCAN'),
            (b'\xA5\x20', 'STOP_SCAN')
        ]
        
        for cmd, name in commands:
            print(f"\n   🔧 Testing {name} command: {cmd.hex()}")
            ser.write(cmd)
            time.sleep(0.5)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"      📊 Response: {len(response)} bytes")
                print(f"      📋 Data: {response.hex()}")
                
                # Try to interpret the response
                if len(response) >= 2:
                    if response[0] == 0xA5:
                        print(f"      ✅ Valid RPLIDAR response header")
                    else:
                        print(f"      ⚠️  Unexpected response header: {response[0]:02x}")
            else:
                print(f"      ❌ No response")
        
        ser.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Raw communication failed: {e}")
        return False

def test_library_communication(port, baudrate):
    """Test communication using the rplidar library"""
    print(f"\n📚 Library Communication Test - {baudrate} baud")
    print("-" * 50)
    
    try:
        from rplidar import RPLidar
    except ImportError:
        print("   ❌ rplidar library not installed")
        print("   💡 Install with: pip install rplidar-roboticia")
        return False
    
    try:
        lidar = RPLidar(port, baudrate=baudrate, timeout=3)
        print(f"   ✅ Library connection established")
        
        # Get device info
        try:
            info = lidar.get_info()
            print(f"   📊 Device Info: Model {info.model}, FW {info.firmware}")
        except Exception as e:
            print(f"   ❌ Could not get device info: {e}")
        
        # Get health status
        try:
            health = lidar.get_health()
            print(f"   🏥 Health Status: {health.status}")
        except Exception as e:
            print(f"   ❌ Could not get health: {e}")
        
        # Test motor control
        try:
            print(f"   🔄 Testing motor...")
            lidar.start_motor()
            time.sleep(2)
            print(f"   ✅ Motor started successfully")
            
            # Try to get a scan
            try:
                print(f"   📡 Testing scan...")
                scan_generator = lidar.iter_scans(max_buf_meas=1000)
                scan = next(scan_generator)
                valid_points = [p for p in scan if p[2] > 0]
                print(f"   🎉 SUCCESS! Got {len(valid_points)} scan points")
                
                # Show sample points
                if valid_points:
                    for i in range(min(3, len(valid_points))):
                        quality, angle, distance = valid_points[i]
                        print(f"      Point {i+1}: {angle:.1f}°, {distance:.0f}mm, Q{quality}")
                
                lidar.stop_motor()
                lidar.disconnect()
                
                print(f"\n🎉 WORKING CONFIGURATION FOUND!")
                print(f"   Port: {port}")
                print(f"   Baudrate: {baudrate}")
                return True
                
            except Exception as scan_error:
                print(f"   ❌ Scan failed: {scan_error}")
                lidar.stop_motor()
                lidar.disconnect()
                
        except Exception as motor_error:
            print(f"   ❌ Motor control failed: {motor_error}")
            try:
                lidar.disconnect()
            except:
                pass
        
    except Exception as e:
        print(f"   ❌ Library communication failed: {e}")
    
    return False

def main():
    """Main diagnostic function"""
    print("🚀 Enhanced RPLIDAR Diagnostic for Raspberry Pi")
    print("=" * 60)
    
    # Check hardware first
    check_hardware()
    
    # Test ports
    ports = ['/dev/ttyUSB0', '/dev/ttyUSB1']
    baudrates = [115200, 256000, 230400, 460800, 921600]
    
    print(f"\n🔍 Testing Available Ports and Baudrates")
    print("=" * 60)
    
    working_config = None
    
    for port in ports:
        if os.path.exists(port):
            print(f"\n📍 Testing port: {port}")
            
            for baudrate in baudrates:
                print(f"\n{'='*60}")
                
                # Test raw communication
                raw_success = test_raw_communication(port, baudrate)
                
                # Test library communication
                lib_success = test_library_communication(port, baudrate)
                
                if lib_success:
                    working_config = (port, baudrate)
                    break
            
            if working_config:
                break
        else:
            print(f"\n❌ Port {port} not found")
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    if working_config:
        port, baudrate = working_config
        print(f"🎉 SUCCESS! Working configuration found:")
        print(f"   Port: {port}")
        print(f"   Baudrate: {baudrate}")
        print(f"\n💡 Use these settings in your scripts:")
        print(f"   RPLIDAR_PORT={port}")
        print(f"   RPLIDAR_BAUD={baudrate}")
    else:
        print(f"❌ No working configurations found!")
        print(f"\n🔧 Troubleshooting recommendations:")
        print(f"   1. Check USB cable and power supply")
        print(f"   2. Verify RPLIDAR model and firmware")
        print(f"   3. Try different USB ports on Raspberry Pi")
        print(f"   4. Check if RPLIDAR motor is spinning")
        print(f"   5. Verify 5V power supply (500mA+)")

if __name__ == "__main__":
    main()
