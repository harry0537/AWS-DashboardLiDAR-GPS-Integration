#!/usr/bin/env python3
"""
RPLIDAR Library Compatibility Test
Tests multiple RPLIDAR libraries to find one compatible with your firmware
"""

import os
import sys
import time
import serial

def test_rplidar_roboticia(port, baudrate):
    """Test the rplidar-roboticia library"""
    print(f"\n📚 Testing rplidar-roboticia library...")
    
    try:
        from rplidar import RPLidar
        print(f"   ✅ Library imported successfully")
        
        lidar = RPLidar(port, baudrate=baudrate, timeout=3)
        print(f"   ✅ Connection established")
        
        # Test device info
        try:
            info = lidar.get_info()
            print(f"   🎉 SUCCESS! Device Info: Model {info.model}, FW {info.firmware}")
            return True
        except Exception as e:
            print(f"   ❌ Device info failed: {e}")
            
        # Test health
        try:
            health = lidar.get_health()
            print(f"   🎉 SUCCESS! Health: {health.status}")
            return True
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
        
        lidar.disconnect()
        return False
        
    except ImportError:
        print(f"   ❌ rplidar-roboticia not installed")
        return False
    except Exception as e:
        print(f"   ❌ Library test failed: {e}")
        return False

def test_rplidar_original(port, baudrate):
    """Test the original rplidar library"""
    print(f"\n📚 Testing original rplidar library...")
    
    try:
        import rplidar
        print(f"   ✅ Library imported successfully")
        
        lidar = rplidar.RPLidar(port, baudrate=baudrate, timeout=3)
        print(f"   ✅ Connection established")
        
        # Test device info
        try:
            info = lidar.get_info()
            print(f"   🎉 SUCCESS! Device Info: Model {info.model}, FW {info.firmware}")
            return True
        except Exception as e:
            print(f"   ❌ Device info failed: {e}")
            
        # Test health
        try:
            health = lidar.get_health()
            print(f"   🎉 SUCCESS! Health: {health.status}")
            return True
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
        
        lidar.disconnect()
        return False
        
    except ImportError:
        print(f"   ❌ Original rplidar not installed")
        return False
    except Exception as e:
        print(f"   ❌ Library test failed: {e}")
        return False

def test_rplidar_sdk(port, baudrate):
    """Test the rplidar_sdk library"""
    print(f"\n📚 Testing rplidar_sdk library...")
    
    try:
        from rplidar_sdk import RPLidar
        print(f"   ✅ Library imported successfully")
        
        lidar = RPLidar(port, baudrate=baudrate, timeout=3)
        print(f"   ✅ Connection established")
        
        # Test device info
        try:
            info = lidar.get_info()
            print(f"   🎉 SUCCESS! Device Info: Model {info.model}, FW {info.firmware}")
            return True
        except Exception as e:
            print(f"   ❌ Device info failed: {e}")
            
        # Test health
        try:
            health = lidar.get_health()
            print(f"   🎉 SUCCESS! Health: {health.status}")
            return True
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
        
        lidar.disconnect()
        return False
        
    except ImportError:
        print(f"   ❌ rplidar_sdk not installed")
        return False
    except Exception as e:
        print(f"   ❌ Library test failed: {e}")
        return False

def test_raw_protocol_variants(port, baudrate):
    """Test different protocol variants with raw serial"""
    print(f"\n🔧 Testing Raw Protocol Variants...")
    
    try:
        ser = serial.Serial(port, baudrate, timeout=2)
        print(f"   ✅ Serial connection established")
        
        # Test different command formats
        commands = [
            (b'\xA5\x40', 'RESET'),
            (b'\xA5\x50', 'GET_INFO'),
            (b'\xA5\x52', 'GET_HEALTH'),
            (b'\xA5\x25', 'START_SCAN'),
            (b'\xA5\x20', 'STOP_SCAN'),
            # Try some alternative command formats
            (b'\xA5\x40\x00', 'RESET_EXTENDED'),
            (b'\xA5\x50\x00', 'GET_INFO_EXTENDED'),
            (b'\xA5\x52\x00', 'GET_HEALTH_EXTENDED'),
        ]
        
        for cmd, name in commands:
            print(f"\n   🔧 Testing {name}: {cmd.hex()}")
            ser.write(cmd)
            time.sleep(0.5)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"      📊 Response: {len(response)} bytes")
                print(f"      📋 Data: {response.hex()}")
                
                # Try to interpret the response
                if len(response) >= 1:
                    if response[0] == 0xA5:
                        print(f"      ✅ Valid RPLIDAR response header")
                        if len(response) >= 2:
                            print(f"      📝 Command response: {response[1]:02x}")
                    else:
                        print(f"      ⚠️  Unexpected response header: {response[0]:02x}")
            else:
                print(f"      ❌ No response")
        
        ser.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Raw protocol test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 RPLIDAR Library Compatibility Test")
    print("=" * 50)
    
    port = "/dev/ttyUSB0"
    baudrate = 115200  # Start with standard baudrate
    
    print(f"Testing port: {port} at {baudrate} baud")
    print(f"Looking for compatible library...")
    
    # Test different libraries
    libraries = [
        ("rplidar-roboticia", test_rplidar_roboticia),
        ("original rplidar", test_rplidar_original),
        ("rplidar_sdk", test_rplidar_sdk)
    ]
    
    working_library = None
    
    for lib_name, test_func in libraries:
        print(f"\n{'='*50}")
        print(f"Testing {lib_name}...")
        
        if test_func(port, baudrate):
            working_library = lib_name
            print(f"\n🎉 SUCCESS! {lib_name} is compatible!")
            break
        else:
            print(f"❌ {lib_name} failed")
    
    # Test raw protocol variants
    print(f"\n{'='*50}")
    test_raw_protocol_variants(port, baudrate)
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 COMPATIBILITY TEST SUMMARY")
    print("=" * 50)
    
    if working_library:
        print(f"🎉 Compatible library found: {working_library}")
        print(f"\n💡 Use this library in your scripts:")
        if working_library == "rplidar-roboticia":
            print(f"   pip install rplidar-roboticia")
        elif working_library == "original rplidar":
            print(f"   pip install rplidar")
        elif working_library == "rplidar_sdk":
            print(f"   pip install rplidar_sdk")
    else:
        print(f"❌ No compatible libraries found")
        print(f"\n🔧 Next steps:")
        print(f"   1. Check RPLIDAR firmware version")
        print(f"   2. Try updating RPLIDAR firmware")
        print(f"   3. Check if device is actually a RPLIDAR")
        print(f"   4. Try different USB cable/port")

if __name__ == "__main__":
    main()
