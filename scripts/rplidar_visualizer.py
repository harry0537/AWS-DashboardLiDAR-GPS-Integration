#!/usr/bin/env python3
"""
Real-time RPLIDAR S3 Visualizer
Creates live polar plot and statistics from RPLIDAR data
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import serial
import threading
import time
import argparse
from collections import deque
import re

class RPLIDARVisualizer:
    def __init__(self, com_port='COM8', baud_rate=1000000, max_points=2000):
        self.com_port = com_port
        self.baud_rate = baud_rate
        self.max_points = max_points
        
        # Data storage
        self.angles = deque(maxlen=max_points)
        self.distances = deque(maxlen=max_points)
        self.qualities = deque(maxlen=max_points)
        self.timestamps = deque(maxlen=max_points)
        
        # Serial connection
        self.serial_port = None
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
        self.fig = plt.figure(figsize=(15, 10))
        self.fig.suptitle('RPLIDAR S3 Real-Time Visualization', fontsize=16)
        
        # Polar plot for scan data
        self.ax_polar = self.fig.add_subplot(221, projection='polar')
        self.ax_polar.set_title('360° Scan Data')
        self.ax_polar.set_ylim(0, 8000)  # 8 meters max
        self.ax_polar.grid(True)
        
        # Distance histogram
        self.ax_hist = self.fig.add_subplot(222)
        self.ax_hist.set_title('Distance Distribution')
        self.ax_hist.set_xlabel('Distance (mm)')
        self.ax_hist.set_ylabel('Count')
        
        # Quality vs Distance
        self.ax_quality = self.fig.add_subplot(223)
        self.ax_quality.set_title('Quality vs Distance')
        self.ax_quality.set_xlabel('Distance (mm)')
        self.ax_quality.set_ylabel('Quality')
        
        # Statistics
        self.ax_stats = self.fig.add_subplot(224)
        self.ax_stats.set_title('Real-Time Statistics')
        self.ax_stats.axis('off')
        
        plt.tight_layout()
        
    def connect(self):
        """Connect to RPLIDAR"""
        try:
            print(f"🔌 Connecting to RPLIDAR S3 on {self.com_port}...")
            self.serial_port = serial.Serial(
                port=self.com_port,
                baudrate=self.baud_rate,
                timeout=1.0,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            print("✅ Connected successfully!")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from RPLIDAR"""
        self.is_running = False
        if self.data_thread:
            self.data_thread.join(timeout=2)
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            print("🔌 Disconnected from RPLIDAR")
            
    def parse_line(self, line):
        """Parse a line of RPLIDAR data"""
        # Pattern: "S  theta: 359.95 Dist: 02862.00" or "   theta: 200.00 Dist: 00054.00 Q: 47"
        pattern = r'([S\s]*)\s*theta:\s*([\d.]+)\s+Dist:\s*([\d.]+)(?:\s+Q:\s*(\d+))?'
        match = re.match(pattern, line.strip())
        
        if match:
            sync_flag = 'S' in match.group(1)
            angle = float(match.group(2))
            distance = float(match.group(3))
            quality = int(match.group(4)) if match.group(4) else 30  # Default quality
            
            return sync_flag, angle, distance, quality
        return None
        
    def data_reader(self):
        """Read data from RPLIDAR in separate thread"""
        print("📡 Starting data collection...")
        
        while self.is_running:
            try:
                if self.serial_port and self.serial_port.in_waiting:
                    line = self.serial_port.readline().decode('utf-8', errors='ignore')
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
                            self.timestamps.append(time.time())
                            
                            self.total_points += 1
                            
                            if sync_flag:
                                self.scan_count += 1
                                
            except Exception as e:
                print(f"⚠️ Data reading error: {e}")
                time.sleep(0.1)
                
        print("📡 Data collection stopped")
        
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
        self.ax_hist.clear()
        self.ax_quality.clear()
        self.ax_stats.clear()
        
        # 1. Polar plot
        self.ax_polar.scatter(angles, distances, c=qualities, s=1, cmap='viridis', alpha=0.6)
        self.ax_polar.set_title('360° Scan Data (Color = Quality)')
        self.ax_polar.set_ylim(0, 8000)
        self.ax_polar.grid(True)
        
        # 2. Distance histogram
        valid_distances = distances[distances > 0]
        if len(valid_distances) > 0:
            self.ax_hist.hist(valid_distances, bins=50, alpha=0.7, color='blue', edgecolor='black')
            self.ax_hist.set_title('Distance Distribution')
            self.ax_hist.set_xlabel('Distance (mm)')
            self.ax_hist.set_ylabel('Count')
            self.ax_hist.grid(True, alpha=0.3)
        
        # 3. Quality vs Distance
        self.ax_quality.scatter(distances, qualities, alpha=0.5, s=1, c='red')
        self.ax_quality.set_title('Quality vs Distance')
        self.ax_quality.set_xlabel('Distance (mm)')
        self.ax_quality.set_ylabel('Quality')
        self.ax_quality.grid(True, alpha=0.3)
        
        # 4. Statistics
        elapsed_time = time.time() - self.start_time
        scan_rate = self.scan_count / elapsed_time if elapsed_time > 0 else 0
        point_rate = self.total_points / elapsed_time if elapsed_time > 0 else 0
        
        stats_text = f"""
RPLIDAR S3 Statistics
═══════════════════════
⏱️ Runtime: {elapsed_time:.1f}s
🔄 Total Scans: {self.scan_count}
📊 Total Points: {self.total_points}
📈 Scan Rate: {scan_rate:.1f} Hz
📡 Point Rate: {point_rate:.0f} pts/sec
📏 Distance Range: {distances.min():.0f} - {distances.max():.0f} mm
⭐ Quality Range: {qualities.min()} - {qualities.max()}
📊 Active Points: {len(distances)}
        """
        
        self.ax_stats.text(0.1, 0.9, stats_text, transform=self.ax_stats.transAxes,
                          fontsize=10, verticalalignment='top', fontfamily='monospace')
        self.ax_stats.set_title('Real-Time Statistics')
        self.ax_stats.axis('off')
        
    def start_visualization(self):
        """Start the real-time visualization"""
        if not self.connect():
            return
            
        self.is_running = True
        
        # Start data reading thread
        self.data_thread = threading.Thread(target=self.data_reader, daemon=True)
        self.data_thread.start()
        
        # Start animation
        print("🎨 Starting visualization...")
        print("💡 Close the plot window to stop")
        
        ani = animation.FuncAnimation(self.fig, self.update_plots, 
                                     interval=100, cache_frame_data=False)
        
        try:
            plt.show()
        except KeyboardInterrupt:
            print("\n⏹️ Interrupted by user")
        finally:
            self.disconnect()

def main():
    parser = argparse.ArgumentParser(description='RPLIDAR S3 Real-Time Visualizer')
    parser.add_argument('--port', default='COM8', help='COM port (default: COM8)')
    parser.add_argument('--baud', type=int, default=1000000, help='Baud rate (default: 1000000)')
    parser.add_argument('--points', type=int, default=2000, help='Max points to display (default: 2000)')
    
    args = parser.parse_args()
    
    print("🔍 RPLIDAR S3 Real-Time Visualizer")
    print("=================================")
    print(f"Port: {args.port}")
    print(f"Baud: {args.baud}")
    print(f"Max Points: {args.points}")
    print()
    
    visualizer = RPLIDARVisualizer(args.port, args.baud, args.points)
    visualizer.start_visualization()

if __name__ == "__main__":
    main()
