#!/usr/bin/env python3
"""
Team Omega - Obstacle Fusion Engine
Combines LiDAR, camera, and ultrasonic data into MAVLink messages for ArduPilot
"""

import os
import sys
import time
import math
import socket
import threading
import structlog
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json

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


class ObstacleType(Enum):
    """Obstacle type classification"""
    UNKNOWN = "unknown"
    STATIC = "static"
    MOVING = "moving"
    VEGETATION = "vegetation"


@dataclass
class FusedObstacle:
    """Fused obstacle information from multiple sensors"""
    angle_deg: float
    distance_mm: float
    confidence: float
    obstacle_type: ObstacleType
    sensor_sources: List[str]  # Which sensors detected this
    timestamp: float
    velocity_mm_s: Optional[float] = None  # For moving obstacles


class ObstacleFusion:
    """Multi-sensor obstacle fusion engine"""
    
    def __init__(self):
        # Configuration
        self.angle_resolution_deg = 5  # 5° bins for OBSTACLE_DISTANCE
        self.num_bins = 72  # 360° / 5° = 72 bins
        self.max_distance_mm = 8000  # 8m maximum
        self.min_distance_mm = 100   # 10cm minimum
        
        # Sensor data buffers
        self.lidar_obstacles: List[Dict] = []
        self.camera_obstacles: List[Dict] = []
        self.ultrasonic_obstacles: List[Dict] = []
        
        # Fused obstacle map
        self.fused_obstacles: List[FusedObstacle] = []
        self.obstacle_history: List[FusedObstacle] = []
        
        # Performance metrics
        self.fusion_rate_hz = 0.0
        self.last_fusion_time = 0.0
        self.fusion_count = 0
        
        # Temporal filtering
        self.obstacle_tracking: Dict[int, FusedObstacle] = {}  # Track obstacles over time
        self.tracking_timeout = 2.0  # Seconds to track an obstacle
    
    def update_lidar_data(self, obstacles: List[Dict]):
        """Update LiDAR obstacle data"""
        self.lidar_obstacles = obstacles
        logger.debug("Updated LiDAR data", obstacle_count=len(obstacles))
    
    def update_camera_data(self, obstacles: List[Dict]):
        """Update camera obstacle data"""
        self.camera_obstacles = obstacles
        logger.debug("Updated camera data", obstacle_count=len(obstacles))
    
    def update_ultrasonic_data(self, obstacles: List[Dict]):
        """Update ultrasonic obstacle data"""
        self.ultrasonic_obstacles = obstacles
        logger.debug("Updated ultrasonic data", obstacle_count=len(obstacles))
    
    def fuse_sensors(self) -> List[FusedObstacle]:
        """Fuse data from all sensors into unified obstacle map"""
        start_time = time.time()
        
        # Combine all sensor data
        all_obstacles = []
        all_obstacles.extend(self.lidar_obstacles)
        all_obstacles.extend(self.camera_obstacles)
        all_obstacles.extend(self.ultrasonic_obstacles)
        
        if not all_obstacles:
            self.fused_obstacles = []
            return []
        
        # Group obstacles by angle bins
        angle_bins = {}
        for obstacle in all_obstacles:
            angle = obstacle.get('center_angle_deg', 0)
            distance = obstacle.get('center_distance_mm', float('inf'))
            obstacle_type = obstacle.get('obstacle_type', ObstacleType.UNKNOWN)
            confidence = obstacle.get('confidence', 0.0)
            sensor_source = obstacle.get('sensor_source', 'unknown')
            
            # Skip invalid obstacles
            if distance < self.min_distance_mm or distance > self.max_distance_mm:
                continue
            
            # Determine angle bin
            bin_index = int(angle / self.angle_resolution_deg) % self.num_bins
            bin_center_angle = bin_index * self.angle_resolution_deg
            
            if bin_index not in angle_bins:
                angle_bins[bin_index] = []
            
            angle_bins[bin_index].append({
                'angle': angle,
                'distance': distance,
                'type': obstacle_type,
                'confidence': confidence,
                'sensor_source': sensor_source,
                'timestamp': time.time()
            })
        
        # Fuse obstacles in each bin
        fused_obstacles = []
        for bin_index, obstacles_in_bin in angle_bins.items():
            if not obstacles_in_bin:
                continue
            
            # Find the closest obstacle in this bin (highest priority)
            closest_obstacle = min(obstacles_in_bin, key=lambda x: x['distance'])
            
            # Calculate fused confidence based on multiple sensors
            sensor_sources = list(set(obs['sensor_source'] for obs in obstacles_in_bin))
            fused_confidence = min(1.0, sum(obs['confidence'] for obs in obstacles_in_bin) / len(obstacles_in_bin))
            
            # Create fused obstacle
            fused_obstacle = FusedObstacle(
                angle_deg=closest_obstacle['angle'],
                distance_mm=closest_obstacle['distance'],
                confidence=fused_confidence,
                obstacle_type=closest_obstacle['type'],
                sensor_sources=sensor_sources,
                timestamp=time.time()
            )
            
            fused_obstacles.append(fused_obstacle)
        
        # Apply temporal filtering and tracking
        fused_obstacles = self._apply_temporal_filtering(fused_obstacles)
        
        # Update state
        self.fused_obstacles = fused_obstacles
        self.obstacle_history.extend(fused_obstacles)
        
        # Keep only recent history
        current_time = time.time()
        self.obstacle_history = [obs for obs in self.obstacle_history 
                               if current_time - obs.timestamp < 10.0]
        
        # Update metrics
        self.fusion_count += 1
        elapsed = time.time() - start_time
        if elapsed > 0:
            self.fusion_rate_hz = 1.0 / elapsed
        self.last_fusion_time = current_time
        
        logger.debug("Fusion completed", 
                    input_obstacles=len(all_obstacles),
                    fused_obstacles=len(fused_obstacles),
                    fusion_rate_hz=self.fusion_rate_hz)
        
        return fused_obstacles
    
    def _apply_temporal_filtering(self, obstacles: List[FusedObstacle]) -> List[FusedObstacle]:
        """Apply temporal filtering to reduce noise and track moving obstacles"""
        current_time = time.time()
        filtered_obstacles = []
        
        for obstacle in obstacles:
            # Create unique ID for this obstacle based on angle and distance
            obstacle_id = self._create_obstacle_id(obstacle)
            
            if obstacle_id in self.obstacle_tracking:
                # Update existing tracked obstacle
                tracked = self.obstacle_tracking[obstacle_id]
                time_diff = current_time - tracked.timestamp
                
                if time_diff < self.tracking_timeout:
                    # Calculate velocity if we have recent data
                    if tracked.distance_mm != obstacle.distance_mm:
                        velocity = (obstacle.distance_mm - tracked.distance_mm) / time_diff
                        obstacle.velocity_mm_s = velocity
                    
                    # Update tracking
                    self.obstacle_tracking[obstacle_id] = obstacle
                    filtered_obstacles.append(obstacle)
                else:
                    # Obstacle reappeared after timeout, treat as new
                    self.obstacle_tracking[obstacle_id] = obstacle
                    filtered_obstacles.append(obstacle)
            else:
                # New obstacle
                self.obstacle_tracking[obstacle_id] = obstacle
                filtered_obstacles.append(obstacle)
        
        # Clean up old tracked obstacles
        self.obstacle_tracking = {k: v for k, v in self.obstacle_tracking.items()
                                if current_time - v.timestamp < self.tracking_timeout}
        
        return filtered_obstacles
    
    def _create_obstacle_id(self, obstacle: FusedObstacle) -> int:
        """Create unique ID for obstacle tracking"""
        # Round angle to nearest bin and distance to nearest 10cm
        angle_bin = int(obstacle.angle_deg / self.angle_resolution_deg)
        distance_bin = int(obstacle.distance_mm / 100)
        return hash((angle_bin, distance_bin))
    
    def get_obstacle_distances(self) -> List[int]:
        """Get 72-bin obstacle distance array for MAVLink OBSTACLE_DISTANCE"""
        distances = [0] * self.num_bins
        
        for obstacle in self.fused_obstacles:
            bin_index = int(obstacle.angle_deg / self.angle_resolution_deg) % self.num_bins
            distance_cm = int(obstacle.distance_mm / 10)
            distances[bin_index] = distance_cm
        
        return distances
    
    def get_cardinal_distances(self) -> Dict[str, float]:
        """Get obstacle distances in cardinal directions"""
        directions = {
            "front": (315, 45),    # -45° to +45°
            "left": (45, 135),     # +45° to +135°
            "rear": (135, 225),    # +135° to +225°
            "right": (225, 315)    # +225° to +315°
        }
        
        obstacle_distances = {}
        
        for direction, (start_angle, end_angle) in directions.items():
            min_distance = float('inf')
            
            for obstacle in self.fused_obstacles:
                angle = obstacle.angle_deg
                
                # Handle angle wrapping
                if start_angle > end_angle:  # e.g., 315 to 45
                    if start_angle <= angle <= 360 or 0 <= angle <= end_angle:
                        min_distance = min(min_distance, obstacle.distance_mm)
                else:  # Normal range
                    if start_angle <= angle <= end_angle:
                        min_distance = min(min_distance, obstacle.distance_mm)
            
            obstacle_distances[direction] = min_distance if min_distance != float('inf') else float('inf')
        
        return obstacle_distances
    
    def get_fusion_status(self) -> Dict[str, Any]:
        """Get fusion engine status information"""
        return {
            "fusion_rate_hz": self.fusion_rate_hz,
            "fusion_count": self.fusion_count,
            "last_fusion_time": self.last_fusion_time,
            "fused_obstacles_count": len(self.fused_obstacles),
            "tracked_obstacles_count": len(self.obstacle_tracking),
            "history_size": len(self.obstacle_history),
            "sensor_data": {
                "lidar": len(self.lidar_obstacles),
                "camera": len(self.camera_obstacles),
                "ultrasonic": len(self.ultrasonic_obstacles)
            }
        }


