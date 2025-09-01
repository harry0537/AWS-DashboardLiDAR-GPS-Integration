#!/usr/bin/env python3
"""
RPLIDAR S3 3D Visualizer
Creates 3D point clouds by stacking 2D scans over time
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.animation as animation
import subprocess
import threading
import time
import re
import sys
from collections import deque
import queue

class RPLIDAR3DViz:
    def __init__(self, max_scans=50, points_per_scan=1000):
        self.max_scans = max_scans
        self.points_per_scan = points_per_scan
        
        # 3D point cloud storage
        self.point_cloud_x = deque(maxlen=max_scans * points_per_scan)
        self.point_cloud_y = deque(maxlen=max_scans * points_per_scan)
        self.point_cloud_z = deque(maxlen=max_scans * points_per_scan)
        self.point_cloud_colors = deque(maxlen=max_scans * points_per_scan)
        
        # Current scan data
        self.current_scan_angles = []
        self.current_scan_distances = []
        self.current_scan_qualities = []
        
        # Z-height management (time-based layers)
        self.current_z_height = 0
        self.z_increment = 50  # mm between scan layers
        
        # Data queue for high-speed processing
        self.data_queue = queue.Queue(maxsize=3000)
        
        # Process handling
        self.process = None
        self.is_running = False
        self.data_thread = None
        self.scan_thread = None
        
        # Performance tracking
        self.scan_count = 0
        self.start_time = time.time()
        self.fps = 0
        self.fps_counter = 0
        self.last_fps_time = time.time()
        
        # 3D view parameters
        self.view_elevation = 20
        self.view_azimuth = 45
        self.auto_rotate = True
        
        # Setup 3D visualization
        self.setup_3d_plots()
        
    def setup_3d_plots(self):
        """Setup 3D matplotlib visualization"""
        plt.style.use('dark_background')
        
        self.fig = plt.figure(figsize=(18, 12))
        
        # Main 3D plot
        self.ax_3d = self.fig.add_subplot(221, projection='3d')
        self.ax_3d.set_facecolor('black')
        self.ax_3d.set_title('RPLIDAR S3 - 3D Point Cloud (Time Stacked)', 
                            color='white', fontsize=16)
        
        # Top-down view (XY plane)
        self.ax_top = self.fig.add_subplot(222)
        self.ax_top.set_facecolor('black')
        self.ax_top.set_title('Top-Down View (Latest Scan)', color='white', fontsize=14)
        self.ax_top.set_xlabel('X (mm)', color='white')
        self.ax_top.set_ylabel('Y (mm)', color='white')
        self.ax_top.grid(True, alpha=0.3, color='gray')
        self.ax_top.axis('equal')
        
        # Side view (XZ plane)
        self.ax_side = self.fig.add_subplot(223)
        self.ax_side.set_facecolor('black')
        self.ax_side.set_title('Side View (XZ Plane)', color='white', fontsize=14)
        self.ax_side.set_xlabel('X (mm)', color='white')
        self.ax_side.set_ylabel('Z (Time Layer)', color='white')
        self.ax_side.grid(True, alpha=0.3, color='gray')
        
        # Stats and controls
        self.ax_stats = self.fig.add_subplot(224)
        self.ax_stats.set_facecolor('black')
        self.ax_stats.set_title('3D Visualization Controls', color='white', fontsize=14)
        self.ax_stats.axis('off')
        
        plt.tight_layout()
        self.fig.suptitle('RPLIDAR S3 3D Environment Scanner', 
                         color='white', fontsize=18)
        
    def start_rplidar_process(self):
        """Start the RPLIDAR S3 process"""
        try:
            exe_path = "../rplidar_sdk_dev/output/win32/Release/ultra_simple.exe"
            cmd = [exe_path, "--channel", "--serial", "COM8", "1000000"]
            
            print(f"🚀 Starting RPLIDAR S3 for 3D scanning: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=0
            )
            
            print("✅ RPLIDAR S3 connected for 3D visualization!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start RPLIDAR: {e}")
            return False
            
    def parse_line(self, line):
        """Parse RPLIDAR data line"""
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
                    
                    return sync_flag, angle, distance, quality
            except (ValueError, IndexError):
                pass
                
        return None
        
    def data_reader(self):
        """High-speed data collection"""
        print("📡 Starting 3D data collection...")
        
        while self.is_running and self.process:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                    
                parsed = self.parse_line(line)
                if parsed:
                    try:
                        self.data_queue.put_nowait(parsed)
                    except queue.Full:
                        pass  # Skip if queue full
                        
            except Exception as e:
                print(f"⚠️ Data error: {e}")
                break
                
        print("📡 3D data collection stopped")
        
    def scan_processor(self):
        """Process scans and build 3D point cloud"""
        while self.is_running:
            try:
                sync_flag, angle, distance, quality = self.data_queue.get(timeout=0.1)
                
                # Filter valid points
                if distance > 100 and distance < 10000:  # 10cm to 10m
                    self.current_scan_angles.append(angle)
                    self.current_scan_distances.append(distance)
                    self.current_scan_qualities.append(quality)
                
                # Complete scan detected
                if sync_flag and len(self.current_scan_angles) > 50:
                    self.add_scan_to_3d_cloud()
                    
                    # Reset for next scan
                    self.current_scan_angles = []
                    self.current_scan_distances = []
                    self.current_scan_qualities = []
                    
                    self.scan_count += 1
                    self.current_z_height += self.z_increment
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"⚠️ Scan processing error: {e}")
                break
                
    def add_scan_to_3d_cloud(self):
        """Add current scan to 3D point cloud"""
        angles = np.array(self.current_scan_angles)
        distances = np.array(self.current_scan_distances)
        qualities = np.array(self.current_scan_qualities)
        
        # Convert to cartesian coordinates
        angles_rad = np.radians(angles)
        x = distances * np.sin(angles_rad)
        y = distances * np.cos(angles_rad)
        z = np.full_like(x, self.current_z_height)
        
        # Color by quality and distance
        colors = qualities / 63.0  # Normalize quality to 0-1
        
        # Add to point cloud
        for i in range(len(x)):
            self.point_cloud_x.append(x[i])
            self.point_cloud_y.append(y[i])
            self.point_cloud_z.append(z[i])
            self.point_cloud_colors.append(colors[i])
            
    def stop_process(self):
        """Clean shutdown"""
        self.is_running = False
        
        if self.data_thread:
            self.data_thread.join(timeout=2)
        if self.scan_thread:
            self.scan_thread.join(timeout=2)
            
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print("🛑 3D RPLIDAR process stopped")
        
    def update_3d_plots(self, frame):
        """Update 3D visualization"""
        # Update FPS
        self.fps_counter += 1
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            self.fps = self.fps_counter
            self.fps_counter = 0
            self.last_fps_time = current_time
        
        # Skip if no data
        if len(self.point_cloud_x) < 100:
            return
            
        # Convert to numpy arrays
        x = np.array(list(self.point_cloud_x))
        y = np.array(list(self.point_cloud_y))
        z = np.array(list(self.point_cloud_z))
        colors = np.array(list(self.point_cloud_colors))
        
        # 1. MAIN 3D PLOT
        self.ax_3d.clear()
        self.ax_3d.set_facecolor('black')
        
        # Create 3D scatter plot with color gradient
        scatter = self.ax_3d.scatter(x, y, z, c=colors, s=8, 
                                    cmap='plasma', alpha=0.6, vmin=0, vmax=1)
        
        self.ax_3d.set_title('RPLIDAR S3 - 3D Point Cloud (Time Stacked)', 
                            color='white', fontsize=16)
        self.ax_3d.set_xlabel('X (mm)', color='white')
        self.ax_3d.set_ylabel('Y (mm)', color='white')
        self.ax_3d.set_zlabel('Z (Time Layer)', color='white')
        
        # Set limits
        max_range = 5000
        self.ax_3d.set_xlim([-max_range, max_range])
        self.ax_3d.set_ylim([-max_range, max_range])
        self.ax_3d.set_zlim([0, self.current_z_height + 100])
        
        # Auto-rotate view
        if self.auto_rotate:
            self.view_azimuth += 0.5
            if self.view_azimuth >= 360:
                self.view_azimuth = 0
                
        self.ax_3d.view_init(elev=self.view_elevation, azim=self.view_azimuth)
        
        # Grid and styling
        self.ax_3d.grid(True, alpha=0.3)
        
        # 2. TOP-DOWN VIEW (Latest scan)
        self.ax_top.clear()
        self.ax_top.set_facecolor('black')
        
        # Show only the latest layer
        if len(z) > 0:
            latest_z = z.max()
            latest_mask = z >= (latest_z - self.z_increment/2)
            
            if np.any(latest_mask):
                self.ax_top.scatter(x[latest_mask], y[latest_mask], 
                                   c=colors[latest_mask], s=12, 
                                   cmap='plasma', alpha=0.8)
        
        self.ax_top.set_title('Top-Down View (Latest Scan)', color='white', fontsize=14)
        self.ax_top.set_xlabel('X (mm)', color='white')
        self.ax_top.set_ylabel('Y (mm)', color='white')
        self.ax_top.grid(True, alpha=0.3, color='gray')
        self.ax_top.axis('equal')
        self.ax_top.set_xlim([-5000, 5000])
        self.ax_top.set_ylim([-5000, 5000])
        
        # Add range circles
        for r in [1000, 2000, 3000, 4000, 5000]:
            circle = plt.Circle((0, 0), r, fill=False, alpha=0.2, color='cyan')
            self.ax_top.add_patch(circle)
        
        # 3. SIDE VIEW (XZ)
        self.ax_side.clear()
        self.ax_side.set_facecolor('black')
        
        # Show side profile
        self.ax_side.scatter(x, z, c=colors, s=6, cmap='plasma', alpha=0.7)
        self.ax_side.set_title('Side View (XZ Plane)', color='white', fontsize=14)
        self.ax_side.set_xlabel('X (mm)', color='white')
        self.ax_side.set_ylabel('Z (Time Layer)', color='white')
        self.ax_side.grid(True, alpha=0.3, color='gray')
        self.ax_side.set_xlim([-5000, 5000])
        self.ax_side.set_ylim([0, self.current_z_height + 100])
        
        # 4. STATS AND CONTROLS
        self.ax_stats.clear()
        self.ax_stats.set_facecolor('black')
        
        runtime = current_time - self.start_time
        point_count = len(x)
        scan_rate = self.scan_count / runtime if runtime > 0 else 0
        
        stats_text = f"""
