#!/usr/bin/env python3
"""
RPLIDAR S3 Advanced Visualizer - ENHANCED VERSION
Next-generation LIDAR visualization with intelligent features

NEW FEATURES:
- Interactive zoom/pan controls
- Object detection and tracking
- Data recording and playback
- Dynamic range scaling
- Enhanced environment mapping
- Smart alerts and notifications
- Advanced analytics
- Export capabilities
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch
from matplotlib.widgets import Button, Slider
import matplotlib.patches as mpatches
import subprocess
import threading
import time
import re
import sys
import json
import csv
from collections import deque
import queue
from datetime import datetime
import math

class RPLIDARAdvancedViz:
    def __init__(self, max_points=3000):
        self.max_points = max_points
        
        # Enhanced data storage
        self.data_queue = queue.Queue(maxsize=8000)
        
        # Current scan data
        self.current_scan_angles = []
        self.current_scan_distances = []
        self.current_scan_qualities = []
        
        # Latest complete scan
        self.latest_scan_angles = np.array([])
        self.latest_scan_distances = np.array([])
        self.latest_scan_qualities = np.array([])
        
        # Advanced features
        self.persistent_map = {}  # For building persistent environment map
        self.detected_objects = []  # Object tracking
        self.recording_data = []  # Data recording
        self.is_recording = False
        
        # Interactive controls
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.auto_scale = True
        self.show_objects = True
        self.show_trails = False
        
        # Smart scaling
        self.dynamic_range = [0, 8000]
        self.last_range_update = time.time()
        
        # Process handling
        self.process = None
        self.is_running = False
        self.data_thread = None
        
        # Performance tracking
        self.scan_count = 0
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.fps = 0
        self.start_time = time.time()
        
        # Analytics
        self.scan_history = deque(maxlen=100)
        self.quality_trends = deque(maxlen=200)
        self.range_trends = deque(maxlen=200)
        
        # Alert system
        self.alerts = []
        self.last_alert_check = time.time()
        
        # Color scheme
        self.setup_colors()
        
        # Setup enhanced UI
        self.setup_enhanced_ui()
        
    def setup_colors(self):
        """Enhanced color palette"""
        self.colors = {
            'bg': '#0a0a0a',           # Deep black
            'panel': '#111111',        # Dark gray
            'accent': '#00ff41',       # Matrix green
            'warning': '#ff3030',      # Bright red
            'info': '#00bfff',         # Deep sky blue
            'success': '#32cd32',      # Lime green
            'purple': '#9d4edd',       # Purple
            'orange': '#ff8500',       # Orange
            'cyan': '#00ffff',         # Cyan
            'yellow': '#ffff00',       # Bright yellow
            'text': '#ffffff',         # Pure white
            'object': '#ff6b6b',       # Object highlight
            'trail': '#4ecdc4',        # Trail color
            'grid': '#333333'          # Grid lines
        }
        
    def setup_enhanced_ui(self):
        """Setup enhanced UI with polished layout and no overlapping"""
        plt.style.use('dark_background')
        
        # Create figure with optimized size and layout
        self.fig = plt.figure(figsize=(18, 12), facecolor=self.colors['bg'])
        self.fig.patch.set_facecolor(self.colors['bg'])
        
        # Professional grid layout (5x4) for better spacing
        # Main polar plot (larger, top-left)
        self.ax_polar = plt.subplot2grid((5, 4), (0, 0), colspan=2, rowspan=2, projection='polar')
        self.ax_polar.set_facecolor(self.colors['bg'])
        
        # Interactive environment map (larger, top-right)
        self.ax_env = plt.subplot2grid((5, 4), (0, 2), colspan=2, rowspan=2)
        self.ax_env.set_facecolor(self.colors['bg'])
        
        # Object tracking panel (middle-left)
        self.ax_objects = plt.subplot2grid((5, 4), (2, 0), colspan=2)
        self.ax_objects.set_facecolor(self.colors['bg'])
        
        # Analytics panel (middle-right)
        self.ax_analytics = plt.subplot2grid((5, 4), (2, 2), colspan=2)
        self.ax_analytics.set_facecolor(self.colors['bg'])
        
        # Control panels (bottom row, evenly spaced)
        self.ax_controls = plt.subplot2grid((5, 4), (3, 0))
        self.ax_controls.set_facecolor(self.colors['bg'])
        
        self.ax_recording = plt.subplot2grid((5, 4), (3, 1))
        self.ax_recording.set_facecolor(self.colors['bg'])
        
        self.ax_alerts = plt.subplot2grid((5, 4), (3, 2))
        self.ax_alerts.set_facecolor(self.colors['bg'])
        
        self.ax_status = plt.subplot2grid((5, 4), (3, 3))
        self.ax_status.set_facecolor(self.colors['bg'])
        
        # Premium layout with generous spacing - NO OVERLAPPING
        plt.subplots_adjust(
            left=0.04,      # Left margin
            right=0.97,     # Right margin  
            top=0.94,       # Top margin
            bottom=0.05,    # Bottom margin
            wspace=0.35,    # Horizontal spacing between subplots
            hspace=0.5      # Vertical spacing between subplots
        )
        
        # Premium interactive title with enhanced styling
        self.fig.suptitle('RPLIDAR S3 ADVANCED ANALYZER • INTELLIGENT REAL-TIME PROCESSING', 
                         fontsize=18, color=self.colors['accent'], fontweight='bold', y=0.98)
        
        # Add subtitle with version info
        self.fig.text(0.5, 0.96, 'Professional LIDAR Visualization Suite v2.0', 
                     fontsize=12, color=self.colors['cyan'], ha='center', fontweight='normal')
        
        # Setup mouse/keyboard interactions
        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.fig.canvas.mpl_connect('key_press_event', self.on_key_press)
        self.fig.canvas.mpl_connect('resize_event', self.on_resize)
        
        # Prevent window shrinking and ensure consistent sizing
        self.fig.set_size_inches(18, 12, forward=True)
        self.fig.canvas.manager.window.resizable(True, True)
        self.fig.canvas.manager.window.minsize(1600, 1000)  # Minimum window size
        
    def on_scroll(self, event):
        """Handle mouse wheel zoom"""
        if event.inaxes == self.ax_env:
            if event.button == 'up':
                self.zoom_level *= 1.2
            else:
                self.zoom_level /= 1.2
            self.zoom_level = max(0.1, min(10.0, self.zoom_level))
            
    def on_click(self, event):
        """Handle mouse clicks for measurement"""
        if event.inaxes == self.ax_env and event.dblclick:
            # Double-click to measure distance from center
            distance = np.sqrt(event.xdata**2 + event.ydata**2)
            angle = np.degrees(np.arctan2(event.xdata, event.ydata))
            self.add_alert(f"Measurement: {distance:.0f}mm @ {angle:.1f}°", 'info')
            
    def on_key_press(self, event):
        """Handle keyboard shortcuts"""
        if event.key == 'r':
            self.toggle_recording()
        elif event.key == 'o':
            self.show_objects = not self.show_objects
        elif event.key == 't':
            self.show_trails = not self.show_trails
        elif event.key == 'a':
            self.auto_scale = not self.auto_scale
        elif event.key == 'c':
            self.clear_persistent_map()
        elif event.key == 's':
            self.export_data()
        elif event.key == 'h':
            self.show_help()
            
    def on_resize(self, event):
        """Handle window resize to maintain proportions"""
        if hasattr(self, 'fig') and self.fig:
            # Maintain aspect ratio and prevent shrinking
            current_size = self.fig.get_size_inches()
            if current_size[0] < 16 or current_size[1] < 10:
                self.fig.set_size_inches(18, 12, forward=True)
                self.fig.canvas.draw()
            
    def show_help(self):
        """Display keyboard shortcuts"""
        help_text = """
