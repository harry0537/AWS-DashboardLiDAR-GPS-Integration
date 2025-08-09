import os
import time
import boto3

AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
DDB_ENDPOINT_URL = os.getenv("DDB_ENDPOINT_URL", "http://localhost:8000")
TABLE_NAME = os.getenv("DDB_TABLE_NAME", "UGVTelemetry")
DEVICE_ID = os.getenv("DEVICE_ID", "ugv-1")


item = {
    "device_id": DEVICE_ID,
    "timestamp": int(time.time()),
    "lat": -36.848461,
    "lon": 174.763336,
    "speed": 2.5,
    "heading": 90.0,
    "gps_accuracy_hdop": 0.8,
}

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION, endpoint_url=DDB_ENDPOINT_URL)
telemetry_table = dynamodb.Table(TABLE_NAME)
telemetry_table.put_item(Item=item)
print("Seeded telemetry:", item) 