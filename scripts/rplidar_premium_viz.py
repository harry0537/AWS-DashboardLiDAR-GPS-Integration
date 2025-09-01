#!/usr/bin/env python3
"""
RPLIDAR S3 Premium Visualizer - BEST TO DATE VERSION
Beautiful dark theme with vibrant colors and enhanced graphics
- Perfect screen proportions (14x9)
- Enlarged environment map
- 7-panel premium layout
- Real-time 32KHz processing
- Professional dark theme with vibrant colors
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Circle, FancyBboxPatch
import matplotlib.patches as mpatches
import subprocess
import threading
import time
import re
import sys
from collections import deque
import queue

class RPLIDARPremiumViz:
    def __init__(self, max_points=2000):
        self.max_points = max_points
        
        # High-speed data queue
        self.data_queue = queue.Queue(maxsize=5000)
        
        # Current scan data
        self.current_scan_angles = []
        self.current_scan_distances = []
        self.current_scan_qualities = []
        
        # Latest complete scan
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
        
        # UI Enhancement data
        self.time_data = deque(maxlen=200)
        self.min_range_data = deque(maxlen=200)
        self.max_range_data = deque(maxlen=200)
        self.avg_range_data = deque(maxlen=200)
        self.quality_history = deque(maxlen=100)
        
        # Setup premium UI
        self.setup_premium_ui()
        
    def setup_premium_ui(self):
        """Setup beautiful dark theme with vibrant colors"""
        # Set premium dark style
        plt.style.use('dark_background')
        
        # Custom color palette
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
            'text': '#ffffff'          # Pure white
        }
        
        # Create figure with optimized screen-proportionate size
        self.fig = plt.figure(figsize=(14, 9), facecolor=self.colors['bg'])
        self.fig.patch.set_facecolor(self.colors['bg'])
        
        # Main polar plot 
        self.ax_polar = plt.subplot2grid((3, 4), (0, 0), colspan=2, rowspan=2, projection='polar')
        self.ax_polar.set_facecolor(self.colors['bg'])
        
        # Environment map (XY) - BIGGER!
        self.ax_env = plt.subplot2grid((3, 4), (0, 2), colspan=2, rowspan=2)
        self.ax_env.set_facecolor(self.colors['bg'])
        
        # Range analysis - moved to bottom row
        self.ax_range = plt.subplot2grid((3, 4), (2, 2), colspan=2)
        self.ax_range.set_facecolor(self.colors['bg'])
        
        # Quality monitor
        self.ax_quality = plt.subplot2grid((3, 4), (2, 0))
        self.ax_quality.set_facecolor(self.colors['bg'])
        
        # Performance dashboard
        self.ax_perf = plt.subplot2grid((3, 4), (2, 1))
        self.ax_perf.set_facecolor(self.colors['bg'])
        
        # Environment analysis
        self.ax_analysis = plt.subplot2grid((3, 4), (2, 2))
        self.ax_analysis.set_facecolor(self.colors['bg'])
        
        # System status
        self.ax_status = plt.subplot2grid((3, 4), (2, 3))
        self.ax_status.set_facecolor(self.colors['bg'])
        
        # Configure layouts for better screen fit
        plt.subplots_adjust(left=0.06, right=0.97, top=0.91, bottom=0.08, 
                           wspace=0.3, hspace=0.45)
        
        # Premium title with adjusted size
        self.fig.suptitle('RPLIDAR S3 PREMIUM SCANNER • REAL-TIME ENVIRONMENT ANALYSIS', 
                         fontsize=16, color=self.colors['accent'], fontweight='bold')
        
    def start_rplidar_process(self):
        """Start RPLIDAR with premium initialization"""
        try:
            exe_path = "../rplidar_sdk_dev/output/win32/Release/ultra_simple.exe"
            cmd = [exe_path, "--channel", "--serial", "COM8", "1000000"]
            
            print(f"🚀 \033[92mInitializing RPLIDAR S3 Premium Scanner\033[0m")
            print(f"📡 Command: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=0
            )
            
            print("✅ \033[92mRPLIDAR S3 Premium Scanner Online!\033[0m")
            return True
            
        except Exception as e:
            print(f"❌ \033[91mFailed to initialize RPLIDAR: {e}\033[0m")
            return False
            
    def parse_line(self, line):
        """Optimized data parser"""
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
        """Premium data collection"""
        print("📡 \033[96mPremium data collection active...\033[0m")
        line_count = 0
        
        while self.is_running and self.process:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                
                line_count += 1
                
                # Debug: Print first few raw lines
                if line_count <= 5:
                    print(f"📄 Raw line {line_count}: {line.strip()}")
                    
                parsed = self.parse_line(line)
                if parsed:
                    try:
                        self.data_queue.put_nowait(parsed)
                        if line_count <= 10:  # Debug first few parsed results
                            print(f"✅ Parsed: {parsed}")
                    except queue.Full:
                        if line_count % 1000 == 0:  # Periodic queue full warning
                            print("⚠️ Data queue full, skipping points")
                        pass
                        
            except Exception as e:
                print(f"⚠️ \033[93mData error: {e}\033[0m")
                break
                
        print("📡 \033[96mData collection terminated\033[0m")
        
    def process_data(self):
        """Process data with premium quality"""
        print("🔧 Data processor thread started")
        while True:
            try:
                sync_flag, angle, distance, quality = self.data_queue.get(timeout=0.1)
                
                # Debug: Print first few data points
                if len(self.current_scan_angles) < 5:
                    print(f"📊 Data: θ={angle:.1f}° D={distance:.0f}mm Q={quality} S={sync_flag}")
                
                # Premium filtering (more lenient for testing)
                if 10 < distance < 15000:  # 1cm to 15m range
                    self.current_scan_angles.append(angle)
                    self.current_scan_distances.append(distance)
                    self.current_scan_qualities.append(quality)
                
                # Complete rotation detected (lower threshold for testing)
                if sync_flag and len(self.current_scan_angles) > 10:
                    print(f"✅ Complete scan: {len(self.current_scan_angles)} points")
                    
                    # Update complete scan
                    self.latest_scan_angles = np.array(self.current_scan_angles)
                    self.latest_scan_distances = np.array(self.current_scan_distances)
                    self.latest_scan_qualities = np.array(self.current_scan_qualities)
                    
                    # Add to quality history
                    if len(self.latest_scan_qualities) > 0:
                        self.quality_history.append(np.mean(self.latest_scan_qualities))
                    
                    # Reset
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
        """Premium shutdown"""
        self.is_running = False
        
        if self.data_thread:
            self.data_thread.join(timeout=2)
            
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print("🛑 \033[91mPremium RPLIDAR scanner offline\033[0m")
        
    def draw_range_circles(self, ax, max_range=6000):
        """Draw beautiful range circles"""
        ranges = [1000, 2000, 3000, 4000, 5000, 6000]
        colors = ['#ff00ff', '#00ffff', '#ffff00', '#ff8000', '#ff0080', '#8000ff']
        
        for i, (r, color) in enumerate(zip(ranges, colors)):
            if r <= max_range:
                circle = Circle((0, 0), r, fill=False, alpha=0.3, 
                               color=color, linewidth=1.5, linestyle='--')
                ax.add_patch(circle)
                
                # Range labels
                ax.text(r*0.7, r*0.7, f'{r//1000}m', 
                       color=color, fontweight='bold', fontsize=10)
        
    def update_premium_plots(self, frame):
        """Premium visualization update with stunning graphics"""
        # Update FPS counter
        self.fps_counter += 1
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            self.fps = self.fps_counter
            self.fps_counter = 0
            self.last_fps_time = current_time
        
        # Debug: Check data availability
        if len(self.latest_scan_distances) < 10:
            if frame % 20 == 0:  # Print every 20 frames (once per second)
                print(f"⏳ Waiting for data... Current points: {len(self.latest_scan_distances)}, Scans: {self.scan_count}")
            return
            
        angles = self.latest_scan_angles
        distances = self.latest_scan_distances
        qualities = self.latest_scan_qualities
        
        # === 1. PREMIUM POLAR PLOT ===
        self.ax_polar.clear()
        self.ax_polar.set_facecolor(self.colors['bg'])
        
        # Convert to radians
        angles_rad = np.radians(angles)
        
        # Multi-layer visualization
        # Layer 1: Background glow
        self.ax_polar.scatter(angles_rad, distances, c=distances, s=15, 
                             cmap='plasma', alpha=0.4, vmin=0, vmax=8000)
        
        # Layer 2: Main points with quality
        scatter = self.ax_polar.scatter(angles_rad, distances, c=qualities, s=25, 
                                       cmap='viridis', alpha=0.9, vmin=0, vmax=63,
                                       edgecolors='white', linewidths=0.3)
        
        # Premium polar styling
        self.ax_polar.set_title('360° ENVIRONMENT SCAN', 
                               color=self.colors['accent'], fontsize=14, fontweight='bold', pad=15)
        self.ax_polar.set_ylim(0, 8000)
        self.ax_polar.grid(True, alpha=0.4, color=self.colors['info'], linewidth=0.8)
        self.ax_polar.set_theta_zero_location('N')
        self.ax_polar.set_theta_direction(-1)
        self.ax_polar.set_facecolor(self.colors['bg'])
        
        # Custom radial labels
        self.ax_polar.set_ylim(0, 8000)
        self.ax_polar.set_yticks([2000, 4000, 6000, 8000])
        self.ax_polar.set_yticklabels(['2m', '4m', '6m', '8m'], color=self.colors['text'])
        
        # === 2. PREMIUM ENVIRONMENT MAP ===
        self.ax_env.clear()
        self.ax_env.set_facecolor(self.colors['bg'])
        
        # Convert to XY coordinates
        x = distances * np.sin(angles_rad)
        y = distances * np.cos(angles_rad)
        
        # Multi-layer XY plot
        # Background heatmap
        self.ax_env.scatter(x, y, c=distances, s=12, cmap='hot', alpha=0.6, vmin=0, vmax=8000)
        
        # Overlay with quality
        self.ax_env.scatter(x, y, c=qualities, s=8, cmap='cool', alpha=0.8, vmin=0, vmax=63)
        
        # Draw premium range circles
        self.draw_range_circles(self.ax_env, max_range=8000)
        
        # Styling
        self.ax_env.set_title('ENVIRONMENT MAP', color=self.colors['cyan'], 
                             fontsize=12, fontweight='bold')
        self.ax_env.set_xlabel('X Distance (mm)', color=self.colors['text'])
        self.ax_env.set_ylabel('Y Distance (mm)', color=self.colors['text'])
        self.ax_env.grid(True, alpha=0.3, color=self.colors['info'])
        self.ax_env.axis('equal')
        self.ax_env.set_xlim(-8000, 8000)
        self.ax_env.set_ylim(-8000, 8000)
        
        # Center crosshair
        self.ax_env.plot([-500, 500], [0, 0], color=self.colors['accent'], linewidth=3, alpha=0.8)
        self.ax_env.plot([0, 0], [-500, 500], color=self.colors['accent'], linewidth=3, alpha=0.8)
        
        # === 3. PREMIUM RANGE ANALYSIS ===
        self.ax_range.clear()
        self.ax_range.set_facecolor(self.colors['bg'])
        
        # Update time series data
        self.time_data.append(current_time - self.start_time)
        self.min_range_data.append(distances.min())
        self.max_range_data.append(distances.max())
        self.avg_range_data.append(distances.mean())
        
        if len(self.time_data) > 1:
            # Multiple range plots with different styles
            self.ax_range.plot(self.time_data, self.min_range_data, 
                              color=self.colors['cyan'], linewidth=2, label='Min Range', alpha=0.9)
            self.ax_range.plot(self.time_data, self.max_range_data, 
                              color=self.colors['orange'], linewidth=2, label='Max Range', alpha=0.9)
            self.ax_range.plot(self.time_data, self.avg_range_data, 
                              color=self.colors['accent'], linewidth=3, label='Avg Range', alpha=0.9)
            
            # Fill between for visual appeal
            self.ax_range.fill_between(self.time_data, self.min_range_data, self.max_range_data,
                                      alpha=0.2, color=self.colors['purple'])
        
        self.ax_range.set_title('RANGE ANALYSIS', color=self.colors['yellow'], 
                               fontsize=12, fontweight='bold')
        self.ax_range.set_xlabel('Time (s)', color=self.colors['text'])
        self.ax_range.set_ylabel('Distance (mm)', color=self.colors['text'])
        self.ax_range.grid(True, alpha=0.3, color=self.colors['info'])
        self.ax_range.legend(loc='upper right', facecolor=self.colors['panel'], 
                            edgecolor=self.colors['accent'])
        
        # === 4. QUALITY MONITOR ===
        self.ax_quality.clear()
        self.ax_quality.set_facecolor(self.colors['bg'])
        
        if len(self.quality_history) > 1:
            # Quality trend line
            quality_x = range(len(self.quality_history))
            self.ax_quality.plot(quality_x, self.quality_history, 
                               color=self.colors['success'], linewidth=3, alpha=0.9)
            self.ax_quality.fill_between(quality_x, self.quality_history, 
                                        alpha=0.3, color=self.colors['success'])
        
        # Current quality bar
        current_quality = qualities.mean() if len(qualities) > 0 else 0
        quality_bars = self.ax_quality.bar([0], [current_quality], 
                                          color=self.colors['warning'] if current_quality < 30 else self.colors['success'],
                                          alpha=0.8, width=0.5)
        
        self.ax_quality.set_title('SIGNAL QUALITY', color=self.colors['success'], 
                                 fontsize=12, fontweight='bold')
        self.ax_quality.set_ylim(0, 63)
        self.ax_quality.grid(True, alpha=0.3, color=self.colors['info'])
        self.ax_quality.set_ylabel('Quality', color=self.colors['text'])
        
        # === 5. PERFORMANCE DASHBOARD ===
        self.ax_perf.clear()
        self.ax_perf.set_facecolor(self.colors['bg'])
        
        runtime = current_time - self.start_time
        scan_rate = self.scan_count / runtime if runtime > 0 else 0
        
        perf_text = f"""
