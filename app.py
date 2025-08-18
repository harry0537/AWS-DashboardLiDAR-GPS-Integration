from flask import Flask, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import boto3
from boto3.dynamodb.conditions import Key

app = Flask(__name__)
CORS(app)

# Environment-driven configuration for existing EC2 infrastructure
load_dotenv()
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
# Connect to existing EC2 DynamoDB (not local)
DDB_ENDPOINT_URL = os.getenv("DDB_ENDPOINT_URL", None)  # None = use AWS default
TELEM_TABLE = os.getenv("EXISTING_DDB_TABLE_NAME", "UGVTelemetry")
LIDAR_TABLE = os.getenv("EXISTING_LIDAR_TABLE_NAME", "UGVLidarScans")
ULTRASONIC_TABLE = os.getenv("ULTRASONIC_TABLE_NAME", "UGVUltrasonic")
BATTERY_TABLE = os.getenv("BATTERY_TABLE_NAME", "UGVBattery")
DEVICE_ID = os.getenv("DEVICE_ID", "ugv-1")

# DynamoDB setup - connect to existing EC2 instance
if DDB_ENDPOINT_URL:
    # Local development fallback
    _dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION, endpoint_url=DDB_ENDPOINT_URL)
else:
    # Production: connect to existing EC2 DynamoDB
    _dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

_telem_table = _dynamodb.Table(TELEM_TABLE)
_lidar_table = _dynamodb.Table(LIDAR_TABLE)
_ultrasonic_table = _dynamodb.Table(ULTRASONIC_TABLE)
_battery_table = _dynamodb.Table(BATTERY_TABLE)


@app.route("/api/telemetry")
def get_telemetry():
    # Retained for compatibility with existing dashboard
    response = _telem_table.scan()
    data = response.get("Items", [])
    return jsonify(data)


@app.route("/api/telemetry/latest")
def get_telemetry_latest():
    # Query latest by sort key timestamp for the device
    resp = _telem_table.query(
        KeyConditionExpression=Key("device_id").eq(DEVICE_ID),
        ScanIndexForward=False,
        Limit=1,
    )
    items = resp.get("Items", [])
    return jsonify(items[0] if items else {})


@app.route("/api/lidar/latest")
def get_lidar_latest():
    # Get latest LiDAR distance data for object avoidance
    resp = _lidar_table.query(
        KeyConditionExpression=Key("device_id").eq(DEVICE_ID),
        ScanIndexForward=False,
        Limit=1,
    )
    items = resp.get("Items", [])
    return jsonify(items[0] if items else {})


@app.route("/api/ultrasonic/latest")
def get_ultrasonic_latest():
    # Get latest ultrasonic sensor data (Maxbotix I2C EZ4)
    resp = _ultrasonic_table.query(
        KeyConditionExpression=Key("device_id").eq(DEVICE_ID),
        ScanIndexForward=False,
        Limit=1,
    )
    items = resp.get("Items", [])
    return jsonify(items[0] if items else {})


@app.route("/api/battery/latest")
def get_battery_latest():
    # Get latest battery status from Pixhawk
    resp = _battery_table.query(
        KeyConditionExpression=Key("device_id").eq(DEVICE_ID),
        ScanIndexForward=False,
        Limit=1,
    )
    items = resp.get("Items", [])
    return jsonify(items[0] if items else {})


@app.route("/api/status")
def get_system_status():
    # Overall system status endpoint
    try:
        # Check if we can access the existing DynamoDB tables
        _telem_table.load()
        _lidar_table.load()
        return jsonify({
            "status": "connected",
            "message": "Connected to existing EC2 DynamoDB infrastructure",
            "tables": {
                "telemetry": TELEM_TABLE,
                "lidar": LIDAR_TABLE,
                "ultrasonic": ULTRASONIC_TABLE,
                "battery": BATTERY_TABLE
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Connection error: {str(e)}",
            "tables": {}
        }), 500


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5000"))
    print(f"🚀 Starting AWS Dashboard API - connecting to existing EC2 infrastructure")
    print(f"📍 Region: {AWS_REGION}")
    print(f"🔗 DynamoDB: {'Local' if DDB_ENDPOINT_URL else 'EC2 Production'}")
    app.run(host=host, port=port)
