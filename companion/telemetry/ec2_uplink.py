#!/usr/bin/env python3
"""
Team Omega - Enhanced EC2 Telemetry Uplink
Sends rich rover data (position, speed, LiDAR, battery, etc.) to existing EC2 dashboard
"""

import os
import sys
import time
import json
import requests
import threading
import structlog
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import socket
import ssl

# Setup structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@dataclass
class RoverPosition:
    """Rover position data"""
    latitude: float
    longitude: float
    altitude: float
    accuracy_m: float
    timestamp: float


@dataclass
class RoverMotion:
    """Rover motion data"""
    speed_mps: float
    heading_deg: float
    pitch_deg: float
    roll_deg: float
    acceleration_mps2: float
    timestamp: float


@dataclass
class RoverBattery:
    """Rover battery data"""
    voltage_v: float
    current_a: float
    percentage: float
    temperature_c: float
    health: str  # "good", "warning", "critical"
    timestamp: float


@dataclass
class RoverObstacles:
    """Rover obstacle data"""
    count: int
    closest_distance_m: float
    cardinal_distances: Dict[str, float]  # front, left, rear, right
    obstacle_map: List[int]  # 72-bin distance array
    confidence: float
    timestamp: float


@dataclass
class RoverSensors:
    """Rover sensor status"""
    lidar: str  # "connected", "disconnected", "error"
    camera: str
    ultrasonic: str
    gps: str
    imu: str
    timestamp: float


@dataclass
class RoverSystem:
    """Rover system status"""
    mode: str  # "MANUAL", "AUTO", "RTL", "LOITER"
    armed: bool
    rtk_status: str  # "NO_RTK", "FLOAT", "FIXED"
    cpu_usage: float
    memory_usage: float
    temperature_c: float
    uptime_seconds: float
    timestamp: float


