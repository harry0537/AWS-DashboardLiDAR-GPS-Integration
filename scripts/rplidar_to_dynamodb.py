import os
import time
import json
import boto3
from rplidar import RPLidar

AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
# Connect to existing EC2 DynamoDB
DDB_ENDPOINT_URL = os.getenv("DDB_ENDPOINT_URL", None)
LIDAR_TABLE = os.getenv("EXISTING_LIDAR_TABLE_NAME", "UGVLidarScans")
DEVICE_ID = os.getenv("DEVICE_ID", "ugv-1")
RPLIDAR_PORT = os.getenv("RPLIDAR_PORT", "COM4")
RPLIDAR_BAUD = int(os.getenv("RPLIDAR_BAUD", "256000"))

# DynamoDB setup - connect to existing EC2 instance
if DDB_ENDPOINT_URL:
    # Local development fallback
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION, endpoint_url=DDB_ENDPOINT_URL)
else:
    # Production: connect to existing EC2 DynamoDB
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

lidar_table = dynamodb.Table(LIDAR_TABLE)


def get_object_distance(measurements):
    """
    Simplified LiDAR processing for ArduPilot object avoidance
    Only needs distance data - no complex SLAM/mapping required
    """
    # measurements: list of tuples (quality, angle, distance_mm)
    if not measurements:
        return None
    
    # Filter valid measurements and get closest object distance
    valid_distances = [m[2] for m in measurements if m[2] > 0 and m[1] > 0]
    
    if not valid_distances:
        return None
    
    # Return closest object distance (most critical for collision avoidance)
    closest_distance = min(valid_distances)
    
    return {
        "closest_distance_mm": closest_distance,
        "closest_distance_cm": round(closest_distance / 10, 1),
        "closest_distance_m": round(closest_distance / 1000, 2),
        "measurement_count": len(valid_distances),
        "timestamp": int(time.time())
    }


def main():
    print(f"🔍 Connecting to RPLIDAR on {RPLIDAR_PORT} for ArduPilot object avoidance...")
    print(f"📡 Connecting to existing EC2 DynamoDB: {LIDAR_TABLE}")
    
    try:
        lidar = RPLidar(RPLIDAR_PORT, baudrate=RPLIDAR_BAUD, timeout=1)
        print("✅ RPLIDAR connected successfully")
        
        for i, scan in enumerate(lidar.iter_scans(max_buf_meas=5000)):
            # Get simplified distance data for object avoidance
            distance_data = get_object_distance(scan)
            
            if distance_data:
                item = {
                    "device_id": DEVICE_ID,
                    "timestamp": int(time.time()),
                    "object_avoidance": distance_data,
                    "scan_quality": "basic",  # Simplified processing
                    "purpose": "ardupilot_collision_detection"
                }
                
                lidar_table.put_item(Item=item)
                print(f"📡 Published LiDAR data: Closest object at {distance_data['closest_distance_cm']}cm")
                
                # Throttle to 10Hz for ArduPilot compatibility
                time.sleep(0.1)
                
    except KeyboardInterrupt:
        print("\n⏹️ Stopping RPLIDAR reader...")
    except Exception as e:
        print(f"❌ RPLIDAR error: {e}")
    finally:
        try:
            lidar.stop()
            lidar.stop_motor()
            lidar.disconnect()
            print("✅ RPLIDAR disconnected")
        except:
            pass


if __name__ == "__main__":
    main() 