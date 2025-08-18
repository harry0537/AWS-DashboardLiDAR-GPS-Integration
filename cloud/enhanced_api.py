#!/usr/bin/env python3
"""
Team Omega - Enhanced Cloud API
Receives rich rover telemetry and provides enhanced endpoints for dashboard
"""

import os
import sys
import json
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import structlog

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
class EnhancedTelemetry:
    """Enhanced telemetry data structure"""
    device_id: str
    timestamp: float
    timestamp_iso: str
    
    # Position data
    position: Dict[str, Any]
    
    # Motion data
    motion: Dict[str, Any]
    
    # Battery data
    battery: Dict[str, Any]
    
    # Obstacle data
    obstacles: Dict[str, Any]
    
    # Sensor status
    sensors: Dict[str, Any]
    
    # System status
    system: Dict[str, Any]
    
    # Performance metrics
    performance: Dict[str, Any]


class EnhancedTelemetryStore:
    """Store for enhanced telemetry data"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.telemetry_history: List[EnhancedTelemetry] = []
        self.latest_telemetry: Optional[EnhancedTelemetry] = None
        self.device_status: Dict[str, Any] = {}
        
        # Performance tracking
        self.total_received = 0
        self.last_received_time = 0.0
        self.receive_rate_hz = 0.0
        
        # Data validation
        self.validation_errors = 0
        self.last_validation_error = 0.0
    
    def add_telemetry(self, telemetry_data: Dict[str, Any]) -> bool:
        """Add new telemetry data"""
        try:
            # Validate required fields
            required_fields = ['device_id', 'timestamp', 'position', 'motion', 'battery', 
                             'obstacles', 'sensors', 'system']
            
            for field in required_fields:
                if field not in telemetry_data:
                    logger.warning("Missing required field", field=field, data=telemetry_data)
                    self.validation_errors += 1
                    self.last_validation_error = time.time()
                    return False
            
            # Create enhanced telemetry object
            telemetry = EnhancedTelemetry(
                device_id=telemetry_data['device_id'],
                timestamp=telemetry_data['timestamp'],
                timestamp_iso=telemetry_data.get('timestamp_iso', ''),
                position=telemetry_data['position'],
                motion=telemetry_data['motion'],
                battery=telemetry_data['battery'],
                obstacles=telemetry_data['obstacles'],
                sensors=telemetry_data['sensors'],
                system=telemetry_data['system'],
                performance=telemetry_data.get('performance', {})
            )
            
            # Update latest telemetry
            self.latest_telemetry = telemetry
            
            # Add to history
            self.telemetry_history.append(telemetry)
            
            # Trim history if too long
            if len(self.telemetry_history) > self.max_history:
                self.telemetry_history = self.telemetry_history[-self.max_history:]
            
            # Update device status
            self.device_status[telemetry.device_id] = {
                'last_seen': telemetry.timestamp,
                'status': 'online',
                'mode': telemetry.system.get('mode', 'UNKNOWN'),
                'armed': telemetry.system.get('armed', False),
                'rtk_status': telemetry.system.get('rtk_status', 'NO_RTK'),
                'battery_health': telemetry.battery.get('health', 'unknown'),
                'obstacle_count': telemetry.obstacles.get('count', 0)
            }
            
            # Update performance metrics
            self.total_received += 1
            current_time = time.time()
            if self.last_received_time > 0:
                time_diff = current_time - self.last_received_time
                if time_diff > 0:
                    self.receive_rate_hz = 1.0 / time_diff
            self.last_received_time = current_time
            
            logger.debug("Added telemetry", 
                        device_id=telemetry.device_id,
                        timestamp=telemetry.timestamp,
                        obstacle_count=telemetry.obstacles.get('count', 0))
            
            return True
            
        except Exception as e:
            logger.error("Failed to add telemetry", error=str(e))
            self.validation_errors += 1
            self.last_validation_error = time.time()
            return False
    
    def get_latest_telemetry(self, device_id: Optional[str] = None) -> Optional[EnhancedTelemetry]:
        """Get latest telemetry for device"""
        if device_id:
            # Find latest for specific device
            for telemetry in reversed(self.telemetry_history):
                if telemetry.device_id == device_id:
                    return telemetry
            return None
        else:
            return self.latest_telemetry
    
    def get_telemetry_history(self, device_id: Optional[str] = None, 
                            limit: int = 100) -> List[EnhancedTelemetry]:
        """Get telemetry history for device"""
        if device_id:
            # Filter by device
            device_history = [t for t in self.telemetry_history if t.device_id == device_id]
            return device_history[-limit:]
        else:
            # Return all history
            return self.telemetry_history[-limit:]
    
    def get_device_status(self) -> Dict[str, Any]:
        """Get status of all devices"""
        return self.device_status
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health"""
        current_time = time.time()
        
        # Check device connectivity
        online_devices = 0
        total_devices = len(self.device_status)
        
        for device_id, status in self.device_status.items():
            if current_time - status['last_seen'] < 60:  # Online if seen in last minute
                online_devices += 1
        
        # Calculate health metrics
        health_percentage = (online_devices / total_devices * 100) if total_devices > 0 else 0
        
        if health_percentage >= 80:
            overall_status = "healthy"
        elif health_percentage >= 50:
            overall_status = "degraded"
        else:
            overall_status = "critical"
        
        return {
            'overall_status': overall_status,
            'health_percentage': health_percentage,
            'online_devices': online_devices,
            'total_devices': total_devices,
            'receive_rate_hz': self.receive_rate_hz,
            'total_received': self.total_received,
            'validation_errors': self.validation_errors,
            'last_received': self.last_received_time,
            'devices': self.device_status
        }
    
    def get_obstacle_summary(self) -> Dict[str, Any]:
        """Get obstacle detection summary"""
        if not self.latest_telemetry:
            return {}
        
        obstacles = self.latest_telemetry.obstacles
        
        return {
            'total_obstacles': obstacles.get('count', 0),
            'closest_distance_m': obstacles.get('closest_distance_m', float('inf')),
            'cardinal_distances': obstacles.get('cardinal_distances', {}),
            'confidence': obstacles.get('confidence', 0.0),
            'timestamp': obstacles.get('timestamp', 0),
            'obstacle_map': obstacles.get('obstacle_map', [])
        }
    
    def get_battery_summary(self) -> Dict[str, Any]:
        """Get battery status summary"""
        if not self.latest_telemetry:
            return {}
        
        battery = self.latest_telemetry.battery
        
        return {
            'voltage_v': battery.get('voltage_v', 0.0),
            'current_a': battery.get('current_a', 0.0),
            'percentage': battery.get('percentage', 0.0),
            'temperature_c': battery.get('temperature_c', 0.0),
            'health': battery.get('health', 'unknown'),
            'timestamp': battery.get('timestamp', 0)
        }


# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize telemetry store
telemetry_store = EnhancedTelemetryStore()

# Configuration
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    system_health = telemetry_store.get_system_health()
    
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'timestamp_iso': datetime.now(timezone.utc).isoformat(),
        'service': 'Team Omega Enhanced API',
        'version': '1.0.0',
        'system_health': system_health
    })


@app.route('/api/telemetry', methods=['POST'])
def receive_telemetry():
    """Receive enhanced telemetry data from rover"""
    try:
        # Get JSON data
        telemetry_data = request.get_json()
        
        if not telemetry_data:
            return jsonify({'error': 'No JSON data received'}), 400
        
        # Add to store
        success = telemetry_store.add_telemetry(telemetry_data)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Telemetry received',
                'timestamp': time.time(),
                'device_id': telemetry_data.get('device_id', 'unknown')
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to process telemetry',
                'timestamp': time.time()
            }), 400
            
    except Exception as e:
        logger.error("Error receiving telemetry", error=str(e))
        return jsonify({
            'status': 'error',
            'message': f'Internal error: {str(e)}',
            'timestamp': time.time()
        }), 500


@app.route('/api/telemetry/latest', methods=['GET'])
def get_latest_telemetry():
    """Get latest telemetry data"""
    device_id = request.args.get('device_id')
    telemetry = telemetry_store.get_latest_telemetry(device_id)
    
    if not telemetry:
        return jsonify({
            'status': 'error',
            'message': 'No telemetry data available',
            'timestamp': time.time()
        }), 404
    
    return jsonify({
        'status': 'success',
        'data': asdict(telemetry),
        'timestamp': time.time()
    })


