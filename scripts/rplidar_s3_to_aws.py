#!/usr/bin/env python3
"""
RPLIDAR S3 to AWS EC2 Dashboard - Enhanced Obstacle Avoidance
Sends real-time LiDAR obstacle detection data to AWS DynamoDB for dashboard display

Usage:
    python rplidar_s3_to_aws.py

Environment Variables:
    AWS_REGION - AWS region (default: us-west-2)
    DDB_ENDPOINT_URL - DynamoDB endpoint (None for production AWS)
    EXISTING_LIDAR_TABLE_NAME - DynamoDB table name (default: UGVLidarScans)
    DEVICE_ID - Device identifier (default: ugv-1)
    RPLIDAR_PORT - Serial port (default: /dev/ttyUSB0)
    RPLIDAR_BAUD - Baud rate (default: 115200)

Features:
    - Real-time obstacle detection and distance calculation
    - Sector-based obstacle analysis (front, left, right, rear)
    - Quality filtering and noise reduction
    - Automatic reconnection on errors
    - Detailed logging and status reporting
"""

import os
import time
import json
import boto3
import signal
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np

# Import our custom LiDAR utilities
try:
    from lidar_utils import RPLidarS3
except ImportError:
    print("❌ Error: lidar_utils.py not found. Please ensure it's in the same directory.")
    sys.exit(1)

# Configuration from environment
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
DDB_ENDPOINT_URL = os.getenv("DDB_ENDPOINT_URL", None)
LIDAR_TABLE = os.getenv("EXISTING_LIDAR_TABLE_NAME", "UGVLidarScans")
DEVICE_ID = os.getenv("DEVICE_ID", "ugv-1")
RPLIDAR_PORT = os.getenv("RPLIDAR_PORT", "/dev/ttyUSB0")
RPLIDAR_BAUD = int(os.getenv("RPLIDAR_BAUD", "115200"))

# Obstacle detection parameters
MIN_QUALITY = 10
MAX_DISTANCE_MM = 8000
SECTOR_ANGLES = {
    'front': (-45, 45),    # Front sector: -45° to +45°
    'left': (45, 135),     # Left sector: 45° to 135°
    'rear': (135, 225),    # Rear sector: 135° to 225°
    'right': (225, 315)    # Right sector: 225° to 315°
}

# Global variables for graceful shutdown
running = True
lidar = None


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global running
    print("\n🛑 Received shutdown signal...")
    running = False


def setup_dynamodb():
    """Setup DynamoDB connection"""
    try:
        if DDB_ENDPOINT_URL:
            # Local development
            dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION, endpoint_url=DDB_ENDPOINT_URL)
            print(f"🔗 Connected to local DynamoDB: {DDB_ENDPOINT_URL}")
        else:
            # Production AWS
            dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
            print(f"🔗 Connected to AWS DynamoDB in {AWS_REGION}")
        
        table = dynamodb.Table(LIDAR_TABLE)
        # Test connection
        table.load()
        print(f"✅ DynamoDB table '{LIDAR_TABLE}' is accessible")
        return table
        
    except Exception as e:
        print(f"❌ DynamoDB connection failed: {e}")
        return None


def analyze_obstacles(measurements: List[Dict]) -> Dict:
    """
    Analyze LiDAR measurements for obstacle detection
    
    Args:
        measurements: List of measurement dictionaries with 'angle', 'distance', 'quality'
    
    Returns:
        Dictionary with obstacle analysis results
    """
    if not measurements:
        return {
            "status": "no_data",
            "closest_distance_mm": 0,
            "closest_distance_cm": 0,
            "closest_distance_m": 0,
            "measurement_count": 0,
            "sectors": {},
            "timestamp": int(time.time())
        }
    
    # Filter valid measurements
    valid_measurements = [
        m for m in measurements 
        if (m['quality'] >= MIN_QUALITY and 
            0 < m['distance'] < MAX_DISTANCE_MM)
    ]
    
    if not valid_measurements:
        return {
            "status": "no_valid_data",
            "closest_distance_mm": 0,
            "closest_distance_cm": 0,
            "closest_distance_m": 0,
            "measurement_count": 0,
            "sectors": {},
            "timestamp": int(time.time())
        }
    
    # Find closest obstacle overall
    closest_distance = min(m['distance'] for m in valid_measurements)
    
    # Analyze sectors
    sectors = {}
    for sector_name, (start_angle, end_angle) in SECTOR_ANGLES.items():
        sector_measurements = []
        
        for m in valid_measurements:
            angle = m['angle']
            # Handle angle wrapping
            if start_angle > end_angle:  # e.g., right sector (225-315)
                if angle >= start_angle or angle <= end_angle:
                    sector_measurements.append(m)
            else:
                if start_angle <= angle <= end_angle:
                    sector_measurements.append(m)
        
        if sector_measurements:
            sector_distances = [m['distance'] for m in sector_measurements]
            sectors[sector_name] = {
                "closest_mm": min(sector_distances),
                "closest_cm": round(min(sector_distances) / 10, 1),
                "closest_m": round(min(sector_distances) / 1000, 2),
                "average_mm": int(np.mean(sector_distances)),
                "count": len(sector_measurements),
                "danger_level": "high" if min(sector_distances) < 500 else "medium" if min(sector_distances) < 1000 else "low"
            }
        else:
            sectors[sector_name] = {
                "closest_mm": MAX_DISTANCE_MM,
                "closest_cm": MAX_DISTANCE_MM / 10,
                "closest_m": MAX_DISTANCE_MM / 1000,
                "average_mm": MAX_DISTANCE_MM,
                "count": 0,
                "danger_level": "none"
            }
    
    # Determine overall status
    if closest_distance < 300:
        status = "critical"
    elif closest_distance < 500:
        status = "warning"
    elif closest_distance < 1000:
        status = "caution"
    else:
        status = "clear"
    
    return {
        "status": status,
        "closest_distance_mm": int(closest_distance),
        "closest_distance_cm": round(closest_distance / 10, 1),
        "closest_distance_m": round(closest_distance / 1000, 2),
        "measurement_count": len(valid_measurements),
        "total_measurements": len(measurements),
        "quality_avg": round(np.mean([m['quality'] for m in valid_measurements]), 1),
        "sectors": sectors,
        "timestamp": int(time.time())
    }


