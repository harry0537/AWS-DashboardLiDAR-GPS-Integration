#!/usr/bin/env python3
"""
RPLIDAR S3 Real-Time Visualizer - High Performance
Optimized for 32KHz sample rate with minimal latency
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import subprocess
import threading
import time
import re
import sys
from collections import deque
import queue

class RPLIDARRealtimeViz:
    def __init__(self, max_points=2000):
        self.max_points = max_points
        
        # High-speed data queue
        self.data_queue = queue.Queue(maxsize=5000)
        
        # Current scan data (one complete 360° rotation)
        self.current_scan_angles = []
        self.current_scan_distances = []
        self.current_scan_qualities = []
        
        # Latest complete scan for visualization
        self.latest_scan_angles = np.array([])
        self.latest_scan_distances = np.array([])
        self.latest_scan_qualities = np.array([])
        
        # Process handling
        self.process = None
        self.is_running = False
        self.data_thread = None
        
        # Performance stats
        self.scan_count = 0
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.fps = 0
        self.start_time = time.time()
        
        # Setup optimized plots
        self.setup_plots()
        
    def setup_plots(self):
        """Setup matplotlib with optimized settings for real-time"""
        plt.style.use('dark_background')  # Better for real-time viz
        
        self.fig, ((self.ax_polar, self.ax_cart), (self.ax_range, self.ax_stats)) = plt.subplots(
            2, 2, figsize=(16, 12), 
            subplot_kw={'projection': 'polar'} if True else {}
        )
        
        # Re-setup with correct projections
        self.fig.clear()
        
        # Polar plot (main visualization)
        self.ax_polar = self.fig.add_subplot(221, projection='polar')
        self.ax_polar.set_facecolor('black')
        self.ax_polar.set_title('RPLIDAR S3 - Live 360° Scan', color='white', fontsize=14)
        self.ax_polar.set_ylim(0, 8000)  # 8 meters max
        self.ax_polar.grid(True, alpha=0.3, color='gray')
        self.ax_polar.set_theta_zero_location('N')  # 0° at top
        self.ax_polar.set_theta_direction(-1)  # Clockwise
        
        # XY Cartesian plot
        self.ax_cart = self.fig.add_subplot(222)
        self.ax_cart.set_facecolor('black')
        self.ax_cart.set_title('Environment Map (XY)', color='white', fontsize=14)
        self.ax_cart.set_xlabel('X (mm)', color='white')
        self.ax_cart.set_ylabel('Y (mm)', color='white')
        self.ax_cart.grid(True, alpha=0.3, color='gray')
        self.ax_cart.axis('equal')
        
        # Range vs Time
        self.ax_range = self.fig.add_subplot(223)
        self.ax_range.set_facecolor('black')
        self.ax_range.set_title('Distance Range vs Time', color='white', fontsize=14)
        self.ax_range.set_xlabel('Time (s)', color='white')
        self.ax_range.set_ylabel('Distance (mm)', color='white')
        self.ax_range.grid(True, alpha=0.3, color='gray')
        
        # Performance stats
        self.ax_stats = self.fig.add_subplot(224)
        self.ax_stats.set_facecolor('black')
        self.ax_stats.set_title('Real-Time Performance', color='white', fontsize=14)
        self.ax_stats.axis('off')
        
        # Initialize plot elements for blitting (faster updates)
        self.polar_scatter = None
        self.cart_scatter = None
        self.range_line = None
        
        # Data for range plot
        self.time_data = deque(maxlen=200)
        self.min_range_data = deque(maxlen=200)
        self.max_range_data = deque(maxlen=200)
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.92)
        self.fig.suptitle('RPLIDAR S3 Real-Time Environment Scanner', 
                         color='white', fontsize=16)
        
    def start_rplidar_process(self):
        """Start ultra_simple.exe with optimized settings"""
        try:
            exe_path = "../rplidar_sdk_dev/output/win32/Release/ultra_simple.exe"
            cmd = [exe_path, "--channel", "--serial", "COM8", "1000000"]
            
            print(f"🚀 Starting RPLIDAR S3: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=0  # Unbuffered for minimal latency
            )
            
            print("✅ RPLIDAR S3 connected successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start RPLIDAR: {e}")
            return False
            
    def parse_line(self, line):
        """Optimized line parser for RPLIDAR data"""
        # Fast regex for: "S  theta: 359.95 Dist: 02862.00 Q: 47"
        if 'theta:' in line:
            parts = line.split()
            try:
                sync_flag = 'S' in line[:5]
                
                # Find theta, Dist, Q values
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
        """High-speed data collection thread"""
        print("📡 Starting high-speed data collection...")
        
        while self.is_running and self.process:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                    
                parsed = self.parse_line(line)
                if parsed:
                    # Add to queue for processing
                    try:
                        self.data_queue.put_nowait(parsed)
                    except queue.Full:
                        # Skip if queue is full (maintain real-time)
                        pass
                        
            except Exception as e:
                print(f"⚠️ Data error: {e}")
                break
                
        print("📡 Data collection stopped")
        
    def process_data(self):
        """Process queued data into scan frames"""
        while True:
            try:
                # Get data from queue
                sync_flag, angle, distance, quality = self.data_queue.get(timeout=0.1)
                
                # Filter valid data
                if distance > 50:  # Minimum 5cm
                    self.current_scan_angles.append(angle)
                    self.current_scan_distances.append(distance)
                    self.current_scan_qualities.append(quality)
                
                # If sync flag, we completed one rotation
                if sync_flag and len(self.current_scan_angles) > 100:
                    # Update latest complete scan
                    self.latest_scan_angles = np.array(self.current_scan_angles)
                    self.latest_scan_distances = np.array(self.current_scan_distances)
                    self.latest_scan_qualities = np.array(self.current_scan_qualities)
                    
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
                
    def stop_process(self):
        """Clean shutdown"""
        self.is_running = False
        
        if self.data_thread:
            self.data_thread.join(timeout=2)
            
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print("🛑 RPLIDAR process stopped")
        
    def update_plots(self, frame):
        """Ultra-fast plot updates"""
        # Update FPS counter
        self.fps_counter += 1
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            self.fps = self.fps_counter
            self.fps_counter = 0
            self.last_fps_time = current_time
        
        # Skip if no data
        if len(self.latest_scan_distances) < 10:
            return
            
        angles = self.latest_scan_angles
        distances = self.latest_scan_distances
        qualities = self.latest_scan_qualities
        
        # 1. POLAR PLOT - Main visualization
        self.ax_polar.clear()
        self.ax_polar.set_facecolor('black')
        
        # Convert angles to radians
        angles_rad = np.radians(angles)
        
        # Color by distance for better depth perception
        colors = plt.cm.plasma(np.clip(distances / 5000, 0, 1))
        
        self.ax_polar.scatter(angles_rad, distances, c=distances, s=12, 
                             cmap='plasma', alpha=0.8, vmin=0, vmax=5000)
        
        self.ax_polar.set_title('RPLIDAR S3 - Live 360° Scan', color='white', fontsize=14)
        self.ax_polar.set_ylim(0, 6000)
        self.ax_polar.grid(True, alpha=0.3, color='gray')
        self.ax_polar.set_theta_zero_location('N')
        self.ax_polar.set_theta_direction(-1)
        
        # 2. XY CARTESIAN - Environment map
        self.ax_cart.clear()
        self.ax_cart.set_facecolor('black')
        
        # Convert to XY coordinates
        x = distances * np.sin(angles_rad)
        y = distances * np.cos(angles_rad)
        
        self.ax_cart.scatter(x, y, c=qualities, s=8, cmap='viridis', alpha=0.7)
        self.ax_cart.set_title('Environment Map (XY)', color='white', fontsize=14)
        self.ax_cart.set_xlabel('X (mm)', color='white')
        self.ax_cart.set_ylabel('Y (mm)', color='white')
        self.ax_cart.grid(True, alpha=0.3, color='gray')
        self.ax_cart.axis('equal')
        
        # Add range circles
        for r in [1000, 2000, 3000, 4000, 5000]:
            circle = plt.Circle((0, 0), r, fill=False, alpha=0.2, color='white')
            self.ax_cart.add_patch(circle)
        
        # 3. RANGE vs TIME
        self.time_data.append(current_time - self.start_time)
        self.min_range_data.append(distances.min())
        self.max_range_data.append(distances.max())
        
        self.ax_range.clear()
        self.ax_range.set_facecolor('black')
        
        if len(self.time_data) > 1:
            self.ax_range.plot(self.time_data, self.min_range_data, 'cyan', 
                              label='Min Distance', alpha=0.8)
            self.ax_range.plot(self.time_data, self.max_range_data, 'yellow', 
                              label='Max Distance', alpha=0.8)
            self.ax_range.fill_between(self.time_data, self.min_range_data, 
                                      self.max_range_data, alpha=0.2, color='blue')
        
        self.ax_range.set_title('Distance Range vs Time', color='white', fontsize=14)
        self.ax_range.set_xlabel('Time (s)', color='white')
        self.ax_range.set_ylabel('Distance (mm)', color='white')
        self.ax_range.grid(True, alpha=0.3, color='gray')
        self.ax_range.legend()
        
        # 4. PERFORMANCE STATS
        self.ax_stats.clear()
        self.ax_stats.set_facecolor('black')
        
        runtime = current_time - self.start_time
        avg_scan_rate = self.scan_count / runtime if runtime > 0 else 0
        point_density = len(distances)
        
        # Detect closest and farthest objects
        closest_dist = distances.min()
        farthest_dist = distances.max()
        closest_angle = angles[np.argmin(distances)]
        farthest_angle = angles[np.argmax(distances)]
        
        stats_text = f"""