@app.route('/api/telemetry/history', methods=['GET'])
def get_telemetry_history():
    """Get telemetry history"""
    device_id = request.args.get('device_id')
    limit = min(int(request.args.get('limit', 100)), 1000)  # Max 1000 records
    
    history = telemetry_store.get_telemetry_history(device_id, limit)
    
    return jsonify({
        'status': 'success',
        'data': [asdict(t) for t in history],
        'count': len(history),
        'timestamp': time.time()
    })


@app.route('/api/status/devices', methods=['GET'])
def get_device_status():
    """Get status of all devices"""
    device_status = telemetry_store.get_device_status()
    
    return jsonify({
        'status': 'success',
        'data': device_status,
        'count': len(device_status),
        'timestamp': time.time()
    })


@app.route('/api/status/system', methods=['GET'])
def get_system_status():
    """Get overall system status"""
    system_health = telemetry_store.get_system_health()
    
    return jsonify({
        'status': 'success',
        'data': system_health,
        'timestamp': time.time()
    })


@app.route('/api/obstacles/summary', methods=['GET'])
def get_obstacle_summary():
    """Get obstacle detection summary"""
    obstacle_summary = telemetry_store.get_obstacle_summary()
    
    if not obstacle_summary:
        return jsonify({
            'status': 'error',
            'message': 'No obstacle data available',
            'timestamp': time.time()
        }), 404
    
    return jsonify({
        'status': 'success',
        'data': obstacle_summary,
        'timestamp': time.time()
    })


@app.route('/api/battery/summary', methods=['GET'])
def get_battery_summary():
    """Get battery status summary"""
    battery_summary = telemetry_store.get_battery_summary()
    
    if not battery_summary:
        return jsonify({
            'status': 'error',
            'message': 'No battery data available',
            'timestamp': time.time()
        }), 404
    
    return jsonify({
        'status': 'success',
        'data': battery_summary,
        'timestamp': time.time()
    })