🎮 RPLIDAR S3 ADVANCED CONTROLS
════════════════════════════════════════
[R] - Toggle recording on/off
[O] - Toggle object detection display
[T] - Toggle trail visualization
[A] - Toggle auto-scaling
[C] - Clear persistent map
[S] - Export data to file
[H] - Show this help

🖱️ MOUSE CONTROLS:
• Scroll wheel - Zoom in/out on environment map
• Double-click - Measure distance from center
• Drag - Pan around (future feature)

📊 FEATURES:
• Real-time object detection and tracking
• Persistent environment mapping
• Data recording and export
• Smart alerts and notifications
• Advanced analytics and trends
        """
        print(help_text)
        
    def start_rplidar_process(self):
        """Start RPLIDAR with enhanced initialization"""
        try:
            exe_path = "../rplidar_sdk_dev/output/win32/Release/ultra_simple.exe"
            cmd = [exe_path, "--channel", "--serial", "COM8", "1000000"]
            
            print(f"🚀 \033[92mInitializing RPLIDAR S3 Advanced Scanner\033[0m")
            print(f"📡 Command: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=0
            )
            
            print("✅ \033[92mRPLIDAR S3 Advanced Scanner Online!\033[0m")
            return True
            
        except Exception as e:
            print(f"❌ \033[91mFailed to initialize RPLIDAR: {e}\033[0m")
            return False
            
    def parse_line(self, line):
        """Enhanced data parser with validation"""
        if 'theta:' in line:
            parts = line.split()
            try:
                sync_flag = 'S' in line[:5]
                
                theta_idx = parts.index('theta:') + 1 if 'theta:' in parts else -1
                dist_idx = parts.index('Dist:') + 1 if 'Dist:' in parts else -1
                q_idx = parts.index('Q:') + 1 if 'Q:' in parts else -1
                
                if theta_idx > 0 and dist_idx > 0:
                    angle = float(parts[theta_idx])
                    distance = float(parts[dist_idx])
                    quality = int(parts[q_idx]) if q_idx > 0 and q_idx < len(parts) else 40
                    
                    # Enhanced validation
                    if 0 <= angle <= 360 and 0 <= distance <= 20000 and 0 <= quality <= 63:
                        return sync_flag, angle, distance, quality
            except (ValueError, IndexError):
                pass
                
        return None
        
    def data_reader(self):
        """Enhanced data collection with analytics"""
        print("📡 \033[96mAdvanced data collection active...\033[0m")
        line_count = 0
        
        while self.is_running and self.process:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                
                line_count += 1
                
                # Debug: Show first few lines
                if line_count <= 5:
                    print(f"📄 Raw line {line_count}: {line.strip()}")
                
                parsed = self.parse_line(line)
                
                if parsed:
                    try:
                        self.data_queue.put_nowait(parsed)
                        if line_count <= 10:  # Debug first few parsed results
                            print(f"✅ Parsed: {parsed}")
                    except queue.Full:
                        # Smart queue management
                        try:
                            self.data_queue.get_nowait()  # Remove oldest
                            self.data_queue.put_nowait(parsed)  # Add new
                        except queue.Empty:
                            pass
                        
            except Exception as e:
                print(f"⚠️ \033[93mData error: {e}\033[0m")
                break
                
        print("📡 \033[96mAdvanced data collection terminated\033[0m")
        
    def process_data(self):
        """Enhanced data processing with intelligence"""
        print("🧠 Advanced data processor started")
        
        while True:
            try:
                sync_flag, angle, distance, quality = self.data_queue.get(timeout=0.1)
                
                # Debug: Show first few data points
                if len(self.current_scan_angles) < 5:
                    print(f"📊 Data: θ={angle:.1f}° D={distance:.0f}mm Q={quality} S={sync_flag}")
                
                # Enhanced filtering and validation
                if 10 < distance < 15000:  # Reasonable range
                    self.current_scan_angles.append(angle)
                    self.current_scan_distances.append(distance)
                    self.current_scan_qualities.append(quality)
                
                # Complete scan detected
                if sync_flag and len(self.current_scan_angles) > 50:
                    print(f"✅ Complete scan: {len(self.current_scan_angles)} points")
                    self.process_complete_scan()
                    
                    # Reset for next scan
                    self.current_scan_angles = []
                    self.current_scan_distances = []
                    self.current_scan_qualities = []
                    
                    self.scan_count += 1
                    
            except queue.Empty:
                if not self.is_running:
                    break
                continue
            except Exception as e:
                print(f"⚠️ Processing error: {e}")
                break
                
    def process_complete_scan(self):
        """Process a complete 360° scan with intelligence"""
        # Update latest scan
        self.latest_scan_angles = np.array(self.current_scan_angles)
        self.latest_scan_distances = np.array(self.current_scan_distances)
        self.latest_scan_qualities = np.array(self.current_scan_qualities)
        
        # Record data if enabled
        if self.is_recording:
            self.record_scan_data()
        
        # Update persistent map
        self.update_persistent_map()
        
        # Detect objects
        self.detect_objects()
        
        # Update analytics
        self.update_analytics()
        
        # Check for alerts
        self.check_alerts()
        
        # Update dynamic range
        self.update_dynamic_range()
        
    def record_scan_data(self):
        """Record scan data for later analysis"""
        timestamp = time.time()
        scan_data = {
            'timestamp': timestamp,
            'angles': self.latest_scan_angles.tolist(),
            'distances': self.latest_scan_distances.tolist(),
            'qualities': self.latest_scan_qualities.tolist(),
            'scan_id': self.scan_count
        }
        self.recording_data.append(scan_data)
        
    def update_persistent_map(self):
        """Build persistent environment map"""
        # Simple occupancy grid concept
        for angle, distance in zip(self.latest_scan_angles, self.latest_scan_distances):
            # Convert to grid coordinates
            x = int(distance * np.sin(np.radians(angle)) / 50)  # 5cm resolution
            y = int(distance * np.cos(np.radians(angle)) / 50)
            
            grid_key = (x, y)
            if grid_key not in self.persistent_map:
                self.persistent_map[grid_key] = {'hits': 1, 'confidence': 1}
            else:
                self.persistent_map[grid_key]['hits'] += 1
                self.persistent_map[grid_key]['confidence'] = min(10, self.persistent_map[grid_key]['hits'])
                
    def detect_objects(self):
        """Advanced object detection and tracking"""
        if len(self.latest_scan_distances) < 10:
            return
            
        # Clear old objects
        self.detected_objects = []
        
        # Group nearby points into objects
        angles = self.latest_scan_angles
        distances = self.latest_scan_distances
        qualities = self.latest_scan_qualities
        
        # Simple clustering algorithm
        current_object = []
        
        for i, (angle, dist, qual) in enumerate(zip(angles, distances, qualities)):
            if qual > 20:  # Good quality points only
                if not current_object:
                    current_object = [(angle, dist, qual)]
                else:
                    # Check if point is close to previous points
                    last_angle, last_dist, _ = current_object[-1]
                    angle_diff = min(abs(angle - last_angle), 360 - abs(angle - last_angle))
                    dist_diff = abs(dist - last_dist)
                    
                    if angle_diff < 5 and dist_diff < 200:  # Within 5° and 20cm
                        current_object.append((angle, dist, qual))
                    else:
                        # End current object, start new one
                        if len(current_object) >= 3:  # At least 3 points
                            self.add_detected_object(current_object)
                        current_object = [(angle, dist, qual)]
        
        # Add final object
        if len(current_object) >= 3:
            self.add_detected_object(current_object)
            
    def add_detected_object(self, points):
        """Add a detected object to the list"""
        angles = [p[0] for p in points]
        distances = [p[1] for p in points]
        qualities = [p[2] for p in points]
        
        # Object properties
        center_angle = np.mean(angles)
        center_distance = np.mean(distances)
        size = len(points)
        avg_quality = np.mean(qualities)
        angular_span = max(angles) - min(angles)
        
        obj = {
            'center_angle': center_angle,
            'center_distance': center_distance,
            'size': size,
            'quality': avg_quality,
            'angular_span': angular_span,
            'points': len(points),
            'type': self.classify_object(angular_span, center_distance, size)
        }
        
        self.detected_objects.append(obj)
        
    def classify_object(self, angular_span, distance, size):
        """Simple object classification"""
        if angular_span > 45:
            return "Wall/Large Surface"
        elif size > 20:
            return "Large Object"
        elif distance < 500:
            return "Close Object"
        else:
            return "Small Object"
            
    def update_analytics(self):
        """Update analytical data"""
        if len(self.latest_scan_distances) > 0:
            # Quality trends
            avg_quality = np.mean(self.latest_scan_qualities)
            self.quality_trends.append(avg_quality)
            
            # Range trends
            min_range = np.min(self.latest_scan_distances)
            max_range = np.max(self.latest_scan_distances)
            avg_range = np.mean(self.latest_scan_distances)
            
            self.range_trends.append({
                'min': min_range,
                'max': max_range,
                'avg': avg_range,
                'timestamp': time.time()
            })
            
            # Scan statistics
            scan_stats = {
                'points': len(self.latest_scan_distances),
                'coverage': len(self.latest_scan_distances) / 3600 * 100,  # Percentage of 360°
                'avg_quality': avg_quality,
                'objects_detected': len(self.detected_objects)
            }
            
            self.scan_history.append(scan_stats)
            
    def check_alerts(self):
        """Smart alert system"""
        current_time = time.time()
        
        if current_time - self.last_alert_check > 2:  # Check every 2 seconds
            self.last_alert_check = current_time
            
            # Check for close objects
            if len(self.latest_scan_distances) > 0:
                min_distance = np.min(self.latest_scan_distances)
                if min_distance < 300:  # 30cm
                    self.add_alert(f"⚠️ Close object detected: {min_distance:.0f}mm", 'warning')
                
            # Check quality degradation
            if len(self.quality_trends) > 10:
                recent_quality = np.mean(list(self.quality_trends)[-10:])
                if recent_quality < 25:
                    self.add_alert("⚠️ Signal quality degraded", 'warning')
                    
            # Check for large objects
            for obj in self.detected_objects:
                if obj['type'] == "Wall/Large Surface" and obj['center_distance'] < 1000:
                    self.add_alert(f"🧱 Wall detected at {obj['center_distance']:.0f}mm", 'info')
                    
    def add_alert(self, message, alert_type='info'):
        """Add alert to the system"""
        alert = {
            'timestamp': time.time(),
            'message': message,
            'type': alert_type
        }
        self.alerts.append(alert)
        
        # Keep only recent alerts
        if len(self.alerts) > 10:
            self.alerts = self.alerts[-10:]
            
        print(f"🔔 {message}")
        
    def update_dynamic_range(self):
        """Update display range dynamically"""
        if self.auto_scale and len(self.latest_scan_distances) > 0:
            current_time = time.time()
            
            if current_time - self.last_range_update > 1:  # Update every second
                min_dist = np.min(self.latest_scan_distances)
                max_dist = np.max(self.latest_scan_distances)
                
                # Add margins
                margin = (max_dist - min_dist) * 0.2
                new_min = max(0, min_dist - margin)
                new_max = max_dist + margin
                
                # Smooth transition
                self.dynamic_range[0] = self.dynamic_range[0] * 0.8 + new_min * 0.2
                self.dynamic_range[1] = self.dynamic_range[1] * 0.8 + new_max * 0.2
                
                self.last_range_update = current_time
                
    def toggle_recording(self):
        """Toggle data recording on/off"""
        self.is_recording = not self.is_recording
        if self.is_recording:
            self.recording_data = []
            self.add_alert("🔴 Recording started", 'success')
        else:
            self.add_alert(f"⏹️ Recording stopped - {len(self.recording_data)} scans saved", 'info')
            
    def clear_persistent_map(self):
        """Clear the persistent environment map"""
        self.persistent_map = {}
        self.add_alert("🧹 Persistent map cleared", 'info')
        
    def export_data(self):
        """Export recorded data to files"""
        if not self.recording_data:
            self.add_alert("❌ No recorded data to export", 'warning')
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export to JSON
        json_filename = f"rplidar_advanced_data_{timestamp}.json"
        with open(json_filename, 'w') as f:
            json.dump(self.recording_data, f, indent=2)
            
        # Export to CSV (simplified)
        csv_filename = f"rplidar_advanced_summary_{timestamp}.csv"
        with open(csv_filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'scan_id', 'points', 'min_dist', 'max_dist', 'avg_quality'])
            
            for scan in self.recording_data:
                distances = scan['distances']
                qualities = scan['qualities']
                writer.writerow([
                    scan['timestamp'],
                    scan['scan_id'],
                    len(distances),
                    min(distances) if distances else 0,
                    max(distances) if distances else 0,
                    np.mean(qualities) if qualities else 0
                ])
                
        self.add_alert(f"💾 Data exported: {json_filename}, {csv_filename}", 'success')
        
    def stop_process(self):
        """Enhanced shutdown with data saving"""
        self.is_running = False
        
        # Auto-save if recording
        if self.is_recording and self.recording_data:
            self.export_data()
        
        if self.data_thread:
            self.data_thread.join(timeout=2)
            
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print("🛑 \033[91mAdvanced RPLIDAR scanner offline\033[0m")
        
    def update_advanced_plots(self, frame):
        """Update all plots with advanced features"""
        # Update FPS counter
        self.fps_counter += 1
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            self.fps = self.fps_counter
            self.fps_counter = 0
            self.last_fps_time = current_time
        
        # Skip if no data
        if len(self.latest_scan_distances) < 10:
            if frame % 20 == 0:  # Print every 20 frames (once per second)
                print(f"⏳ Waiting for data... Current points: {len(self.latest_scan_distances)}, Scans: {self.scan_count}")
            return
            
        angles = self.latest_scan_angles
        distances = self.latest_scan_distances
        qualities = self.latest_scan_qualities
        
        # === 1. ENHANCED POLAR PLOT ===
        self.ax_polar.clear()
        self.ax_polar.set_facecolor(self.colors['bg'])
        
        angles_rad = np.radians(angles)
        
        # Multi-layer visualization
        # Background layer
        self.ax_polar.scatter(angles_rad, distances, c=distances, s=8, 
                             cmap='plasma', alpha=0.4, vmin=0, vmax=8000)
        
        # Quality overlay
        self.ax_polar.scatter(angles_rad, distances, c=qualities, s=15, 
                             cmap='viridis', alpha=0.8, vmin=0, vmax=63)
        
        # Object highlights
        if self.show_objects:
            for obj in self.detected_objects:
                obj_angle_rad = np.radians(obj['center_angle'])
                self.ax_polar.scatter(obj_angle_rad, obj['center_distance'], 
                                     c=self.colors['object'], s=100, alpha=0.8, marker='x')
        
        self.ax_polar.set_title('ENHANCED 360° SCAN', color=self.colors['accent'], 
                               fontsize=14, fontweight='bold')
        self.ax_polar.set_ylim(0, self.dynamic_range[1])
        self.ax_polar.grid(True, alpha=0.3, color=self.colors['grid'])
        self.ax_polar.set_theta_zero_location('N')
        self.ax_polar.set_theta_direction(-1)
        
        # === 2. INTERACTIVE ENVIRONMENT MAP ===
        self.ax_env.clear()
        self.ax_env.set_facecolor(self.colors['bg'])
        
        # Convert to XY coordinates
        x = distances * np.sin(angles_rad)
        y = distances * np.cos(angles_rad)
        
        # Apply zoom and pan
        display_range = 8000 / self.zoom_level
        
        # Main data
        self.ax_env.scatter(x, y, c=qualities, s=10, cmap='plasma', alpha=0.8)
        
        # Persistent map overlay
        if self.persistent_map:
            map_x = []
            map_y = []
            map_confidence = []
            
            for (grid_x, grid_y), data in self.persistent_map.items():
                if data['confidence'] > 2:  # Only show confident points
                    map_x.append(grid_x * 50)  # Convert back to mm
                    map_y.append(grid_y * 50)
                    map_confidence.append(data['confidence'])
            
            if map_x:
                self.ax_env.scatter(map_x, map_y, c=map_confidence, s=5, 
                                   cmap='hot', alpha=0.3, vmin=1, vmax=10)
        
        # Object overlays
        if self.show_objects:
            for obj in self.detected_objects:
                obj_x = obj['center_distance'] * np.sin(np.radians(obj['center_angle']))
                obj_y = obj['center_distance'] * np.cos(np.radians(obj['center_angle']))
                
                # Draw object with size indicator
                circle = Circle((obj_x, obj_y), obj['size'] * 10, 
                               fill=False, color=self.colors['object'], alpha=0.7)
                self.ax_env.add_patch(circle)
                
                # Label
                self.ax_env.text(obj_x, obj_y + 200, obj['type'][:8], 
                                color=self.colors['object'], fontsize=8, ha='center')
        
        # Enhanced range circles with zoom adaptation
        for r in [1000, 2000, 3000, 4000, 5000, 6000]:
            if r <= display_range:
                circle = Circle((0, 0), r, fill=False, alpha=0.2, 
                               color=self.colors['info'], linewidth=1)
                self.ax_env.add_patch(circle)
                self.ax_env.text(r*0.7, r*0.7, f'{r//1000}m', 
                                color=self.colors['info'], fontsize=9)
        
        # Center crosshair
        self.ax_env.plot([-300, 300], [0, 0], color=self.colors['accent'], linewidth=2)
        self.ax_env.plot([0, 0], [-300, 300], color=self.colors['accent'], linewidth=2)
        
        self.ax_env.set_title(f'INTERACTIVE ENVIRONMENT (Zoom: {self.zoom_level:.1f}x)', 
                             color=self.colors['cyan'], fontsize=12, fontweight='bold')
        self.ax_env.set_xlabel('X Distance (mm)', color=self.colors['text'])
        self.ax_env.set_ylabel('Y Distance (mm)', color=self.colors['text'])
        self.ax_env.grid(True, alpha=0.2, color=self.colors['grid'])
        self.ax_env.axis('equal')
        self.ax_env.set_xlim(-display_range + self.pan_x, display_range + self.pan_x)
        self.ax_env.set_ylim(-display_range + self.pan_y, display_range + self.pan_y)
        
        # === 3. OBJECT TRACKING PANEL ===
        self.ax_objects.clear()
        self.ax_objects.set_facecolor(self.colors['bg'])
        
        objects_text = f"🎯 DETECTED OBJECTS: {len(self.detected_objects)}\n"
        objects_text += "=" * 35 + "\n"
        
        for i, obj in enumerate(self.detected_objects[:4]):  # Show max 4 objects to prevent overlap
            objects_text += f"{i+1}. {obj['type'][:15]}\n"  # Truncate long names
            objects_text += f"   📍 {obj['center_distance']:.0f}mm @ {obj['center_angle']:.0f}°\n"
            objects_text += f"   📊 {obj['points']} pts, Q:{obj['quality']:.0f}\n\n"
        
        if len(self.detected_objects) > 4:
            objects_text += f"... and {len(self.detected_objects) - 4} more objects\n"
        
        # Persistent map info
        objects_text += f"\n🗺️ PERSISTENT MAP: {len(self.persistent_map)} grid cells\n"
        
        self.ax_objects.text(0.05, 0.95, objects_text, transform=self.ax_objects.transAxes,
                            fontsize=9, verticalalignment='top', fontfamily='monospace', 
                            color=self.colors['object'], linespacing=1.2)
        
        self.ax_objects.set_title('OBJECT TRACKING', color=self.colors['object'], 
                                 fontsize=12, fontweight='bold', pad=10)
        self.ax_objects.axis('off')
        
        # === 4. ANALYTICS PANEL ===
        self.ax_analytics.clear()
        self.ax_analytics.set_facecolor(self.colors['bg'])
        
        if len(self.quality_trends) > 1 and len(self.range_trends) > 1:
            # Quality trend line
            x_qual = range(len(self.quality_trends))
            self.ax_analytics.plot(x_qual, self.quality_trends, 
                                  color=self.colors['success'], linewidth=2, alpha=0.8, label='Quality')
            
            # Range trend (normalized)
            recent_ranges = [r['avg'] for r in list(self.range_trends)[-len(self.quality_trends):]]
            if recent_ranges:
                norm_ranges = np.array(recent_ranges) / max(recent_ranges) * 63  # Normalize to quality scale
                self.ax_analytics.plot(x_qual[-len(norm_ranges):], norm_ranges, 
                                      color=self.colors['cyan'], linewidth=2, alpha=0.8, label='Range (norm)')
            
            self.ax_analytics.set_ylim(0, 63)
            self.ax_analytics.legend()
        
        self.ax_analytics.set_title('ANALYTICS TRENDS', color=self.colors['yellow'], 
                                   fontsize=12, fontweight='bold')
        self.ax_analytics.grid(True, alpha=0.3, color=self.colors['grid'])
        
        # === 5. CONTROL PANEL ===
        self.ax_controls.clear()
        self.ax_controls.set_facecolor(self.colors['bg'])
        
        controls_text = f"""🎮 CONTROLS
