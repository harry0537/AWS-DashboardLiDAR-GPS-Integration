import os
import time
import json
from statistics import median
import boto3
from rplidar import RPLidar

AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
DDB_ENDPOINT_URL = os.getenv("DDB_ENDPOINT_URL", "http://localhost:8000")
LIDAR_TABLE = os.getenv("LIDAR_TABLE_NAME", "UGVLidarScans")
DEVICE_ID = os.getenv("DEVICE_ID", "ugv-1")
RPLIDAR_PORT = os.getenv("RPLIDAR_PORT", "COM4")
RPLIDAR_BAUD = int(os.getenv("RPLIDAR_BAUD", "256000"))


dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION, endpoint_url=DDB_ENDPOINT_URL)
lidar_table = dynamodb.Table(LIDAR_TABLE)


def summarize_scan(measurements):
    # measurements: list of tuples (quality, angle, distance_mm)
    distances = [m[2] for m in measurements if m[2] > 0]
    if not distances:
        return {"min": None, "max": None, "median": None}
    return {
        "min": min(distances),
        "max": max(distances),
        "median": median(distances),
    }


def main():
    print(f"Connecting to RPLIDAR on {RPLIDAR_PORT} ...")
    lidar = RPLidar(RPLIDAR_PORT, baudrate=RPLIDAR_BAUD, timeout=1)
    try:
        for i, scan in enumerate(lidar.iter_scans(max_buf_meas=5000)):
            # scan is a list of (quality, angle, distance)
            summary = summarize_scan(scan)
            item = {
                "device_id": DEVICE_ID,
                "timestamp": int(time.time()),
                "summary": summary,
            }
            lidar_table.put_item(Item=item)
            print(f"Published LiDAR summary: {json.dumps(item)}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Stopping RPLIDAR reader...")
    finally:
        lidar.stop()
        lidar.stop_motor()
        lidar.disconnect()


if __name__ == "__main__":
    main() 