class EnhancedTelemetryUplink:
    """Enhanced telemetry uplink to EC2 dashboard"""
    
    def __init__(self):
        # Load configuration from environment
        self.ec2_api_url = os.getenv("EC2_API_URL", "http://localhost:5000")
        self.device_id = os.getenv("DEVICE_ID", "astra-rover-1")
        self.uplink_interval = float(os.getenv("TELEMETRY_UPLINK_INTERVAL", "2.0"))
        self.retry_attempts = int(os.getenv("TELEMETRY_RETRY_ATTEMPTS", "3"))
        self.retry_delay = float(os.getenv("TELEMETRY_RETRY_DELAY", "1.0"))
        
        # AWS credentials (if using AWS services directly)
        self.aws_region = os.getenv("AWS_REGION", "us-west-2")
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        
        # Telemetry data structures
        self.position = RoverPosition(0.0, 0.0, 0.0, 0.0, time.time())
        self.motion = RoverMotion(0.0, 0.0, 0.0, 0.0, 0.0, time.time())
        self.battery = RoverBattery(0.0, 0.0, 0.0, 0.0, "unknown", time.time())
        self.obstacles = RoverObstacles(0, float('inf'), {}, [], 0.0, time.time())
        self.sensors = RoverSensors("disconnected", "disconnected", "disconnected", 
                                  "disconnected", "disconnected", time.time())
        self.system = RoverSystem("MANUAL", False, "NO_RTK", 0.0, 0.0, 0.0, 0.0, time.time())
        
        # State tracking
        self.running = False
        self.connected = False
        self.last_uplink_time = 0.0
        self.uplink_count = 0
        self.error_count = 0
        
        # Performance metrics
        self.avg_uplink_time_ms = 0.0
        self.success_rate = 100.0
        
        # HTTP session for persistent connections
        self.session = requests.Session()
        self.session.timeout = 10.0
        
        # Health check endpoint
        self.health_endpoint = f"{self.ec2_api_url}/health"
        
        logger.info("Enhanced telemetry uplink initialized", 
                   ec2_url=self.ec2_api_url,
                   device_id=self.device_id,
                   uplink_interval=self.uplink_interval)
    
    def update_position(self, lat: float, lon: float, alt: float, accuracy: float = 0.0):
        """Update rover position data"""
        self.position = RoverPosition(lat, lon, alt, accuracy, time.time())
        logger.debug("Updated position", lat=lat, lon=lon, alt=alt, accuracy=accuracy)
    
    def update_motion(self, speed: float, heading: float, pitch: float = 0.0, 
                     roll: float = 0.0, acceleration: float = 0.0):
        """Update rover motion data"""
        self.motion = RoverMotion(speed, heading, pitch, roll, acceleration, time.time())
        logger.debug("Updated motion", speed=speed, heading=heading)
    
    def update_battery(self, voltage: float, current: float = 0.0, percentage: float = 0.0,
                      temperature: float = 0.0):
        """Update rover battery data"""
        # Determine battery health
        if percentage > 20 and voltage > 10.0:
            health = "good"
        elif percentage > 10 and voltage > 9.0:
            health = "warning"
        else:
            health = "critical"
        
        self.battery = RoverBattery(voltage, current, percentage, temperature, health, time.time())
        logger.debug("Updated battery", voltage=voltage, percentage=percentage, health=health)
    
    def update_obstacles(self, count: int, closest_distance: float, 
                        cardinal_distances: Dict[str, float], obstacle_map: List[int],
                        confidence: float = 1.0):
        """Update rover obstacle data"""
        self.obstacles = RoverObstacles(
            count, closest_distance, cardinal_distances, obstacle_map, confidence, time.time()
        )
        logger.debug("Updated obstacles", count=count, closest_distance=closest_distance)
    
    def update_sensors(self, lidar_status: str = None, camera_status: str = None,
                      ultrasonic_status: str = None, gps_status: str = None, imu_status: str = None):
        """Update rover sensor status"""
        if lidar_status:
            self.sensors.lidar = lidar_status
        if camera_status:
            self.sensors.camera = camera_status
        if ultrasonic_status:
            self.sensors.ultrasonic = ultrasonic_status
        if gps_status:
            self.sensors.gps = gps_status
        if imu_status:
            self.sensors.imu = imu_status
        
        self.sensors.timestamp = time.time()
        logger.debug("Updated sensors", 
                    lidar=self.sensors.lidar,
                    camera=self.sensors.camera,
                    ultrasonic=self.sensors.ultrasonic)
    
    def update_system(self, mode: str = None, armed: bool = None, rtk_status: str = None,
                     cpu_usage: float = None, memory_usage: float = None,
                     temperature: float = None):
        """Update rover system status"""
        if mode:
            self.system.mode = mode
        if armed is not None:
            self.system.armed = armed
        if rtk_status:
            self.system.rtk_status = rtk_status
        if cpu_usage is not None:
            self.system.cpu_usage = cpu_usage
        if memory_usage is not None:
            self.system.memory_usage = memory_usage
        if temperature is not None:
            self.system.temperature = temperature
        
        self.system.timestamp = time.time()
        logger.debug("Updated system", mode=self.system.mode, armed=self.system.armed)
    
    def _check_ec2_health(self) -> bool:
        """Check if EC2 dashboard is healthy and accessible"""
        try:
            response = self.session.get(self.health_endpoint, timeout=5.0)
            if response.status_code == 200:
                health_data = response.json()
                logger.debug("EC2 health check passed", status=health_data.get('status'))
                return True
            else:
                logger.warning("EC2 health check failed", status_code=response.status_code)
                return False
        except Exception as e:
            logger.error("EC2 health check error", error=str(e))
            return False
    
    def _prepare_telemetry_payload(self) -> Dict[str, Any]:
        """Prepare the complete telemetry payload for EC2"""
        current_time = time.time()
        
        # Calculate uptime
        uptime = current_time - self.system.timestamp + self.system.uptime_seconds
        
        # Prepare enhanced telemetry payload
        payload = {
            "device_id": self.device_id,
            "timestamp": current_time,
            "timestamp_iso": datetime.fromtimestamp(current_time, tz=timezone.utc).isoformat(),
            
            # Position data
            "position": {
                "latitude": self.position.latitude,
                "longitude": self.position.longitude,
                "altitude": self.position.altitude,
                "accuracy_m": self.position.accuracy_m,
                "timestamp": self.position.timestamp
            },
            
            # Motion data
            "motion": {
                "speed_mps": self.motion.speed_mps,
                "speed_kmh": self.motion.speed_mps * 3.6,  # Convert to km/h
                "heading_deg": self.motion.heading_deg,
                "pitch_deg": self.motion.pitch_deg,
                "roll_deg": self.motion.roll_deg,
                "acceleration_mps2": self.motion.acceleration_mps2,
                "timestamp": self.motion.timestamp
            },
            
            # Battery data
            "battery": {
                "voltage_v": self.battery.voltage_v,
                "current_a": self.battery.current_a,
                "percentage": self.battery.percentage,
                "temperature_c": self.battery.temperature_c,
                "health": self.battery.health,
                "timestamp": self.battery.timestamp
            },
            
            # Obstacle data
            "obstacles": {
                "count": self.obstacles.count,
                "closest_distance_m": self.obstacles.closest_distance_m,
                "cardinal_distances": self.obstacles.cardinal_distances,
                "obstacle_map": self.obstacles.obstacle_map,
                "confidence": self.obstacles.confidence,
                "timestamp": self.obstacles.timestamp
            },
            
            # Sensor status
            "sensors": {
                "lidar": self.sensors.lidar,
                "camera": self.sensors.camera,
                "ultrasonic": self.sensors.ultrasonic,
                "gps": self.sensors.gps,
                "imu": self.sensors.imu,
                "timestamp": self.sensors.timestamp
            },
            
            # System status
            "system": {
                "mode": self.system.mode,
                "armed": self.system.armed,
                "rtk_status": self.system.rtk_status,
                "cpu_usage": self.system.cpu_usage,
                "memory_usage": self.system.memory_usage,
                "temperature_c": self.system.temperature_c,
                "uptime_seconds": uptime,
                "timestamp": self.system.timestamp
            },
            
            # Performance metrics
            "performance": {
                "uplink_count": self.uplink_count,
                "error_count": self.error_count,
                "success_rate": self.success_rate,
                "avg_uplink_time_ms": self.avg_uplink_time_ms,
                "last_uplink_time": self.last_uplink_time
            }
        }
        
        return payload
    
    def _send_to_ec2_api(self, payload: Dict[str, Any]) -> bool:
        """Send telemetry data to EC2 API endpoints"""
        try:
            # Send to main telemetry endpoint
            telemetry_url = f"{self.ec2_api_url}/api/telemetry"
            response = self.session.post(
                telemetry_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.debug("Telemetry sent successfully", status_code=response.status_code)
                return True
            else:
                logger.warning("Telemetry send failed", 
                             status_code=response.status_code,
                             response_text=response.text[:200])
                return False
                
        except Exception as e:
            logger.error("Failed to send telemetry to EC2", error=str(e))
            return False
    
    def _send_to_dynamodb(self, payload: Dict[str, Any]) -> bool:
        """Send telemetry data directly to DynamoDB (if AWS credentials available)"""
        if not (self.aws_access_key and self.aws_secret_key):
            logger.debug("AWS credentials not available, skipping DynamoDB upload")
            return False
        
        try:
            # TODO: Implement direct DynamoDB upload using boto3
            # This would be useful for high-frequency data that needs to bypass the API
            logger.debug("DynamoDB upload not yet implemented")
            return False
            
        except Exception as e:
            logger.error("Failed to send to DynamoDB", error=str(e))
            return False
    
    def _send_telemetry(self) -> bool:
        """Send telemetry data to EC2 with retry logic"""
        start_time = time.time()
        payload = self._prepare_telemetry_payload()
        
        # Try to send to EC2 API
        success = False
        for attempt in range(self.retry_attempts):
            try:
                if self._send_to_ec2_api(payload):
                    success = True
                    break
                elif attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
                    logger.debug(f"Retrying telemetry send, attempt {attempt + 2}")
            except Exception as e:
                logger.error(f"Telemetry send attempt {attempt + 1} failed", error=str(e))
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
        
        # Update metrics
        elapsed_ms = (time.time() - start_time) * 1000
        self.avg_uplink_time_ms = (
            (self.avg_uplink_time_ms * (self.uplink_count - 1) + elapsed_ms) / self.uplink_count
            if self.uplink_count > 0 else elapsed_ms
        )
        
        if success:
            self.uplink_count += 1
            self.last_uplink_time = time.time()
            self.success_rate = ((self.uplink_count - self.error_count) / self.uplink_count) * 100
            logger.info("Telemetry uplink successful", 
                       attempt=attempt + 1,
                       elapsed_ms=elapsed_ms,
                       payload_size=len(json.dumps(payload)))
        else:
            self.error_count += 1
            self.success_rate = ((self.uplink_count - self.error_count) / self.uplink_count) * 100
            logger.error("Telemetry uplink failed after all retries", 
                        attempts=self.retry_attempts,
                        elapsed_ms=elapsed_ms)
        
        return success
    
    def run_uplink_loop(self):
        """Main telemetry uplink loop"""
        logger.info("Starting telemetry uplink loop")
        
        try:
            while self.running:
                start_time = time.time()
                
                # Check EC2 health periodically
                if not self._check_ec2_health():
                    logger.warning("EC2 dashboard not healthy, skipping telemetry")
                    time.sleep(self.uplink_interval)
                    continue
                
                # Send telemetry
                self._send_telemetry()
                
                # Wait for next interval
                elapsed = time.time() - start_time
                if elapsed < self.uplink_interval:
                    time.sleep(self.uplink_interval - elapsed)
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error("Error in uplink loop", error=str(e))
        finally:
            self.stop()
    
    def start(self):
        """Start the telemetry uplink"""
        if self.running:
            logger.warning("Telemetry uplink already running")
            return False
        
        # Check initial EC2 connectivity
        if not self._check_ec2_health():
            logger.error("Cannot connect to EC2 dashboard, cannot start uplink")
            return False
        
        self.running = True
        self.connected = True
        
        # Start uplink loop in separate thread
        self.uplink_thread = threading.Thread(target=self.run_uplink_loop, daemon=True)
        self.uplink_thread.start()
        
        logger.info("Enhanced telemetry uplink started")
        return True
    
    def stop(self):
        """Stop the telemetry uplink"""
        logger.info("Stopping telemetry uplink")
        self.running = False
        self.connected = False
        
        # Close HTTP session
        try:
            self.session.close()
        except:
            pass
        
        logger.info("Telemetry uplink stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get uplink status information"""
        return {
            "running": self.running,
            "connected": self.connected,
            "ec2_api_url": self.ec2_api_url,
            "device_id": self.device_id,
            "uplink_interval": self.uplink_interval,
            "last_uplink_time": self.last_uplink_time,
            "uplink_count": self.uplink_count,
            "error_count": self.error_count,
            "success_rate": self.success_rate,
            "avg_uplink_time_ms": self.avg_uplink_time_ms,
            "current_telemetry": {
                "position": asdict(self.position),
                "motion": asdict(self.motion),
                "battery": asdict(self.battery),
                "obstacles": asdict(self.obstacles),
                "sensors": asdict(self.sensors),
                "system": asdict(self.system)
            }
        }


def main():
    """Main entry point for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Team Omega Enhanced EC2 Telemetry Uplink")
    parser.add_argument("--ec2-url", help="EC2 API URL")
    parser.add_argument("--device-id", help="Device ID")
    parser.add_argument("--interval", type=float, help="Uplink interval (seconds)")
    parser.add_argument("--test", action="store_true", help="Run in test mode with simulated data")
    
    args = parser.parse_args()
    
    # Override environment variables with command line args
    if args.ec2_url:
        os.environ["EC2_API_URL"] = args.ec2_url
    if args.device_id:
        os.environ["DEVICE_ID"] = args.device_id
    if args.interval:
        os.environ["TELEMETRY_UPLINK_INTERVAL"] = str(args.interval)
    
    uplink = EnhancedTelemetryUplink()
    
    if args.test:
        # Test mode: simulate some data updates
        logger.info("Running in test mode")
        uplink.update_position(37.7749, -122.4194, 100.0, 0.5)
        uplink.update_motion(2.5, 45.0)
        uplink.update_battery(12.6, 2.1, 85.0)
        uplink.update_sensors("connected", "connected", "connected", "connected", "connected")
        uplink.update_system("AUTO", True, "FIXED", 15.2, 45.8, 35.0)
        
        # Simulate obstacle data
        cardinal_distances = {"front": 2.5, "left": 1.8, "rear": 3.2, "right": 2.1}
        obstacle_map = [0] * 72
        obstacle_map[0] = 250  # 2.5m at 0°
        obstacle_map[18] = 180  # 1.8m at 90°
        obstacle_map[36] = 320  # 3.2m at 180°
        obstacle_map[54] = 210  # 2.1m at 270°
        
        uplink.update_obstacles(4, 1.8, cardinal_distances, obstacle_map, 0.95)
    
    try:
        if uplink.start():
            # Keep main thread alive
            while uplink.running:
                time.sleep(1)
                
                # Print status every 10 seconds
                if int(time.time()) % 10 == 0:
                    status = uplink.get_status()
                    logger.info("Uplink status", 
                               success_rate=status["success_rate"],
                               uplink_count=status["uplink_count"])
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        uplink.stop()


if __name__ == "__main__":
    main()