⚡ FPS: {self.fps:2d}
🔄 SCAN: {scan_rate:.1f}Hz
📊 POINTS: {len(distances):,}
⏱️ TIME: {runtime:.1f}s
🎯 SCANS: {self.scan_count:,}
        """
        
        self.ax_perf.text(0.1, 0.9, perf_text, transform=self.ax_perf.transAxes,
                         fontsize=11, verticalalignment='top', fontfamily='monospace', 
                         color=self.colors['accent'], fontweight='bold')
        
        self.ax_perf.set_title('PERFORMANCE', color=self.colors['info'], 
                              fontsize=12, fontweight='bold')
        self.ax_perf.axis('off')
        
        # === 6. ENVIRONMENT ANALYSIS ===
        self.ax_analysis.clear()
        self.ax_analysis.set_facecolor(self.colors['bg'])
        
        # Find closest and farthest objects
        closest_dist = distances.min()
        farthest_dist = distances.max()
        closest_angle = angles[np.argmin(distances)]
        farthest_angle = angles[np.argmax(distances)]
        
        analysis_text = f"""
📏 RANGE
  Min: {closest_dist:.0f}mm
  Max: {farthest_dist:.0f}mm
  Avg: {distances.mean():.0f}mm

🎯 OBJECTS
  Closest: {closest_angle:.0f}°
  Farthest: {farthest_angle:.0f}°
  