🎮 3D RPLIDAR S3 SCANNER
═══════════════════════════════════
⚡ Visualization FPS: {self.fps:2d}
🔄 Scan Rate: {scan_rate:.1f} Hz
🎯 Total Scans: {self.scan_count:,}
📊 3D Points: {point_count:,}
📏 Z Layers: {int(self.current_z_height/self.z_increment)}
⏱️ Runtime: {runtime:.1f}s

🎨 3D VIEW CONTROLS
═══════════════════════════════════
📐 Elevation: {self.view_elevation:.0f}°
🔄 Azimuth: {self.view_azimuth:.0f}°
🔄 Auto-Rotate: {'ON' if self.auto_rotate else 'OFF'}
📏 Z Increment: {self.z_increment}mm

🌍 ENVIRONMENT STATUS
═══════════════════════════════════
📊 Point Density: {point_count/(self.scan_count or 1):.0f} pts/scan
🎯 Coverage: 360° × {int(self.current_z_height/self.z_increment)} layers
🚀 Building 3D world in real-time!

💡 TIPS:
• Each scan adds a new Z layer
• Colors represent point quality
• Auto-rotation shows all angles
• Time creates the 3rd dimension!
        """
        
        self.ax_stats.text(0.05, 0.95, stats_text, transform=self.ax_stats.transAxes,
                          fontsize=10, verticalalignment='top', 
                          fontfamily='monospace', color='lime')
        self.ax_stats.set_title('3D Visualization Controls', color='white', fontsize=14)
        self.ax_stats.axis('off')
        
    def start_visualization(self):
        """Start 3D visualization"""
        if not self.start_rplidar_process():
            return
            
        self.is_running = True
        
        # Start threads
        self.data_thread = threading.Thread(target=self.data_reader, daemon=True)
        self.data_thread.start()
        
        self.scan_thread = threading.Thread(target=self.scan_processor, daemon=True)
        self.scan_thread.start()
        
        print("🎨 Starting 3D REAL-TIME visualization...")
        print("🌍 Building 3D point cloud from time-stacked scans")
        print("🔄 Auto-rotating view for full perspective")
        print("🔍 Close window to stop")
        
        # Animation with 3D updates
        ani = animation.FuncAnimation(self.fig, self.update_3d_plots, 
                                     interval=100, cache_frame_data=False)
        
        try:
            plt.show()
        except KeyboardInterrupt:
            print("\n⏹️ Interrupted by user")
        finally:
            self.stop_process()

def main():
    print("🌍 RPLIDAR S3 3D VISUALIZATION")
    print("===============================")
    print("🎮 Creating 3D point clouds from 2D scans")
    print("📡 Port: COM8 | Baud: 1,000,000")
    print("🔄 Time-stacked layers for 3D effect")
    print("🎨 Auto-rotating view with multiple perspectives")
    print()
    
    visualizer = RPLIDAR3DViz(max_scans=100, points_per_scan=500)
    visualizer.start_visualization()

if __name__ == "__main__":
    main()