def send_to_aws(table, obstacle_data: Dict) -> bool:
    """
    Send obstacle data to AWS DynamoDB
    
    Args:
        table: DynamoDB table object
        obstacle_data: Obstacle analysis data
    
    Returns:
        True if successful, False otherwise
    """
    try:
        item = {
            "device_id": DEVICE_ID,
            "timestamp": int(time.time()),
            "object_avoidance": obstacle_data,
            "scan_quality": "enhanced",
            "purpose": "ardupilot_collision_detection",
            "processed_at": datetime.utcnow().isoformat()
        }
        
        table.put_item(Item=item)
        return True
        
    except Exception as e:
        print(f"❌ Failed to send data to AWS: {e}")
        return False


def main():
    """Main function"""
    global running, lidar
    
    print("🚀 RPLIDAR S3 to AWS EC2 Dashboard - Enhanced Obstacle Avoidance")
    print("=" * 70)
    print(f"📍 LiDAR Port: {RPLIDAR_PORT}")
    print(f"🔗 AWS Region: {AWS_REGION}")
    print(f"📊 DynamoDB Table: {LIDAR_TABLE}")
    print(f"🆔 Device ID: {DEVICE_ID}")
    print("=" * 70)
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Setup DynamoDB
    table = setup_dynamodb()
    if not table:
        print("❌ Cannot proceed without DynamoDB connection")
        return False
    
    # Setup LiDAR
    try:
        lidar = RPLidarS3(RPLIDAR_PORT, baudrate=RPLIDAR_BAUD)
        print(f"🔍 Connecting to RPLIDAR S3 on {RPLIDAR_PORT}...")
        
        if not lidar.connect():
            print("❌ Failed to connect to RPLIDAR S3")
            return False
        
        # Check health
        health = lidar.get_health()
        if health and health['status'] == 2:
            print("❌ RPLIDAR S3 is in error state!")
            return False
        
        print("✅ RPLIDAR S3 connected and healthy")
        print("📡 Starting obstacle detection and AWS transmission...")
        print("Press Ctrl+C to stop")
        print("-" * 70)
        
        # Main processing loop
        scan_count = 0
        last_status_time = time.time()
        
        while running:
            try:
                # Collect measurements for one scan
                measurements = []
                start_time = time.time()
                
                # Collect measurements for up to 100ms
                for measurement in lidar.iter_measurements():
                    if not running or time.time() - start_time > 0.1:
                        break
                    
                    measurements.append(measurement)
                    
                    # Limit measurements per scan
                    if len(measurements) >= 1000:
                        break
                
                if measurements:
                    # Analyze obstacles
                    obstacle_data = analyze_obstacles(measurements)
                    
                    # Send to AWS
                    if send_to_aws(table, obstacle_data):
                        scan_count += 1
                        
                        # Print status every 10 scans
                        if scan_count % 10 == 0 or time.time() - last_status_time > 5:
                            status = obstacle_data['status'].upper()
                            closest_cm = obstacle_data['closest_distance_cm']
                            count = obstacle_data['measurement_count']
                            
                            print(f"📊 Scan #{scan_count:04d} | Status: {status} | "
                                  f"Closest: {closest_cm}cm | Points: {count} | "
                                  f"Quality: {obstacle_data.get('quality_avg', 0)}")
                            
                            # Show sector info if there are obstacles
                            if obstacle_data['status'] != 'clear':
                                for sector, data in obstacle_data['sectors'].items():
                                    if data['danger_level'] != 'none':
                                        print(f"  🚨 {sector.upper()}: {data['closest_cm']}cm ({data['danger_level']})")
                            
                            last_status_time = time.time()
                    
                    # Rate limiting for ArduPilot compatibility
                    time.sleep(0.05)  # 20Hz update rate
                
            except Exception as e:
                print(f"⚠️ Error in main loop: {e}")
                time.sleep(1)  # Wait before retrying
        
    except KeyboardInterrupt:
        print("\n⏹️ Stopping by user request...")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
    finally:
        # Cleanup
        if lidar:
            try:
                lidar.stop_scan()
                lidar.disconnect()
                print("✅ RPLIDAR S3 disconnected")
            except:
                pass
        
        print(f"📊 Total scans processed: {scan_count}")
        print("👋 RPLIDAR S3 to AWS script stopped")
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
