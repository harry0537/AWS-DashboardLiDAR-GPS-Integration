#!/usr/bin/env python3
"""
Quick Sensor Status Checker
Shows current status of GPS, LiDAR, and API services
"""

import os
import time
import subprocess
import requests
from datetime import datetime

def check_service_status(service_name):
    """Check if a systemd service is running"""
    try:
        result = subprocess.run(['systemctl', 'is-active', service_name], 
                              capture_output=True, text=True)
        return result.stdout.strip() == 'active'
    except Exception:
        return False

def check_usb_devices():
    """Check for USB serial devices"""
    try:
        result = subprocess.run(['ls', '/dev/ttyUSB*'], 
                              capture_output=True, text=True)
        devices = result.stdout.strip().split('\n') if result.stdout.strip() else []
        return [d for d in devices if d]  # Filter out empty strings
    except Exception:
        return []

def check_api_status():
    """Check if the dashboard API is responding"""
    try:
        response = requests.get('http://localhost:5000/api/telemetry/latest', timeout=5)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except Exception:
        return False, None

def main():
    print("🔍 AWS Dashboard Sensor Status Check")
    print("=" * 40)
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check services
    print("🔄 Service Status:")
    services = ['gps-sensor.service', 'lidar-sensor.service', 'dashboard-api.service']
    for service in services:
        status = "✅ Running" if check_service_status(service) else "❌ Stopped"
        print(f"   {service}: {status}")
    
    print()
    
    # Check USB devices
    print("🔌 USB Devices:")
    devices = check_usb_devices()
    if devices:
        for device in devices:
            print(f"   ✅ {device}")
    else:
        print("   ❌ No USB serial devices found")
    
    print()
    
    # Check API
    print("🌐 API Status:")
    api_ok, data = check_api_status()
    if api_ok:
        print("   ✅ API responding")
        if data:
            print(f"   📡 Last GPS: {data.get('lat', 'N/A')}, {data.get('lon', 'N/A')}")
            print(f"   🚗 Speed: {data.get('speed', 'N/A')} km/h")
            print(f"   🧭 Heading: {data.get('heading', 'N/A')}°")
            print(f"   📍 Accuracy: {data.get('gps_accuracy_hdop', 'N/A')} HDOP")
    else:
        print("   ❌ API not responding")
    
    print()
    
    # Summary
    print("📊 Summary:")
    service_count = sum(1 for service in services if check_service_status(service))
    device_count = len(devices)
    
    if service_count == 3 and device_count >= 1 and api_ok:
        print("   🎉 All systems operational!")
    elif service_count == 3 and api_ok:
        print("   ⚠️ Services running but no sensors detected")
    elif service_count < 3:
        print("   ❌ Some services not running")
    else:
        print("   ⚠️ Mixed status - check individual components")
    
    print()
    print("💡 For detailed testing, run: python test_sensors.py")
    print("💡 For monitoring, run: ~/monitor_sensors.sh")

if __name__ == "__main__":
    main() 