@app.route('/api/dashboard/summary', methods=['GET'])
def get_dashboard_summary():
    """Get comprehensive dashboard summary"""
    try:
        latest = telemetry_store.get_latest_telemetry()
        system_health = telemetry_store.get_system_health()
        
        if not latest:
            return jsonify({
                'status': 'error',
                'message': 'No telemetry data available',
                'timestamp': time.time()
            }), 404
        
        # Create dashboard summary
        summary = {
            'overview': {
                'device_id': latest.device_id,
                'status': 'online' if time.time() - latest.timestamp < 60 else 'offline',
                'last_update': latest.timestamp_iso,
                'uptime_seconds': latest.system.get('uptime_seconds', 0)
            },
            'position': {
                'latitude': latest.position.get('latitude', 0.0),
                'longitude': latest.position.get('longitude', 0.0),
                'altitude': latest.position.get('altitude', 0.0),
                'accuracy_m': latest.position.get('accuracy_m', 0.0)
            },
            'motion': {
                'speed_kmh': latest.motion.get('speed_kmh', 0.0),
                'heading_deg': latest.motion.get('heading_deg', 0.0),
                'mode': latest.system.get('mode', 'UNKNOWN'),
                'armed': latest.system.get('armed', False)
            },
            'battery': {
                'percentage': latest.battery.get('percentage', 0.0),
                'voltage_v': latest.battery.get('voltage_v', 0.0),
                'health': latest.battery.get('health', 'unknown'),
                'temperature_c': latest.battery.get('temperature_c', 0.0)
            },
            'obstacles': {
                'count': latest.obstacles.get('count', 0),
                'closest_distance_m': latest.obstacles.get('closest_distance_m', float('inf')),
                'cardinal_distances': latest.obstacles.get('cardinal_distances', {}),
                'confidence': latest.obstacles.get('confidence', 0.0)
            },
            'sensors': {
                'lidar': latest.sensors.get('lidar', 'disconnected'),
                'camera': latest.sensors.get('camera', 'disconnected'),
                'ultrasonic': latest.sensors.get('ultrasonic', 'disconnected'),
                'gps': latest.sensors.get('gps', 'disconnected'),
                'rtk_status': latest.system.get('rtk_status', 'NO_RTK')
            },
            'system': {
                'cpu_usage': latest.system.get('cpu_usage', 0.0),
                'memory_usage': latest.system.get('memory_usage', 0.0),
                'temperature_c': latest.system.get('temperature_c', 0.0),
                'overall_health': system_health['overall_status']
            }
        }
        
        return jsonify({
            'status': 'success',
            'data': summary,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error("Error creating dashboard summary", error=str(e))
        return jsonify({
            'status': 'error',
            'message': f'Internal error: {str(e)}',
            'timestamp': time.time()
        }), 500


@app.route('/dashboard', methods=['GET'])
def dashboard_view():
    """Enhanced dashboard view"""
    latest = telemetry_store.get_latest_telemetry()
    
    if not latest:
        return jsonify({
            'status': 'error',
            'message': 'No telemetry data available'
        }), 404
    
    # Create HTML dashboard
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Team Omega - Enhanced Rover Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            .status-good { color: #10B981; }
            .status-warning { color: #F59E0B; }
            .status-critical { color: #EF4444; }
            .status-unknown { color: #6B7280; }
        </style>
    </head>
    <body class="bg-gray-100">
        <div class="container mx-auto px-4 py-8">
            <header class="text-center mb-8">
                <h1 class="text-4xl font-bold text-gray-800 mb-2">🚀 Team Omega - Project Astra</h1>
                <p class="text-xl text-gray-600">Enhanced Rover Dashboard</p>
                <p class="text-sm text-gray-500 mt-2">Last Update: <span id="last-update">Loading...</span></p>
            </header>
            
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <!-- Position & Motion -->
                <div class="bg-white rounded-lg shadow-md p-6">
                    <h2 class="text-xl font-semibold mb-4 text-blue-600">📍 Position & Motion</h2>
                    <div class="space-y-3">
                        <div class="flex justify-between">
                            <span class="font-medium">Latitude:</span>
                            <span id="latitude">--</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="font-medium">Longitude:</span>
                            <span id="longitude">--</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="font-medium">Speed:</span>
                            <span id="speed">--</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="font-medium">Heading:</span>
                            <span id="heading">--</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="font-medium">Mode:</span>
                            <span id="mode" class="font-semibold">--</span>
                        </div>
                    </div>
                </div>
                
                <!-- Battery & System -->
                <div class="bg-white rounded-lg shadow-md p-6">
                    <h2 class="text-xl font-semibold mb-4 text-green-600">🔋 Battery & System</h2>
                    <div class="space-y-3">
                        <div class="flex justify-between">
                            <span class="font-medium">Battery:</span>
                            <span id="battery-percentage" class="font-semibold">--</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="font-medium">Voltage:</span>
                            <span id="battery-voltage">--</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="font-medium">Health:</span>
                            <span id="battery-health" class="font-semibold">--</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="font-medium">RTK Status:</span>
                            <span id="rtk-status" class="font-semibold">--</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="font-medium">Armed:</span>
                            <span id="armed" class="font-semibold">--</span>
                        </div>
                    </div>
                </div>
                
                <!-- Obstacles & Sensors -->
                <div class="bg-white rounded-lg shadow-md p-6">
                    <h2 class="text-xl font-semibold mb-4 text-red-600">🚧 Obstacles & Sensors</h2>
                    <div class="space-y-3">
                        <div class="flex justify-between">
                            <span class="font-medium">Obstacles:</span>
                            <span id="obstacle-count" class="font-semibold">--</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="font-medium">Closest:</span>
                            <span id="closest-distance">--</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="font-medium">LiDAR:</span>
                            <span id="lidar-status" class="font-semibold">--</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="font-medium">Camera:</span>
                            <span id="camera-status" class="font-semibold">--</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="font-medium">GPS:</span>
                            <span id="gps-status" class="font-semibold">--</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Map -->
            <div class="mt-8 bg-white rounded-lg shadow-md p-6">
                <h2 class="text-xl font-semibold mb-4 text-purple-600">🗺️ Rover Location</h2>
                <div id="map" class="h-96 rounded-lg"></div>
            </div>
            
            <!-- Obstacle Visualization -->
            <div class="mt-8 bg-white rounded-lg shadow-md p-6">
                <h2 class="text-xl font-semibold mb-4 text-orange-600">📊 Obstacle Map (360° View)</h2>
                <div class="flex justify-center">
                    <canvas id="obstacle-canvas" width="400" height="400" class="border border-gray-300 rounded-lg"></canvas>
                </div>
                <div class="text-center mt-4 text-sm text-gray-600">
                    <p>Center = Rover, Outer ring = 8m, Colors = Distance (Green=Far, Red=Close)</p>
                </div>
            </div>
        </div>
        
        <script>
            // Initialize map
            const map = L.map('map').setView([0, 0], 16);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);
            
            let roverMarker = null;
            
            // Update dashboard data
            function updateDashboard() {
                fetch('/api/dashboard/summary')
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            const d = data.data;
                            
                            // Update position & motion
                            document.getElementById('latitude').textContent = d.position.latitude.toFixed(6);
                            document.getElementById('longitude').textContent = d.position.longitude.toFixed(6);
                            document.getElementById('speed').textContent = d.motion.speed_kmh.toFixed(1) + ' km/h';
                            document.getElementById('heading').textContent = d.motion.heading_deg.toFixed(1) + '°';
                            document.getElementById('mode').textContent = d.motion.mode;
                            
                            // Update battery & system
                            document.getElementById('battery-percentage').textContent = d.battery.percentage.toFixed(1) + '%';
                            document.getElementById('battery-voltage').textContent = d.battery.voltage_v.toFixed(1) + 'V';
                            document.getElementById('battery-health').textContent = d.battery.health;
                            document.getElementById('rtk-status').textContent = d.sensors.rtk_status;
                            document.getElementById('armed').textContent = d.motion.armed ? 'YES' : 'NO';
                            
                            // Update obstacles & sensors
                            document.getElementById('obstacle-count').textContent = d.obstacles.count;
                            document.getElementById('closest-distance').textContent = d.obstacles.closest_distance_m.toFixed(1) + 'm';
                            document.getElementById('lidar-status').textContent = d.sensors.lidar;
                            document.getElementById('camera-status').textContent = d.sensors.camera;
                            document.getElementById('gps-status').textContent = d.sensors.gps;
                            
                            // Update map
                            const lat = d.position.latitude;
                            const lon = d.position.longitude;
                            
                            if (lat !== 0 && lon !== 0) {
                                if (roverMarker) {
                                    map.removeLayer(roverMarker);
                                }
                                
                                roverMarker = L.marker([lat, lon]).addTo(map);
                                map.setView([lat, lon], 16);
                                
                                // Add popup with rover info
                                roverMarker.bindPopup(`
                                    <b>Team Omega Rover</b><br>
                                    Mode: ${d.motion.mode}<br>
                                    Speed: ${d.motion.speed_kmh.toFixed(1)} km/h<br>
                                    Battery: ${d.battery.percentage.toFixed(1)}%<br>
                                    RTK: ${d.sensors.rtk_status}
                                `);
                            }
                            
                            // Update obstacle visualization
                            updateObstacleVisualization(d.obstacles);
                            
                            // Update timestamp
                            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                        }
                    })
                    .catch(error => {
                        console.error('Error updating dashboard:', error);
                    });
            }
            
            // Update obstacle visualization
            function updateObstacleVisualization(obstacles) {
                const canvas = document.getElementById('obstacle-canvas');
                const ctx = canvas.getContext('2d');
                
                // Clear canvas
                ctx.clearRect(0, 0, 400, 400);
                
                // Draw rover (center)
                ctx.beginPath();
                ctx.arc(200, 200, 10, 0, 2 * Math.PI);
                ctx.fillStyle = '#3B82F6';
                ctx.fill();
                ctx.strokeStyle = '#1E40AF';
                ctx.lineWidth = 2;
                ctx.stroke();
                
                // Draw obstacle map if available
                if (obstacles.obstacle_map && obstacles.obstacle_map.length > 0) {
                    const centerX = 200;
                    const centerY = 200;
                    const maxRadius = 180;
                    
                    obstacles.obstacle_map.forEach((distance, index) => {
                        if (distance > 0) {
                            const angle = (index * 5 - 90) * Math.PI / 180; // Start from front (-90°)
                            const radius = (distance / 800) * maxRadius; // Scale to canvas
                            
                            const x = centerX + radius * Math.cos(angle);
                            const y = centerY + radius * Math.sin(angle);
                            
                            // Color based on distance (green=far, red=close)
                            const normalizedDistance = Math.min(distance / 800, 1);
                            const red = Math.round(255 * (1 - normalizedDistance));
                            const green = Math.round(255 * normalizedDistance);
                            
                            ctx.beginPath();
                            ctx.arc(x, y, 3, 0, 2 * Math.PI);
                            ctx.fillStyle = `rgb(${red}, ${green}, 0)`;
                            ctx.fill();
                        }
                    });
                }
                
                // Draw cardinal directions
                ctx.strokeStyle = '#9CA3AF';
                ctx.lineWidth = 1;
                ctx.setLineDash([5, 5]);
                
                // Front (North)
                ctx.beginPath();
                ctx.moveTo(200, 20);
                ctx.lineTo(200, 180);
                ctx.stroke();
                
                // Right (East)
                ctx.beginPath();
                ctx.moveTo(220, 200);
                ctx.lineTo(380, 200);
                ctx.stroke();
                
                // Back (South)
                ctx.beginPath();
                ctx.moveTo(200, 220);
                ctx.lineTo(200, 380);
                ctx.stroke();
                
                // Left (West)
                ctx.beginPath();
                ctx.moveTo(20, 200);
                ctx.lineTo(180, 200);
                ctx.stroke();
                
                ctx.setLineDash([]);
                
                // Add labels
                ctx.fillStyle = '#6B7280';
                ctx.font = '12px Arial';
                ctx.textAlign = 'center';
                ctx.fillText('Front', 200, 15);
                ctx.fillText('Right', 385, 195);
                ctx.fillText('Back', 200, 395);
                ctx.fillText('Left', 15, 195);
            }
            
            // Update dashboard every 2 seconds
            updateDashboard();
            setInterval(updateDashboard, 2000);
        </script>
    </body>
    </html>
    """
    
    return html_template


if __name__ == '__main__':
    # Load configuration
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    
    logger.info("Starting Team Omega Enhanced API", 
                port=port, 
                debug=debug, 
                host=host)
    
    # Start Flask app
    app.run(host=host, port=port, debug=debug)
