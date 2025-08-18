#!/usr/bin/env python3
"""
Maxbotix I2C EZ4 Ultrasonic Sensor Integration
Configured for ArduPilot: RNGFND_TYPE = 2, RNGFND_MAX = 700cm
"""

import os
import time
import json
import boto3
import smbus2 as smbus

AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
# Connect to existing EC2 DynamoDB
DDB_ENDPOINT_URL = os.getenv("DDB_ENDPOINT_URL", None)
ULTRASONIC_TABLE = os.getenv("ULTRASONIC_TABLE_NAME", "UGVUltrasonic")
DEVICE_ID = os.getenv("DEVICE_ID", "ugv-1")

# Maxbotix I2C EZ4 Configuration
I2C_BUS = int(os.getenv("I2C_BUS", "1"))  # Usually 1 on Raspberry Pi
I2C_ADDRESS = int(os.getenv("MAXBOTIX_I2C_ADDRESS", "0x70"), 16)  # Default address
MAX_DISTANCE_CM = int(os.getenv("RNGFND_MAX", "700"))  # ArduPilot setting

# DynamoDB setup - connect to existing EC2 instance
if DDB_ENDPOINT_URL:
    # Local development fallback
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION, endpoint_url=DDB_ENDPOINT_URL)
else:
    # Production: connect to existing EC2 DynamoDB
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

ultrasonic_table = dynamodb.Table(ULTRASONIC_TABLE)


class MaxbotixI2CEZ4:
    """Maxbotix I2C EZ4 Ultrasonic Sensor Driver"""
    
    def __init__(self, bus_num, address):
        self.bus = smbus.SMBus(bus_num)
        self.address = address
        self.max_distance_cm = MAX_DISTANCE_CM
        
    def read_distance(self):
        """Read distance from Maxbotix I2C EZ4 sensor"""
        try:
            # Send range command (0x51)
            self.bus.write_byte(self.address, 0x51)
            time.sleep(0.1)  # Wait for measurement
            
            # Read 2 bytes (high byte, low byte)
            data = self.bus.read_i2c_block_data(self.address, 0x00, 2)
            
            if len(data) == 2:
                # Combine high and low bytes
                distance_cm = (data[0] << 8) + data[1]
                
                # Validate distance (should be within sensor range)
                if 0 <= distance_cm <= self.max_distance_cm:
                    return distance_cm
                else:
                    print(f"⚠️ Distance out of range: {distance_cm}cm (max: {self.max_distance_cm}cm)")
                    return None
            else:
                print(f"⚠️ Invalid data length: {len(data)} bytes")
                return None
                
        except Exception as e:
            print(f"❌ Error reading ultrasonic sensor: {e}")
            return None
    
    def close(self):
        """Close I2C bus connection"""
        try:
            self.bus.close()
        except:
            pass


def publish_ultrasonic_data(distance_cm: float, timestamp: int) -> None:
    """Publish ultrasonic sensor data to DynamoDB"""
    item = {
        "device_id": DEVICE_ID,
        "timestamp": timestamp,
        "distance_cm": distance_cm,
        "distance_m": round(distance_cm / 100, 2),
        "sensor_type": "Maxbotix_I2C_EZ4",
        "ardupilot_config": {
            "RNGFND_TYPE": 2,
            "RNGFND_MAX": MAX_DISTANCE_CM
        },
        "status": "normal" if distance_cm > 0 else "error"
    }
    
    ultrasonic_table.put_item(Item=item)
    print(f"📡 Published ultrasonic data: {distance_cm}cm")


def main():
    print(f"🔍 Starting Maxbotix I2C EZ4 Ultrasonic Sensor Integration")
    print(f"📡 Connecting to existing EC2 DynamoDB: {ULTRASONIC_TABLE}")
    print(f"⚙️ ArduPilot Config: RNGFND_TYPE=2, RNGFND_MAX={MAX_DISTANCE_CM}cm")
    
    try:
        # Initialize ultrasonic sensor
        sensor = MaxbotixI2CEZ4(I2C_BUS, I2C_ADDRESS)
        print(f"✅ Ultrasonic sensor initialized on I2C bus {I2C_BUS}, address 0x{I2C_ADDRESS:02X}")
        
        last_publish = 0
        publish_interval = 0.5  # 2Hz update rate
        
        while True:
            try:
                current_time = time.time()
                
                # Read distance from sensor
                distance = sensor.read_distance()
                
                if distance is not None:
                    # Publish data at specified interval
                    if current_time - last_publish >= publish_interval:
                        publish_ultrasonic_data(distance, int(current_time))
                        last_publish = current_time
                        
                        # Log distance for monitoring
                        if distance < 50:  # Close object warning
                            print(f"⚠️ Close object detected: {distance}cm")
                        elif distance < 100:  # Medium distance
                            print(f"📏 Medium distance: {distance}cm")
                        else:
                            print(f"📏 Distance: {distance}cm")
                
                time.sleep(0.1)  # Small delay between readings
                
            except KeyboardInterrupt:
                print("\n⏹️ Stopping ultrasonic sensor...")
                break
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                time.sleep(1)
                
    except Exception as e:
        print(f"❌ Failed to initialize ultrasonic sensor: {e}")
        print("💡 Check I2C bus number and sensor address")
        print("💡 Ensure sensor is properly connected and powered")
    finally:
        try:
            sensor.close()
            print("✅ Ultrasonic sensor disconnected")
        except:
            pass


if __name__ == "__main__":
    main()
