from flask import Flask, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import boto3
from boto3.dynamodb.conditions import Key

app = Flask(__name__)
CORS(app)

# Environment-driven configuration
load_dotenv()
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
DDB_ENDPOINT_URL = os.getenv("DDB_ENDPOINT_URL", "http://localhost:8000")
TELEM_TABLE = os.getenv("DDB_TABLE_NAME", "UGVTelemetry")
LIDAR_TABLE = os.getenv("LIDAR_TABLE_NAME", "UGVLidarScans")
DEVICE_ID = os.getenv("DEVICE_ID", "ugv-1")

# DynamoDB setup
_dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION, endpoint_url=DDB_ENDPOINT_URL)
_telem_table = _dynamodb.Table(TELEM_TABLE)
_lidar_table = _dynamodb.Table(LIDAR_TABLE)


@app.route("/api/telemetry")
def get_telemetry():
    # Retained for compatibility; not efficient in production
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
    resp = _lidar_table.query(
        KeyConditionExpression=Key("device_id").eq(DEVICE_ID),
        ScanIndexForward=False,
        Limit=1,
    )
    items = resp.get("Items", [])
    return jsonify(items[0] if items else {})


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5000"))
    app.run(host=host, port=port)