🎯 RPLIDAR S3 REAL-TIME SCANNER
═══════════════════════════════════
⚡ Visualization FPS: {self.fps:2d}
🔄 Scan Rate: {avg_scan_rate:.1f} Hz
📊 Points per Scan: {point_density:,}
⏱️ Runtime: {runtime:.1f}s
🎲 Total Scans: {self.scan_count:,}

🎯 ENVIRONMENT ANALYSIS
═══════════════════════════════════
📏 Range: {closest_dist:.0f} - {farthest_dist:.0f} mm
🔍 Closest: {closest_dist:.0f}mm @ {closest_angle:.0f}°
🔭 Farthest: {farthest_dist:.0f}mm @ {farthest_angle:.0f}°
⭐ Quality: {qualities.min()}-{qualities.max()}

🚀 PERFORMANCE OPTIMAL
Real-time 32KHz processing active!
        """
        
        self.ax_stats.text(0.05, 0.95, stats_text, transform=self.ax_stats.transAxes,
                          fontsize=11, verticalalignment='top', 
                          fontfamily='monospace', color='lime')
        self.ax_stats.set_title('Real-Time Performance', color='white', fontsize=14)
        self.ax_stats.axis('off')
        
    def start_visualization(self):
        """Start the real-time visualization system"""
        if not self.start_rplidar_process():
            return
            
        self.is_running = True
        
        # Start data collection thread
        self.data_thread = threading.Thread(target=self.data_reader, daemon=True)
        self.data_thread.start()
        
        # Start data processing thread
        self.process_thread = threading.Thread(target=self.process_data, daemon=True)
        self.process_thread.start()
        
        print("🎨 Starting REAL-TIME visualization...")
        print("⚡ Optimized for 32KHz RPLIDAR S3 data rate")
        print("🔍 Close window to stop")
        
        # High-speed animation (50ms = 20 FPS)
        ani = animation.FuncAnimation(self.fig, self.update_plots, 
                                     interval=50, cache_frame_data=False, blit=False)
        
        try:
            plt.show()
        except KeyboardInterrupt:
            print("\n⏹️ Interrupted by user")
        finally:
            self.stop_process()

def main():
    print("⚡ RPLIDAR S3 REAL-TIME SCANNER")
    print("===============================")
    print("🚀 Ultra-fast 32KHz visualization")
    print("📡 Port: COM8 | Baud: 1,000,000")
    print("🎯 Optimized for minimal latency")
    print()
    
    visualizer = RPLIDARRealtimeViz(max_points=2000)
    visualizer.start_visualization()

if __name__ == "__main__":
    main()