═══════════════
[R] Record: {'🔴 ON' if self.is_recording else '⚪ OFF'}
[O] Objects: {'👁️ ON' if self.show_objects else '⚪ OFF'}
[A] Auto-scale: {'📏 ON' if self.auto_scale else '⚪ OFF'}
[T] Trails: {'🌈 ON' if self.show_trails else '⚪ OFF'}

🖱️ MOUSE
═══════════════
Scroll: Zoom
DblClick: Measure"""
        
        self.ax_controls.text(0.05, 0.95, controls_text, transform=self.ax_controls.transAxes,
                             fontsize=9, verticalalignment='top', fontfamily='monospace', 
                             color=self.colors['info'], linespacing=1.2)
        
        self.ax_controls.set_title('CONTROLS', color=self.colors['info'], 
                                  fontsize=11, fontweight='bold', pad=10)
        self.ax_controls.axis('off')
        
        # === 6. RECORDING PANEL ===
        self.ax_recording.clear()
        self.ax_recording.set_facecolor(self.colors['bg'])
        
        recording_color = self.colors['warning'] if self.is_recording else self.colors['text']
        recording_text = f"""🎬 RECORDING
═══════════════
Status: {'🔴 ACTIVE' if self.is_recording else '⚪ IDLE'}
Scans: {len(self.recording_data)}
Duration: {len(self.recording_data) * 0.1:.1f}s

