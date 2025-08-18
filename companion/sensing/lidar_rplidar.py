#!/usr/bin/env python3
"""
Team Omega - RPLIDAR Driver for Obstacle Detection
Enhanced LiDAR processing with clustering for orchard navigation
"""

import os
import sys
import time
import math
import structlog
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np

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
class ObstaclePoint:
    """Individual obstacle point"""
    angle_deg: float
    distance_mm: float
    quality: int
    timestamp: float


@dataclass
class ObstacleCluster:
    """Clustered obstacle group"""
    center_angle_deg: float
    center_distance_mm: float
    min_distance_mm: float
    max_distance_mm: float
    point_count: int
    obstacle_type: ObstacleType
    confidence: float
    timestamp: float


class RPLIDARDriver:
    """Enhanced RPLIDAR driver with obstacle clustering"""
    
    def __init__(self):
        # Load configuration from environment
        self.port = os.getenv("RPLIDAR_PORT", "/dev/ttyUSB0")
        self.baud = int(os.getenv("RPLIDAR_BAUD", "256000"))
        self.scan_frequency = int(os.getenv("LIDAR_SCAN_FREQUENCY", "10"))
        self.angle_resolution = int(os.getenv("LIDAR_ANGLE_RESOLUTION", "5"))
        
        # Obstacle detection parameters
        self.cluster_radius_mm = 500  # 50cm cluster radius
        self.min_cluster_points = 3   # Minimum points to form cluster
        self.max_detection_range_mm = 8000  # 8m max range
        self.min_detection_range_mm = 100   # 10cm min range
        
        # State tracking
        self.connected = False
        self.lidar = None
        self.last_scan_time = 0.0
        self.scan_count = 0
        
        # Obstacle tracking
        self.obstacles: List[ObstacleCluster] = []
        self.last_obstacle_update = 0.0
        
        # Performance metrics
        self.scans_per_second = 0.0
        self.points_per_scan = 0
        self.clusters_per_scan = 0
        
        # Import RPLIDAR SDK
        try:
            from rplidar import RPLidar
            self.RPLidar = RPLidar
        except ImportError:
            logger.error("RPLIDAR SDK not available. Install with: pip install rplidar-roboticia")
            self.RPLidar = None
    
    def connect(self) -> bool:
        """Connect to RPLIDAR sensor"""
        if not self.RPLidar:
            return False
        
        try:
            logger.info("Connecting to RPLIDAR", port=self.port, baud=self.baud)
            
            self.lidar = self.RPLidar(self.port, baudrate=self.baud, timeout=1)
            
            # Get device info
            info = self.lidar.get_info()
            logger.info("RPLIDAR connected", 
                       model=info.model,
                       firmware_version=info.firmware,
                       hardware_version=info.hardware,
                       serial_number=info.serial)
            
            # Get device health
            health = self.lidar.get_health()
            if health.status == 0:
                logger.info("RPLIDAR health OK")
            else:
                logger.warning("RPLIDAR health issue", status=health.status, error_code=health.error_code)
            
            # Start motor
            self.lidar.start_motor()
            time.sleep(1)
            
            self.connected = True
            logger.info("RPLIDAR connection successful")
            return True
            
        except Exception as e:
            logger.error("Failed to connect to RPLIDAR", error=str(e))
            return False
    
    def disconnect(self):
        """Disconnect from RPLIDAR sensor"""
        if self.lidar and self.connected:
            try:
                self.lidar.stop_motor()
                self.lidar.disconnect()
                logger.info("RPLIDAR disconnected")
            except Exception as e:
                logger.error("Error disconnecting RPLIDAR", error=str(e))
            finally:
                self.connected = False
                self.lidar = None
    
    def _filter_scan_points(self, scan: List[Tuple[int, float, float]]) -> List[ObstaclePoint]:
        """Filter and validate scan points"""
        filtered_points = []
        
        for quality, angle_deg, distance_mm in scan:
            # Filter by quality and range
            if (quality > 0 and 
                self.min_detection_range_mm <= distance_mm <= self.max_detection_range_mm):
                
                point = ObstaclePoint(
                    angle_deg=angle_deg,
                    distance_mm=distance_mm,
                    quality=quality,
                    timestamp=time.time()
                )
                filtered_points.append(point)
        
        return filtered_points
    
    def _cluster_points(self, points: List[ObstaclePoint]) -> List[ObstacleCluster]:
        """Cluster points into obstacle groups using DBSCAN-like algorithm"""
        if len(points) < self.min_cluster_points:
            return []
        
        clusters = []
        processed = set()
        
        for i, point in enumerate(points):
            if i in processed:
                continue
            
            # Start new cluster
            cluster_points = [point]
            processed.add(i)
            
            # Find nearby points
            for j, other_point in enumerate(points):
                if j in processed:
                    continue
                
                # Calculate angular and distance similarity
                angle_diff = abs(point.angle_deg - other_point.angle_deg)
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff
                
                distance_diff = abs(point.distance_mm - other_point.distance_mm)
                
                # Check if points are close enough to cluster
                if (angle_diff <= self.angle_resolution * 2 and 
                    distance_diff <= self.cluster_radius_mm):
                    cluster_points.append(other_point)
                    processed.add(j)
            
            # Create cluster if enough points
            if len(cluster_points) >= self.min_cluster_points:
                cluster = self._create_cluster(cluster_points)
                clusters.append(cluster)
        
        return clusters
    
    def _create_cluster(self, points: List[ObstaclePoint]) -> ObstacleCluster:
        """Create obstacle cluster from points"""
        # Calculate cluster center
        angles_rad = [math.radians(p.angle_deg) for p in points]
        distances = [p.distance_mm for p in points]
        
        # Weighted center by distance (closer points have more weight)
        weights = [1.0 / (d + 1) for d in distances]  # Avoid division by zero
        
        # Calculate weighted average angle
        weighted_sin = sum(w * math.sin(a) for w, a in zip(weights, angles_rad))
        weighted_cos = sum(w * math.cos(a) for w, a in zip(weights, angles_rad))
        center_angle_rad = math.atan2(weighted_sin, weighted_cos)
        center_angle_deg = math.degrees(center_angle_rad)
        if center_angle_deg < 0:
            center_angle_deg += 360
        
        # Calculate weighted average distance
        center_distance_mm = sum(w * d for w, d in zip(weights, distances)) / sum(weights)
        
        # Calculate cluster bounds
        min_distance = min(distances)
        max_distance = max(distances)
        
        # Classify obstacle type based on characteristics
        obstacle_type = self._classify_obstacle(points, center_distance_mm)
        
        # Calculate confidence based on point count and quality
        avg_quality = sum(p.quality for p in points) / len(points)
        confidence = min(1.0, (len(points) / 10.0) * (avg_quality / 255.0))
        
        return ObstacleCluster(
            center_angle_deg=center_angle_deg,
            center_distance_mm=center_distance_mm,
            min_distance_mm=min_distance,
            max_distance_mm=max_distance,
            point_count=len(points),
            obstacle_type=obstacle_type,
            confidence=confidence,
            timestamp=time.time()
        )
    
    def _classify_obstacle(self, points: List[ObstaclePoint], center_distance: float) -> ObstacleType:
        """Classify obstacle type based on point characteristics"""
        if len(points) < 3:
            return ObstacleType.UNKNOWN
        
        # Calculate point spread
        distances = [p.distance_mm for p in points]
        distance_variance = np.var(distances) if len(distances) > 1 else 0
        
        # Calculate angular spread
        angles = [p.angle_deg for p in points]
        angle_variance = np.var(angles) if len(angles) > 1 else 0
        
        # Classification logic
        if distance_variance < 100 and angle_variance < 5:  # Tight cluster
            if center_distance < 2000:  # Close and tight = likely static
                return ObstacleType.STATIC
            else:  # Far and tight = likely vegetation
                return ObstacleType.VEGETATION
        elif distance_variance > 500:  # Spread out = likely moving
            return ObstacleType.MOVING
        else:
            return ObstacleType.UNKNOWN
    
    def get_obstacles(self) -> List[ObstacleCluster]:
        """Get current obstacle list"""
        return self.obstacles.copy()
    
    def get_obstacle_distances(self) -> Dict[str, float]:
        """Get obstacle distances in cardinal directions"""
        if not self.obstacles:
            return {
                "front": float('inf'),
                "left": float('inf'),
                "right": float('inf'),
                "rear": float('inf')
            }
        
        directions = {
            "front": (315, 45),    # -45° to +45°
            "left": (45, 135),     # +45° to +135°
            "rear": (135, 225),    # +135° to +225°
            "right": (225, 315)    # +225° to +315°
        }
        
        obstacle_distances = {}
        
        for direction, (start_angle, end_angle) in directions.items():
            min_distance = float('inf')
            
            for obstacle in self.obstacles:
                angle = obstacle.center_angle_deg
                
                # Handle angle wrapping
                if start_angle > end_angle:  # e.g., 315 to 45
                    if start_angle <= angle <= 360 or 0 <= angle <= end_angle:
                        min_distance = min(min_distance, obstacle.center_distance_mm)
                else:  # Normal range
                    if start_angle <= angle <= end_angle:
                        min_distance = min(min_distance, obstacle.center_distance_mm)
            
            obstacle_distances[direction] = min_distance if min_distance != float('inf') else float('inf')
        
        return obstacle_distances
    
    def scan_once(self) -> bool:
        """Perform single scan and process obstacles"""
        if not self.connected or not self.lidar:
            return False
        
        try:
            # Get single scan
            scan = next(self.lidar.iter_scans(max_buf_meas=5000))
            
            # Filter and cluster points
            filtered_points = self._filter_scan_points(scan)
            clusters = self._cluster_points(filtered_points)
            
            # Update state
            self.obstacles = clusters
            self.last_obstacle_update = time.time()
            self.scan_count += 1
            
            # Update metrics
            current_time = time.time()
            if current_time - self.last_scan_time > 0:
                self.scans_per_second = 1.0 / (current_time - self.last_scan_time)
            self.last_scan_time = current_time
            self.points_per_scan = len(filtered_points)
            self.clusters_per_scan = len(clusters)
            
            # Log scan results
            logger.debug("Scan completed", 
                        points=len(filtered_points),
                        clusters=len(clusters),
                        scan_count=self.scan_count)
            
            return True
            
        except Exception as e:
            logger.error("Error during scan", error=str(e))
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get driver status information"""
        return {
            "connected": self.connected,
            "scan_count": self.scan_count,
            "scans_per_second": self.scans_per_second,
            "points_per_scan": self.points_per_scan,
            "clusters_per_scan": self.clusters_per_scan,
            "obstacles_count": len(self.obstacles),
            "last_obstacle_update": self.last_obstacle_update,
            "port": self.port,
            "baud": self.baud
        }
    
    def run_continuous(self, scan_interval: float = 0.1):
        """Run continuous scanning loop"""
        if not self.connect():
            logger.error("Failed to connect to RPLIDAR")
            return
        
        logger.info("Starting continuous RPLIDAR scanning", interval=scan_interval)
        
        try:
            while self.connected:
                start_time = time.time()
                
                # Perform scan
                if self.scan_once():
                    # Log obstacles periodically
                    if self.scan_count % 100 == 0:
                        obstacles = self.get_obstacles()
                        distances = self.get_obstacle_distances()
                        logger.info("Scan summary", 
                                  scan_count=self.scan_count,
                                  obstacles=len(obstacles),
                                  distances=distances)
                
                # Maintain scan frequency
                elapsed = time.time() - start_time
                if elapsed < scan_interval:
                    time.sleep(scan_interval - elapsed)
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.disconnect()
    
    def run(self):
        """Main entry point for continuous operation"""
        self.run_continuous(1.0 / self.scan_frequency)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Team Omega RPLIDAR Driver")
    parser.add_argument("--port", help="RPLIDAR serial port")
    parser.add_argument("--baud", type=int, help="RPLIDAR baud rate")
    parser.add_argument("--frequency", type=int, help="Scan frequency (Hz)")
    parser.add_argument("--resolution", type=int, help="Angle resolution (degrees)")
    parser.add_argument("--single-scan", action="store_true", help="Perform single scan and exit")
    
    args = parser.parse_args()
    
    # Override environment variables with command line args
    if args.port:
        os.environ["RPLIDAR_PORT"] = args.port
    if args.baud:
        os.environ["RPLIDAR_BAUD"] = str(args.baud)
    if args.frequency:
        os.environ["LIDAR_SCAN_FREQUENCY"] = str(args.frequency)
    if args.resolution:
        os.environ["LIDAR_ANGLE_RESOLUTION"] = str(args.resolution)
    
    driver = RPLIDARDriver()
    
    if args.single_scan:
        if driver.connect():
            driver.scan_once()
            obstacles = driver.get_obstacles()
            distances = driver.get_obstacle_distances()
            status = driver.get_status()
            
            print(f"Single scan completed:")
            print(f"  Points: {status['points_per_scan']}")
            print(f"  Clusters: {status['clusters_per_scan']}")
            print(f"  Obstacles: {len(obstacles)}")
            print(f"  Distances: {distances}")
            
            for i, obstacle in enumerate(obstacles):
                print(f"  Obstacle {i+1}: {obstacle.obstacle_type.value} at "
                      f"{obstacle.center_angle_deg:.1f}°, {obstacle.center_distance_mm:.0f}mm "
                      f"(confidence: {obstacle.confidence:.2f})")
            
            driver.disconnect()
    else:
        driver.run()


if __name__ == "__main__":
    main()
