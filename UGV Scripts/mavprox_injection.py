#!/usr/bin/env python3

import subprocess
import threading
import time
import signal
import sys
from pymavlink import mavutil
import boto3
from datetime import datetime
from decimal import Decimal
from flask import Flask, Response
import pyrealsense2 as rs
import cv2
import numpy as np

# === Configuration Parameters ===
VEHICLE_PORT = "/dev/ttyS5"
BAUDRATE = 921600
GCS_IP = "10.244.181.224"
GCS_PORT = 14552
LOCAL_IP = "127.0.0.1"
LOCAL_OUTPUT_PORT = 14550
D4XX_SCRIPT = "d4xx_to_mavlink.py"
DYNAMODB_ENDPOINT = 'http://96.0.77.42:8000'
DYNAMODB_REGION = 'us-west-2'
AWS_ACCESS_KEY_ID = 'fakeMyKeyId'
AWS_SECRET_ACCESS_KEY = 'fakeSecretAccessKey'
DYNAMODB_TABLE = 'UGVTelemetry'
# NTRIP Connection params
NTRIP_CASTER = "10.244.77.204"
NTRIP_PORT = "2101"
MOUNTPOINT = "SerialBase"

exit_requested = False
flask_app = Flask(__name__)
pipeline = None

def gen_frames():
    ctx = rs.context()
    devices = ctx.query_devices()
    if len(devices) == 0:
        print("[ERROR] No RealSense devices found.")
        return

    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

    try:
        pipeline.start(config)
        print("[INFO] RealSense pipeline for Flask started.")
        while not exit_requested:
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            if not color_frame:
                continue

            frame = np.asanyarray(color_frame.get_data())
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue

            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    except Exception as e:
        print(f"[ERROR] Flask Streaming error: {e}")

    finally:
        if pipeline:
            pipeline.stop()
            print("[INFO] RealSense pipeline for Flask stopped.")


def signal_handler(sig, frame):
    global exit_requested
    print("\nExiting gracefully...")
    exit_requested = True
    time.sleep(1)
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def start_mavproxy():
    def launch_mavproxy():
        cmd = [
            "mavproxy.py",
            f"--master={VEHICLE_PORT}",
            f"--baudrate={BAUDRATE}",
            f"--out=udpout:{GCS_IP}:{GCS_PORT}",
            f"--out=udpout:{LOCAL_IP}:{LOCAL_OUTPUT_PORT}",
            "--load-module=ntrip"
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=sys.stdout, stderr=sys.stderr, text=True)
        time.sleep(2)
        proc.stdin.write(f"ntrip set caster {NTRIP_CASTER}\n")
        proc.stdin.write(f"ntrip set port {NTRIP_PORT}\n")
        proc.stdin.write(f"ntrip set mountpoint {MOUNTPOINT}\n")
        proc.stdin.write("ntrip start\n")
        proc.stdin.write("ntrip status\n")
        proc.stdin.flush()

        print(f"Started MAVProxy with PID: {proc.pid}")
        threading.Thread(target=periodic_ntrip_status, args=(proc,), daemon=True).start()
        return proc

    try:
        process = launch_mavproxy()

        while not exit_requested:
            if process.poll() is not None:
                print("MAVProxy terminated unexpectedly. Restarting...")
                process = launch_mavproxy()
            time.sleep(1)

        # Shutdown process
        if process.poll() is None:
            process.terminate()

    except Exception as e:
        print(f"MAVProxy Error: {e}")
        

def periodic_ntrip_status(proc):
    while not exit_requested:
        try:
            proc.stdin.write("ntrip status\n")
            proc.stdin.flush()
        except Exception as e:
            print(f"Error sending ntrip status: {e}")
        time.sleep (20)