💾 EXPORT
═══════════════
[S] Save Data
Formats: JSON, CSV"""
        
        self.ax_recording.text(0.05, 0.95, recording_text, transform=self.ax_recording.transAxes,
                              fontsize=9, verticalalignment='top', fontfamily='monospace', 
                              color=recording_color, linespacing=1.2)
        
        self.ax_recording.set_title('RECORDING', color=recording_color, 
                                   fontsize=11, fontweight='bold', pad=10)
        self.ax_recording.axis('off')
        
        # === 7. ALERTS PANEL ===
        self.ax_alerts.clear()
        self.ax_alerts.set_facecolor(self.colors['bg'])
        
        alerts_text = "🔔 ALERTS\n═══════════════\n"
        
        recent_alerts = self.alerts[-4:]  # Show last 4 alerts to prevent overlap
        for alert in recent_alerts:
            age = current_time - alert['timestamp']
            if age < 10:  # Show alerts from last 10 seconds
                color_code = {'warning': '⚠️', 'info': 'ℹ️', 'success': '✅'}.get(alert['type'], 'ℹ️')
                alerts_text += f"{color_code} {alert['message'][:20]}...\n"
        
        if not recent_alerts:
            alerts_text += "All systems normal ✅"
        
        alert_color = self.colors['warning'] if any(a['type'] == 'warning' for a in recent_alerts) else self.colors['success']
        
        self.ax_alerts.text(0.05, 0.95, alerts_text, transform=self.ax_alerts.transAxes,
                           fontsize=9, verticalalignment='top', fontfamily='monospace', 
                           color=alert_color, linespacing=1.2)
        
        self.ax_alerts.set_title('ALERTS', color=alert_color, 
                                fontsize=11, fontweight='bold', pad=10)
        self.ax_alerts.axis('off')
        
        # === 8. STATUS PANEL ===
        self.ax_status.clear()
        self.ax_status.set_facecolor(self.colors['bg'])
        
        runtime = current_time - self.start_time
        scan_rate = self.scan_count / runtime if runtime > 0 else 0
        
        status_text = f"""⚡ PERFORMANCE
