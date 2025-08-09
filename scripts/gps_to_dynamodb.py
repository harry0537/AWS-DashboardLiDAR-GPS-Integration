import os
import time
import math
import json
import boto3
import serial
import pynmea2
from datetime import datetime, timezone

AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
DDB_ENDPOINT_URL = os.getenv("DDB_ENDPOINT_URL", "http://localhost:8000")
TABLE_NAME = os.getenv("DDB_TABLE_NAME", "UGVTelemetry")
DEVICE_ID = os.getenv("DEVICE_ID", "ugv-1")
GPS_SERIAL_PORT = os.getenv("GPS_SERIAL_PORT", "COM3")
GPS_BAUD = int(os.getenv("GPS_BAUD", "115200"))

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION, endpoint_url=DDB_ENDPOINT_URL)
telemetry_table = dynamodb.Table(TABLE_NAME)


def knots_to_kmh(knots: float) -> float:
    return knots * 1.852 if knots is not None else 0.0


def parse_nmea_line(line: str, state: dict) -> None:
    try:
        msg = pynmea2.parse(line, check=True)
    except Exception:
        return

    if msg.sentence_type == "GGA":
        # Provides lat, lon, fix quality, number of satellites, HDOP and altitude
        if msg.lat and msg.lon:
            state["lat"] = msg.latitude
            state["lon"] = msg.longitude
        try:
            state["gps_accuracy_hdop"] = float(msg.horizontal_dil)
        except Exception:
            pass
    elif msg.sentence_type == "RMC":
        # Provides speed over ground (knots) and course over ground (deg)
        try:
            sog_knots = float(msg.spd_over_grnd) if msg.spd_over_grnd else 0.0
            state["speed"] = round(knots_to_kmh(sog_knots), 3)
        except Exception:
            pass
        try:
            state["heading"] = float(msg.true_course) if msg.true_course else None
        except Exception:
            pass
    elif msg.sentence_type == "VTG":
        try:
            state["heading"] = float(msg.true_track) if msg.true_track else state.get("heading")
        except Exception:
            pass


def publish_state(state: dict) -> None:
    if "lat" not in state or "lon" not in state:
        return
    timestamp = int(time.time())
    item = {
        "device_id": DEVICE_ID,
        "timestamp": timestamp,
        "lat": float(state.get("lat")),
        "lon": float(state.get("lon")),
        "speed": float(state.get("speed", 0.0)),
        "heading": float(state.get("heading", 0.0)),
    }
    if "gps_accuracy_hdop" in state:
        item["gps_accuracy_hdop"] = float(state["gps_accuracy_hdop"])  # lower is better

    telemetry_table.put_item(Item=item)
    print(f"Published telemetry: {json.dumps(item)}")


def main():
    print(f"Opening GPS serial {GPS_SERIAL_PORT} @ {GPS_BAUD} ...")
    with serial.Serial(GPS_SERIAL_PORT, GPS_BAUD, timeout=1) as ser:
        state = {}
        last_publish = 0
        while True:
            try:
                line = ser.readline().decode(errors="ignore").strip()
                if not line:
                    continue
                if not line.startswith("$"):
                    continue
                parse_nmea_line(line, state)
                now = time.time()
                # Throttle publishing to 1 Hz
                if now - last_publish >= 1 and "lat" in state and "lon" in state:
                    publish_state(state)
                    last_publish = now
            except KeyboardInterrupt:
                print("Stopping GPS reader...")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(0.5)


if __name__ == "__main__":
    main() 