def start_d4xx_script():
    try:
        cmd = f"python3 {D4XX_SCRIPT} --connect udpin:{LOCAL_IP}:{LOCAL_OUTPUT_PORT} --baudrate {BAUDRATE}"
        process = subprocess.Popen(cmd, shell=True)
        print(f"Started RealSense OBSTACLE_DISTANCE script with PID: {process.pid}")
        while not exit_requested:
            if process.poll() is not None:
                print("D4xx script terminated. Restarting...")
                process = subprocess.Popen(cmd, shell=True)
            time.sleep(1)
        if process.poll() is None:
            process.terminate()
    except Exception as e:
        print(f"D4xx Script Error: {e}")

def start_flask_server():
    @flask_app.route('/video_feed')
    def video_feed():
        return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

    @flask_app.route('/')
    def index():
        return '<h1>RealSense Live Stream</h1><img src="/video_feed" width="640" height="480">'
        
    print("Flask Stream Started...")
    flask_app.run(host='0.0.0.0', port=8080, threaded=True)
    
    
def safe_decimal(val):
    return Decimal(str(val)) if val is not None else None

def telemetry_to_dynamodb():
    # Connect to MAVProxy's UDP output instead of direct serial
    connection_str = f"udpin:{LOCAL_IP}:{LOCAL_OUTPUT_PORT}"
    
    while not exit_requested:
        try:
            print(f"Connecting to MAVLink via {connection_str}...")
            master = mavutil.mavlink_connection(connection_str, autoreconnect=True, retries=3)
            master.wait_heartbeat(timeout=5)
            print("✅ Connected to MAVProxy telemetry stream")

            dynamodb = boto3.resource(
                'dynamodb',
                endpoint_url=DYNAMODB_ENDPOINT,
                region_name=DYNAMODB_REGION,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY
            )
            table = dynamodb.Table(DYNAMODB_TABLE)

            while not exit_requested:
                try:
                    msg = master.recv_match(
                        type=['GLOBAL_POSITION_INT', 'SYS_STATUS'],
                        blocking=True,
                        timeout=2
                    )
                    if not msg:
                        continue

                    data = {'timestamp': int(datetime.utcnow().timestamp())}

                    if msg.get_type() == 'GLOBAL_POSITION_INT':
                        data.update({
                            'lat': safe_decimal(msg.lat / 1e7),
                            'lon': safe_decimal(msg.lon / 1e7),
                            'alt': safe_decimal(msg.alt / 1000.0),
                            'relative_alt': safe_decimal(msg.relative_alt / 1000.0),
                            'heading': safe_decimal(msg.hdg / 100.0) if msg.hdg != 65535 else None,
                            'speed': safe_decimal(msg.vx / 100.0)
                        })
                    elif msg.get_type() == 'SYS_STATUS':
                        data.update({
                            'battery_voltage': safe_decimal(msg.voltage_battery / 1000.0),
                            'battery_current': safe_decimal(msg.current_battery / 100.0),
                            'battery_remaining': safe_decimal(msg.battery_remaining)
                        })

                    print("📤 Sending to DynamoDB:", data)
                    table.put_item(Item=data)
                    time.sleep(100)

                except Exception as e:
                    print(f"Telemetry processing error: {e}")
                    time.sleep(1)

        except Exception as conn_error:
            print(f"Connection error: {conn_error} - Retrying in 3 seconds...")
            time.sleep(3)
        finally:
            if 'master' in locals():
                try:
                    master.close()
                except:
                    pass

def main():
    print("Starting all services...")
    
    services = [
        threading.Thread(target=start_mavproxy),
        threading.Thread(target=start_d4xx_script),
        threading.Thread(target=telemetry_to_dynamodb),
        threading.Thread(target=start_flask_server)
    ]

    for service in services:
        service.start()
        time.sleep(2)  # Staggered startup

    try:
        while not exit_requested:
            time.sleep(1)
    finally:
        print("Cleaning up resources...")
        for service in services:
            if service.is_alive():
                service.join(timeout=5)

if __name__ == "__main__":
    main()