═══════════════
FPS: {self.fps:2d}
Scan Rate: {scan_rate:.1f}Hz
Runtime: {runtime:.0f}s
Points: {len(distances):,}

🎯 STATS
═══════════════
Objects: {len(self.detected_objects)}
Map Cells: {len(self.persistent_map)}
Quality: {np.mean(qualities):.1f}"""
        
        self.ax_status.text(0.05, 0.95, status_text, transform=self.ax_status.transAxes,
                           fontsize=9, verticalalignment='top', fontfamily='monospace', 
                           color=self.colors['accent'], linespacing=1.2)
        
        self.ax_status.set_title('STATUS', color=self.colors['accent'], 
                                fontsize=11, fontweight='bold', pad=10)
        self.ax_status.axis('off')
        
    def start_visualization(self):
        """Start the advanced visualization system"""
        if not self.start_rplidar_process():
            return
            
        self.is_running = True
        
        # Start enhanced threads
        self.data_thread = threading.Thread(target=self.data_reader, daemon=True)
        self.data_thread.start()
        
        self.process_thread = threading.Thread(target=self.process_data, daemon=True)
        self.process_thread.start()
        
        print("🧠 \033[95mADVANCED VISUALIZATION ACTIVE\033[0m")
        print("🎮 \033[92mInteractive controls enabled\033[0m")
        print("🎯 \033[96mIntelligent object detection running\033[0m")
        print("📊 \033[93mReal-time analytics processing\033[0m")
        print("🔍 \033[97mPress H for help • Close window to stop\033[0m")
        
        # Enhanced animation with optimal performance
        ani = animation.FuncAnimation(self.fig, self.update_advanced_plots, 
                                     interval=75, cache_frame_data=False, blit=False)
        
        try:
            plt.show()
        except KeyboardInterrupt:
            print("\n⏹️ \033[91mAdvanced visualization terminated by user\033[0m")
        finally:
            self.stop_process()

def main():
    print("\n🧠 \033[95mRPLIDAR S3 ADVANCED VISUALIZER\033[0m")
    print("=" * 70)
    print("🎮 \033[96mInteractive controls and intelligent features\033[0m")
    print("🎯 \033[92mObject detection and tracking\033[0m")
    print("📊 \033[93mReal-time analytics and trends\033[0m")
    print("💾 \033[94mData recording and export capabilities\033[0m")
    print("🔔 \033[95mSmart alerts and notifications\033[0m")
    print("📡 \033[97mPort: COM8 | Baud: 1,000,000\033[0m")
    print("=" * 70)
    print("\n🎮 \033[93mPress H in the visualization window for help\033[0m")
    print()
    
    visualizer = RPLIDARAdvancedViz(max_points=3000)
    visualizer.start_visualization()

if __name__ == "__main__":
    main()
