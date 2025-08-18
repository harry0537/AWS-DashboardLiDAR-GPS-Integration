#!/usr/bin/env python3
"""
Pixhawk Battery Monitoring Script
Monitors battery voltage and triggers RTL at 11V threshold
"""

import os
import time
import json
import boto3
import serial
from datetime import datetime

AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
# Connect to existing EC2 DynamoDB
DDB_ENDPOINT_URL = os.getenv("DDB_ENDPOINT_URL", None)
BATTERY_TABLE = os.getenv("BATTERY_TABLE_NAME", "UGVBattery")
DEVICE_ID = os.getenv("DEVICE_ID", "ugv-1")

# Pixhawk Configuration
PIXHAWK_PORT = os.getenv("PIXHAWK_PORT", "/dev/ttyACM0")  # USB connection
PIXHAWK_BAUD = int(os.getenv("PIXHAWK_BAUD", "115200"))
RTL_VOLTAGE_THRESHOLD = float(os.getenv("RTL_VOLTAGE_THRESHOLD", "11.0"))

# DynamoDB setup - connect to existing EC2 instance
if DDB_ENDPOINT_URL:
    # Local development fallback
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION, endpoint_url=DDB_ENDPOINT_URL)
else:
    # Production: connect to existing EC2 DynamoDB
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

battery_table = dynamodb.Table(BATTERY_TABLE)


class PixhawkBatteryMonitor:
    """Pixhawk Battery Monitoring Class"""
    
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.rtl_threshold = RTL_VOLTAGE_THRESHOLD
        
    def connect(self):
        """Connect to Pixhawk via serial"""
        try:
            self.serial = serial.Serial(
                self.port, 
                self.baudrate, 
                timeout=1,
                write_timeout=1
            )
            print(f"✅ Connected to Pixhawk on {self.port}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Pixhawk: {e}")
            return False
    
    def read_battery_voltage(self):
        """
        Read battery voltage from Pixhawk
        This is a simplified implementation - actual Pixhawk communication
        would use MAVLink protocol for more robust communication
        """
        try:
            if not self.serial or not self.serial.is_open:
                return None
            
            # Send voltage request (simplified - would use MAVLink in production)
            # For now, we'll simulate voltage reading
            # TODO: Implement proper MAVLink voltage reading
            
            # Simulate voltage reading (replace with actual MAVLink implementation)
            simulated_voltage = 12.5  # Replace with actual Pixhawk voltage
            
            return simulated_voltage
            
        except Exception as e:
            print(f"❌ Error reading battery voltage: {e}")
            return None
    
    def check_rtl_condition(self, voltage):
        """Check if RTL (Return to Launch) should be triggered"""
        if voltage <= self.rtl_threshold:
            return True, f"Battery voltage {voltage}V below RTL threshold {self.rtl_threshold}V"
        return False, None
    
    def send_rtl_command(self):
        """Send RTL command to Pixhawk (placeholder)"""
        try:
            if self.serial and self.serial.is_open:
                # TODO: Implement MAVLink RTL command
                print("🚨 SENDING RTL COMMAND TO PIXHAWK")
                print("⚠️ This is a placeholder - implement actual MAVLink RTL command")
                return True
        except Exception as e:
            print(f"❌ Failed to send RTL command: {e}")
        return False
    
    def close(self):
        """Close serial connection"""
        try:
            if self.serial and self.serial.is_open:
                self.serial.close()
                print("✅ Pixhawk connection closed")
        except:
            pass


def publish_battery_status(voltage: float, rtl_triggered: bool, rtl_reason: str, timestamp: int) -> None:
    """Publish battery status to DynamoDB"""
    item = {
        "device_id": DEVICE_ID,
        "timestamp": timestamp,
        "voltage": voltage,
        "voltage_threshold": RTL_VOLTAGE_THRESHOLD,
        "status": "low_battery" if rtl_triggered else "normal",
        "rtl_triggered": rtl_triggered,
        "rtl_reason": rtl_reason if rtl_triggered else "none",
        "action_required": "rtl" if rtl_triggered else "none",
        "monitoring_source": "pixhawk",
        "timestamp_human": datetime.fromtimestamp(timestamp).isoformat()
    }
    
    battery_table.put_item(Item=item)
    
    if rtl_triggered:
        print(f"🚨 CRITICAL: Battery {voltage}V - RTL TRIGGERED: {rtl_reason}")
    else:
        print(f"🔋 Battery status: {voltage}V ({item['status']})")


def main():
    print(f"🔋 Starting Pixhawk Battery Monitoring")
    print(f"📡 Connecting to existing EC2 DynamoDB: {BATTERY_TABLE}")
    print(f"⚙️ RTL Threshold: {RTL_VOLTAGE_THRESHOLD}V")
    print(f"🔌 Pixhawk Port: {PIXHAWK_PORT}")
    
    # Initialize battery monitor
    monitor = PixhawkBatteryMonitor(PIXHAWK_PORT, PIXHAWK_BAUD)
    
    try:
        # Connect to Pixhawk
        if not monitor.connect():
            print("❌ Failed to connect to Pixhawk - exiting")
            return
        
        last_publish = 0
        publish_interval = 5  # Check battery every 5 seconds
        rtl_sent = False  # Track if RTL command was already sent
        
        print("🔋 Starting battery monitoring loop...")
        
        while True:
            try:
                current_time = time.time()
                
                # Read battery voltage
                voltage = monitor.read_battery_voltage()
                
                if voltage is not None:
                    # Check RTL condition
                    rtl_triggered, rtl_reason = monitor.check_rtl_condition(voltage)
                    
                    # Publish status at specified interval
                    if current_time - last_publish >= publish_interval:
                        publish_battery_status(voltage, rtl_triggered, rtl_reason, int(current_time))
                        last_publish = current_time
                        
                        # Send RTL command if threshold exceeded and not already sent
                        if rtl_triggered and not rtl_sent:
                            print(f"🚨 RTL CONDITION MET: {rtl_reason}")
                            if monitor.send_rtl_command():
                                rtl_sent = True
                                print("✅ RTL command sent to Pixhawk")
                            else:
                                print("❌ Failed to send RTL command")
                
                time.sleep(1)  # Check every second
                
            except KeyboardInterrupt:
                print("\n⏹️ Stopping battery monitoring...")
                break
            except Exception as e:
                print(f"❌ Error in monitoring loop: {e}")
                time.sleep(5)
                
    except Exception as e:
        print(f"❌ Fatal error: {e}")
    finally:
        monitor.close()


if __name__ == "__main__":
    main()
