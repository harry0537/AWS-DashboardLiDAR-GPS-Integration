#!/usr/bin/env python3
"""
RPLIDAR S3 Visualizer - Pipe Version
Reads data from ultra_simple.exe output and creates real-time visualization
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

class RPLIDARVisualizerPipe:
    def __init__(self, max_points=1000):
        self.max_points = max_points
        
        # Data storage
        self.angles = deque(maxlen=max_points)
        self.distances = deque(maxlen=max_points)
        self.qualities = deque(maxlen=max_points)
        
        # Process and data handling
        self.process = None
        self.is_running = False
        self.data_thread = None
        
        # Statistics
        self.scan_count = 0
        self.total_points = 0
        self.start_time = time.time()
        
        # Setup plots
        self.setup_plots()
        
    def setup_plots(self):
        """Setup matplotlib plots"""
        self.fig = plt.figure(figsize=(16, 10))
        self.fig.suptitle('RPLIDAR S3 Real-Time Visualization', fontsize=16)
        
        # Large polar plot for main scan data
        self.ax_polar = self.fig.add_subplot(221, projection='polar')
        self.ax_polar.set_title('360° Live Scan Data', fontsize=14)
        self.ax_polar.set_ylim(0, 6000)  # 6 meters max for better view
        self.ax_polar.grid(True, alpha=0.3)
        self.ax_polar.set_theta_zero_location('N')  # 0° at top
        
        # Distance vs Angle (Cartesian)
        self.ax_cartesian = self.fig.add_subplot(222)
        self.ax_cartesian.set_title('Distance vs Angle (Cartesian)')
        self.ax_cartesian.set_xlabel('Angle (degrees)')
        self.ax_cartesian.set_ylabel('Distance (mm)')
        self.ax_cartesian.grid(True, alpha=0.3)
        
        # Distance histogram
        self.ax_hist = self.fig.add_subplot(223)
        self.ax_hist.set_title('Distance Distribution')
        self.ax_hist.set_xlabel('Distance (mm)')
        self.ax_hist.set_ylabel('Count')
        self.ax_hist.grid(True, alpha=0.3)
        
        # Statistics and environment map
        self.ax_stats = self.fig.add_subplot(224)
        self.ax_stats.set_title('Statistics & Object Detection')
        self.ax_stats.axis('off')
        
        plt.tight_layout()
        
    def start_rplidar_process(self):
        """Start the ultra_simple.exe process"""
        try:
            # Path to the built executable
            exe_path = "../rplidar_sdk_dev/output/win32/Release/ultra_simple.exe"
            cmd = [exe_path, "--channel", "--serial", "COM8", "1000000"]
            
            print(f"🚀 Starting RPLIDAR process: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            print("✅ RPLIDAR process started successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start RPLIDAR process: {e}")
            return False
            
    def parse_line(self, line):
        """Parse a line of RPLIDAR data"""
        # Pattern: "S  theta: 359.95 Dist: 02862.00 Q: 47" or "   theta: 200.00 Dist: 00054.00 Q: 47"
        pattern = r'([S\s]*)\s*theta:\s*([\d.]+)\s+Dist:\s*([\d.]+)(?:\s+Q:\s*(\d+))?'
        match = re.match(pattern, line.strip())
        
        if match:
            sync_flag = 'S' in match.group(1)
            angle = float(match.group(2))
            distance = float(match.group(3))
            quality = int(match.group(4)) if match.group(4) else 40  # Default quality
            
            return sync_flag, angle, distance, quality
        return None
        
    def data_reader(self):
        """Read data from RPLIDAR process in separate thread"""
        print("📡 Starting data collection from RPLIDAR...")
        
        while self.is_running and self.process:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                    
                parsed = self.parse_line(line)
                
                if parsed:
                    sync_flag, angle, distance, quality = parsed
                    
                    # Skip invalid readings
                    if distance > 0:
                        # Convert angle to radians for polar plot
                        angle_rad = np.radians(angle)
                        
                        self.angles.append(angle_rad)
                        self.distances.append(distance)
                        self.qualities.append(quality)
                        
                        self.total_points += 1
                        
                        if sync_flag:
                            self.scan_count += 1
                            
            except Exception as e:
                print(f"⚠️ Data reading error: {e}")
                break
                
        print("📡 Data collection stopped")
        
    def stop_process(self):
        """Stop the RPLIDAR process"""
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
        
    def analyze_environment(self, angles, distances):
        """Analyze the environment and detect objects"""
        if len(distances) < 10:
            return "Insufficient data"
            
        # Convert angles back to degrees for analysis
        angles_deg = np.degrees(angles)
        
        # Find objects by grouping nearby points
        objects = []
        current_object = []
        
        for i, (angle, dist) in enumerate(zip(angles_deg, distances)):
            if dist > 0:
                if not current_object or abs(dist - current_object[-1][1]) < 200:  # Within 20cm
                    current_object.append((angle, dist))
                else:
                    if len(current_object) > 5:  # At least 5 points to be an object
                        avg_angle = np.mean([p[0] for p in current_object])
                        avg_dist = np.mean([p[1] for p in current_object])
                        objects.append((avg_angle, avg_dist, len(current_object)))
                    current_object = [(angle, dist)]
        
        # Add the last object
        if len(current_object) > 5:
            avg_angle = np.mean([p[0] for p in current_object])
            avg_dist = np.mean([p[1] for p in current_object])
            objects.append((avg_angle, avg_dist, len(current_object)))
        
        return objects
        
    def update_plots(self, frame):
        """Update all plots with new data"""
        if len(self.distances) < 10:
            return
            
        # Convert to numpy arrays
        angles = np.array(list(self.angles))
        distances = np.array(list(self.distances))
        qualities = np.array(list(self.qualities))
        
        # Clear all plots
        self.ax_polar.clear()
        self.ax_cartesian.clear()
        self.ax_hist.clear()
        self.ax_stats.clear()
        
        # 1. Polar plot with color-coded quality
        scatter = self.ax_polar.scatter(angles, distances, c=qualities, s=8, 
                                       cmap='plasma', alpha=0.7, vmin=0, vmax=63)
        self.ax_polar.set_title('360° Live Scan Data (Color = Quality)', fontsize=14)
        self.ax_polar.set_ylim(0, 6000)
        self.ax_polar.grid(True, alpha=0.3)
        self.ax_polar.set_theta_zero_location('N')
        
        # Add colorbar for quality (fix for matplotlib issue)
        try:
            if hasattr(self, 'colorbar') and self.colorbar is not None:
                self.colorbar.remove()
        except:
            pass
        try:
            self.colorbar = plt.colorbar(scatter, ax=self.ax_polar, label='Quality', shrink=0.8)
        except:
            pass  # Skip colorbar if it fails
        
        # 2. Cartesian distance vs angle
        angles_deg = np.degrees(angles)
        self.ax_cartesian.scatter(angles_deg, distances, c=qualities, s=2, 
                                 cmap='plasma', alpha=0.6, vmin=0, vmax=63)
        self.ax_cartesian.set_title('Distance vs Angle (Cartesian)')
        self.ax_cartesian.set_xlabel('Angle (degrees)')
        self.ax_cartesian.set_ylabel('Distance (mm)')
        self.ax_cartesian.set_xlim(0, 360)
        self.ax_cartesian.grid(True, alpha=0.3)
        
        # 3. Distance histogram
        valid_distances = distances[distances > 0]
        if len(valid_distances) > 0:
            self.ax_hist.hist(valid_distances, bins=30, alpha=0.7, color='skyblue', 
                             edgecolor='black', linewidth=0.5)
            self.ax_hist.set_title('Distance Distribution')
            self.ax_hist.set_xlabel('Distance (mm)')
            self.ax_hist.set_ylabel('Count')
            self.ax_hist.grid(True, alpha=0.3)
        
        # 4. Statistics and object detection
        elapsed_time = time.time() - self.start_time
        scan_rate = self.scan_count / elapsed_time if elapsed_time > 0 else 0
        point_rate = self.total_points / elapsed_time if elapsed_time > 0 else 0
        
        # Analyze environment
        objects = self.analyze_environment(angles, distances)
        
        stats_text = f"""
