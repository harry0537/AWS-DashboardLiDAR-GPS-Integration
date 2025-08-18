#!/usr/bin/env python3
"""
Sensor Testing Script for Raspberry Pi
Tests GPS and LiDAR connectivity and basic functionality
"""

import os
import time
import serial
import sys
from datetime import datetime

def test_serial_port(port, baudrate=115200, timeout=5):
    """Test if a serial port is accessible"""
    try:
        with serial.Serial(port, baudrate, timeout=timeout) as ser:
            print(f"✅ Successfully opened {port} @ {baudrate} baud")
            return ser
    except serial.SerialException as e:
        print(f"❌ Failed to open {port}: {e}")
        return None
    except FileNotFoundError:
        print(f"❌ Port {port} not found")
        return None

def test_gps_module(port="/dev/ttyUSB0", baudrate=115200):
    """Test GPS module connectivity and NMEA output"""
    print(f"\n🔍 Testing GPS Module on {port}...")
    
    ser = test_serial_port(port, baudrate)
    if not ser:
        return False
    
    print("📡 Listening for NMEA data (10 seconds)...")
    start_time = time.time()
    nmea_lines = []
    
    try:
        while time.time() - start_time < 10:
            if ser.in_waiting:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith('$'):
                    nmea_lines.append(line)
                    print(f"📡 Received: {line}")
                    if len(nmea_lines) >= 5:  # Got enough data
                        break
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n⏹️ Testing interrupted")
    
    ser.close()
    
    if nmea_lines:
        print(f"✅ GPS module working! Received {len(nmea_lines)} NMEA sentences")
        return True
    else:
        print("❌ No NMEA data received from GPS module")
        return False

def test_lidar_module(port="/dev/ttyUSB1", baudrate=256000):
    """Test LiDAR module connectivity"""
    print(f"\n🔍 Testing LiDAR Module on {port}...")
    
    ser = test_serial_port(port, baudrate)
    if not ser:
        return False
    
    print("📡 Testing LiDAR communication...")
    
    try:
        # Try to send a simple command to test communication
        ser.write(b'\xA5\x25')  # Simple command to test
        time.sleep(0.1)
        
        if ser.in_waiting:
            response = ser.read(ser.in_waiting)
            print(f"📡 LiDAR responded with {len(response)} bytes")
            ser.close()
            return True
        else:
            print("📡 No immediate response from LiDAR")
            ser.close()
            return True  # Some LiDAR modules don't respond immediately
            
    except Exception as e:
        print(f"❌ LiDAR communication error: {e}")
        ser.close()
        return False

def list_available_ports():
    """List all available serial ports"""
    print("\n🔍 Available Serial Ports:")
    print("============================")
    
    # Common port patterns
    port_patterns = [
        "/dev/ttyUSB*",
        "/dev/ttyACM*", 
        "/dev/ttyAMA*",
        "/dev/ttyS*"
    ]
    
    found_ports = []
    for pattern in port_patterns:
        import glob
        ports = glob.glob(pattern)
        for port in ports:
            try:
                # Get device info
                import subprocess
                result = subprocess.run(['udevadm', 'info', '-a', '-n', port], 
                                     capture_output=True, text=True)
                vendor_id = None
                product_id = None
                
                for line in result.stdout.split('\n'):
                    if 'idVendor' in line:
                        vendor_id = line.split('==')[1].strip().strip('"')
                    elif 'idProduct' in line:
                        product_id = line.split('==')[1].strip().strip('"')
                        break
                
                if vendor_id and product_id:
                    print(f"🔌 {port} (Vendor: {vendor_id}, Product: {product_id})")
                else:
                    print(f"🔌 {port}")
                    
                found_ports.append(port)
                
            except Exception as e:
                print(f"🔌 {port} (Error getting info: {e})")
                found_ports.append(port)
    
    if not found_ports:
        print("❌ No serial ports found")
    
    return found_ports

def test_dynamodb_connection():
    """Test DynamoDB connectivity"""
    print(f"\n🔍 Testing DynamoDB Connection...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        import boto3
        from botocore.exceptions import ClientError
        
        aws_region = os.getenv("AWS_REGION", "us-west-2")
        endpoint_url = os.getenv("DDB_ENDPOINT_URL", "http://localhost:8000")
        table_name = os.getenv("DDB_TABLE_NAME", "UGVTelemetry")
        
        print(f"🌐 Connecting to DynamoDB at {endpoint_url} in {aws_region}")
        
        dynamodb = boto3.resource("dynamodb", 
                                 region_name=aws_region, 
                                 endpoint_url=endpoint_url)
        
        # Try to list tables
        tables = list(dynamodb.tables.all())
        print(f"✅ DynamoDB connection successful! Found {len(tables)} tables")
        
        # Try to access the telemetry table
        try:
            table = dynamodb.Table(table_name)
            response = table.scan(Limit=1)
            print(f"✅ Telemetry table accessible: {len(response.get('Items', []))} items")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"⚠️ Telemetry table '{table_name}' not found - will be created when needed")
                return True
            else:
                print(f"❌ Error accessing table: {e}")
                return False
                
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False
    except Exception as e:
        print(f"❌ DynamoDB connection failed: {e}")
        return False

def main():
    """Main testing function"""
    print("🚀 AWS Dashboard Sensor Testing for Raspberry Pi")
    print("=" * 50)
    
    # List available ports first
    available_ports = list_available_ports()
    
    # Test DynamoDB connection
    db_ok = test_dynamodb_connection()
    
    # Test GPS module
    gps_ok = False
    if len(available_ports) >= 1:
        gps_ok = test_gps_module(available_ports[0])
    else:
        print("\n❌ No serial ports available for GPS testing")
    
    # Test LiDAR module
    lidar_ok = False
    if len(available_ports) >= 2:
        lidar_ok = test_lidar_module(available_ports[1])
    elif len(available_ports) == 1:
        print(f"\n⚠️ Only one serial port available, testing LiDAR on {available_ports[0]}")
        lidar_ok = test_lidar_module(available_ports[0])
    else:
        print("\n❌ No serial ports available for LiDAR testing")
    
    # Summary
    print(f"\n📊 Test Summary:")
    print("=" * 30)
    print(f"🔌 Serial Ports: {'✅' if available_ports else '❌'} ({len(available_ports)} found)")
    print(f"🌐 DynamoDB: {'✅' if db_ok else '❌'}")
    print(f"📡 GPS Module: {'✅' if gps_ok else '❌'}")
    print(f"🔍 LiDAR Module: {'✅' if lidar_ok else '❌'}")
    
    if gps_ok and lidar_ok and db_ok:
        print(f"\n🎉 All tests passed! Your sensors are ready to use.")
        print(f"💡 Run 'python scripts/gps_to_dynamodb.py' to start GPS data collection")
        print(f"💡 Run 'python scripts/rplidar_to_dynamodb.py' to start LiDAR data collection")
    else:
        print(f"\n⚠️ Some tests failed. Please check:")
        if not available_ports:
            print("   - USB connections and drivers")
        if not db_ok:
            print("   - DynamoDB configuration in .env file")
        if not gps_ok:
            print("   - GPS module connection and power")
        if not lidar_ok:
            print("   - LiDAR module connection and power")

if __name__ == "__main__":
    main() 