class ObstaclePublisher:
    """Publishes fused obstacle data via MAVLink and telemetry"""
    
    def __init__(self):
        # Load configuration from environment
        self.fusion_port = int(os.getenv("MAVPROXY_FUSION_PORT", "14551"))
        self.telemetry_interval = float(os.getenv("TELEMETRY_UPLINK_INTERVAL", "2.0"))
        
        # Fusion engine
        self.fusion_engine = ObstacleFusion()
        
        # Network connections
        self.fusion_socket: Optional[socket.socket] = None
        self.telemetry_socket: Optional[socket.socket] = None
        
        # State tracking
        self.running = False
        self.connected = False
        
        # Telemetry data
        self.rover_telemetry = {
            "position": {"lat": 0.0, "lon": 0.0, "alt": 0.0},
            "speed": 0.0,
            "heading": 0.0,
            "battery": {"voltage": 0.0, "percentage": 0.0},
            "obstacles": {"count": 0, "distances": {}, "cardinal": {}},
            "sensors": {"lidar": "disconnected", "camera": "disconnected", "ultrasonic": "disconnected"},
            "rtk_status": "NO_RTK",
            "timestamp": time.time()
        }
    
    def connect_fusion_port(self) -> bool:
        """Connect to MAVProxy fusion port"""
        try:
            self.fusion_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.fusion_socket.bind(('127.0.0.1', self.fusion_port))
            self.fusion_socket.settimeout(0.1)
            
            logger.info("Connected to fusion port", port=self.fusion_port)
            return True
            
        except Exception as e:
            logger.error("Failed to connect to fusion port", error=str(e))
            return False
    
    def connect_telemetry_port(self) -> bool:
        """Connect to telemetry port for data uplink"""
        try:
            self.telemetry_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.telemetry_socket.bind(('127.0.0.1', 0))  # Bind to any available port
            
            logger.info("Connected to telemetry port")
            return True
            
        except Exception as e:
            logger.error("Failed to connect to telemetry port", error=str(e))
            return False
    
    def update_rover_telemetry(self, telemetry_data: Dict[str, Any]):
        """Update rover telemetry from MAVLink messages"""
        # Update position
        if 'lat' in telemetry_data and 'lon' in telemetry_data:
            self.rover_telemetry["position"]["lat"] = telemetry_data.get('lat', 0.0)
            self.rover_telemetry["position"]["lon"] = telemetry_data.get('lon', 0.0)
            self.rover_telemetry["position"]["alt"] = telemetry_data.get('alt', 0.0)
        
        # Update speed and heading
        if 'speed' in telemetry_data:
            self.rover_telemetry["speed"] = telemetry_data.get('speed', 0.0)
        if 'heading' in telemetry_data:
            self.rover_telemetry["heading"] = telemetry_data.get('heading', 0.0)
        
        # Update battery
        if 'battery_voltage' in telemetry_data:
            self.rover_telemetry["battery"]["voltage"] = telemetry_data.get('battery_voltage', 0.0)
        if 'battery_percentage' in telemetry_data:
            self.rover_telemetry["battery"]["percentage"] = telemetry_data.get('battery_percentage', 0.0)
        
        # Update RTK status
        if 'rtk_status' in telemetry_data:
            self.rover_telemetry["rtk_status"] = telemetry_data.get('rtk_status', 'NO_RTK')
        
        # Update timestamp
        self.rover_telemetry["timestamp"] = time.time()
    
    def update_sensor_status(self, sensor_name: str, status: str, data: Optional[Dict] = None):
        """Update sensor status and data"""
        if sensor_name in self.rover_telemetry["sensors"]:
            self.rover_telemetry["sensors"][sensor_name] = status
        
        # Update obstacle data if available
        if data and sensor_name == "lidar":
            self.fusion_engine.update_lidar_data(data.get('obstacles', []))
        elif data and sensor_name == "camera":
            self.fusion_engine.update_camera_data(data.get('obstacles', []))
        elif data and sensor_name == "ultrasonic":
            self.fusion_engine.update_ultrasonic_data(data.get('obstacles', []))
    
    def publish_obstacles(self):
        """Publish fused obstacle data"""
        # Run fusion
        fused_obstacles = self.fusion_engine.fuse_sensors()
        
        # Update telemetry with obstacle information
        self.rover_telemetry["obstacles"]["count"] = len(fused_obstacles)
        self.rover_telemetry["obstacles"]["distances"] = self.fusion_engine.get_obstacle_distances()
        self.rover_telemetry["obstacles"]["cardinal"] = self.fusion_engine.get_cardinal_distances()
        
        # TODO: Send MAVLink messages to ArduPilot
        # This would require pymavlink integration
        logger.debug("Published obstacles", 
                    count=len(fused_obstacles),
                    cardinal_distances=self.rover_telemetry["obstacles"]["cardinal"])
    
    def send_telemetry_to_ec2(self):
        """Send telemetry data to EC2 dashboard"""
        try:
            # Get fusion status
            fusion_status = self.fusion_engine.get_fusion_status()
            
            # Combine telemetry and fusion data
            full_telemetry = {
                **self.rover_telemetry,
                "fusion_status": fusion_status,
                "device_id": os.getenv("DEVICE_ID", "astra-rover-1")
            }
            
            # Convert to JSON
            telemetry_json = json.dumps(full_telemetry)
            
            # TODO: Send to EC2 via HTTP API or WebSocket
            # For now, log the telemetry
            logger.info("Telemetry ready for EC2", 
                       telemetry_size=len(telemetry_json),
                       obstacle_count=full_telemetry["obstacles"]["count"])
            
        except Exception as e:
            logger.error("Failed to send telemetry to EC2", error=str(e))
    
    def run_fusion_loop(self):
        """Main fusion and publishing loop"""
        logger.info("Starting fusion engine loop")
        
        last_telemetry_time = 0.0
        
        try:
            while self.running:
                start_time = time.time()
                
                # Publish obstacles (10Hz for ArduPilot)
                self.publish_obstacles()
                
                # Send telemetry to EC2 at configured interval
                current_time = time.time()
                if current_time - last_telemetry_time >= self.telemetry_interval:
                    self.send_telemetry_to_ec2()
                    last_telemetry_time = current_time
                
                # Maintain 10Hz loop
                elapsed = time.time() - start_time
                if elapsed < 0.1:  # 10Hz = 100ms
                    time.sleep(0.1 - elapsed)
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error("Error in fusion loop", error=str(e))
        finally:
            self.stop()
    
    def start(self):
        """Start the obstacle publisher"""
        if not self.connect_fusion_port():
            logger.error("Failed to connect to fusion port")
            return False
        
        if not self.connect_telemetry_port():
            logger.error("Failed to connect to telemetry port")
            return False
        
        self.running = True
        self.connected = True
        
        # Start fusion loop in separate thread
        self.fusion_thread = threading.Thread(target=self.run_fusion_loop, daemon=True)
        self.fusion_thread.start()
        
        logger.info("Obstacle publisher started")
        return True
    
    def stop(self):
        """Stop the obstacle publisher"""
        logger.info("Stopping obstacle publisher")
        self.running = False
        self.connected = False
        
        if self.fusion_socket:
            try:
                self.fusion_socket.close()
            except:
                pass
        
        if self.telemetry_socket:
            try:
                self.telemetry_socket.close()
            except:
                pass
        
        logger.info("Obstacle publisher stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get publisher status information"""
        return {
            "running": self.running,
            "connected": self.connected,
            "fusion_status": self.fusion_engine.get_fusion_status(),
            "rover_telemetry": self.rover_telemetry
        }


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Team Omega Obstacle Fusion Engine")
    parser.add_argument("--fusion-port", type=int, help="MAVProxy fusion port")
    parser.add_argument("--telemetry-interval", type=float, help="Telemetry interval (seconds)")
    
    args = parser.parse_args()
    
    # Override environment variables with command line args
    if args.fusion_port:
        os.environ["MAVPROXY_FUSION_PORT"] = str(args.fusion_port)
    if args.telemetry_interval:
        os.environ["TELEMETRY_UPLINK_INTERVAL"] = str(args.telemetry_interval)
    
    publisher = ObstaclePublisher()
    
    try:
        if publisher.start():
            # Keep main thread alive
            while publisher.running:
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        publisher.stop()


if __name__ == "__main__":
    main()