🔍 RPLIDAR S3 Live Analysis
═══════════════════════════
⏱️ Runtime: {elapsed_time:.1f}s
🔄 Total Scans: {self.scan_count}
📊 Total Points: {self.total_points:,}
📈 Scan Rate: {scan_rate:.1f} Hz
📡 Point Rate: {point_rate:.0f} pts/sec
📏 Distance Range: {distances.min():.0f} - {distances.max():.0f} mm
⭐ Quality Range: {qualities.min()} - {qualities.max()}
📊 Active Points: {len(distances)}

🎯 Detected Objects: {len(objects) if isinstance(objects, list) else 0}"""

        if isinstance(objects, list) and objects:
            stats_text += "\n\n📍 Object Details:"
            for i, (angle, dist, points) in enumerate(objects[:5]):  # Show max 5 objects
                stats_text += f"\n   {i+1}. {angle:.0f}° - {dist:.0f}mm ({points} pts)"
        
        self.ax_stats.text(0.05, 0.95, stats_text, transform=self.ax_stats.transAxes,
                          fontsize=10, verticalalignment='top', fontfamily='monospace')
        self.ax_stats.set_title('Statistics & Object Detection')
        self.ax_stats.axis('off')
        
    def start_visualization(self):
        """Start the real-time visualization"""
        if not self.start_rplidar_process():
            return
            
        self.is_running = True
        
        # Start data reading thread
        self.data_thread = threading.Thread(target=self.data_reader, daemon=True)
        self.data_thread.start()
        
        # Start animation
        print("🎨 Starting real-time visualization...")
        print("💡 Close the plot window to stop")
        print("🔍 Your RPLIDAR S3 environment will appear in the polar plot!")
        
        ani = animation.FuncAnimation(self.fig, self.update_plots, 
                                     interval=200, cache_frame_data=False)
        
        try:
            plt.show()
        except KeyboardInterrupt:
            print("\n⏹️ Interrupted by user")
        finally:
            self.stop_process()

def main():
    print("🔍 RPLIDAR S3 Real-Time Visualizer")
    print("=================================")
    print("🎨 Creating live visualization from ultra_simple.exe")
    print("📡 Port: COM8 | Baud: 1,000,000")
    print()
    
    visualizer = RPLIDARVisualizerPipe(max_points=1500)
    visualizer.start_visualization()

if __name__ == "__main__":
    main()