⭐ QUALITY: {qualities.mean():.1f}
        """
        
        self.ax_analysis.text(0.1, 0.9, analysis_text, transform=self.ax_analysis.transAxes,
                             fontsize=10, verticalalignment='top', fontfamily='monospace', 
                             color=self.colors['yellow'])
        
        self.ax_analysis.set_title('ANALYSIS', color=self.colors['orange'], 
                                  fontsize=12, fontweight='bold')
        self.ax_analysis.axis('off')
        
        # === 7. SYSTEM STATUS ===
        self.ax_status.clear()
        self.ax_status.set_facecolor(self.colors['bg'])
        
        status_color = self.colors['success'] if self.fps > 15 else self.colors['warning']
        connection_status = "ONLINE" if self.process and self.process.poll() is None else "OFFLINE"
        
        status_text = f"""
🔗 CONNECTION
  Status: {connection_status}
  Port: COM8
  Baud: 1M
  
🎮 SYSTEM
  Status: ACTIVE
  Mode: PREMIUM
  
🚀 RPLIDAR S3
  Model: S3M1-R2
  Ready: ✓
        """
        
        self.ax_status.text(0.1, 0.9, status_text, transform=self.ax_status.transAxes,
                           fontsize=10, verticalalignment='top', fontfamily='monospace', 
                           color=status_color)
        
        self.ax_status.set_title('STATUS', color=status_color, 
                                fontsize=12, fontweight='bold')
        self.ax_status.axis('off')
        
    def start_visualization(self):
        """Start premium visualization"""
        if not self.start_rplidar_process():
            return
            
        self.is_running = True
        
        # Start premium threads
        self.data_thread = threading.Thread(target=self.data_reader, daemon=True)
        self.data_thread.start()
        
        self.process_thread = threading.Thread(target=self.process_data, daemon=True)
        self.process_thread.start()
        
        print("🎨 \033[95mPREMIUM VISUALIZATION ACTIVE\033[0m")
        print("⚡ \033[92mUltra-fast 20 FPS updates\033[0m")
        print("🎯 \033[96mOptimized for RPLIDAR S3 32KHz\033[0m")
        print("🌈 \033[93mPremium dark theme with vibrant colors\033[0m")
        print("🔍 \033[97mClose window to stop\033[0m")
        
        # Premium animation with optimal speed
        ani = animation.FuncAnimation(self.fig, self.update_premium_plots, 
                                     interval=50, cache_frame_data=False, blit=False)
        
        try:
            plt.show()
        except KeyboardInterrupt:
            print("\n⏹️ \033[91mVisualization terminated by user\033[0m")
        finally:
            self.stop_process()

def main():
    print("\n🎨 \033[95mRPLIDAR S3 PREMIUM VISUALIZER - BEST TO DATE\033[0m")
    print("=" * 60)
    print("🌈 \033[96mBeautiful dark theme with vibrant colors\033[0m")
    print("⚡ \033[92mUltra-fast real-time visualization\033[0m")
    print("📡 \033[93mPort: COM8 | Baud: 1,000,000\033[0m")
    print("🎯 \033[97mPremium UI with enhanced graphics\033[0m")
    print("📏 \033[94mPerfect screen proportions (14x9)\033[0m")
    print("🗺️ \033[95mEnlarged environment map\033[0m")
    print("=" * 60)
    print()
    
    visualizer = RPLIDARPremiumViz(max_points=2000)
    visualizer.start_visualization()

if __name__ == "__main__":
    main()
