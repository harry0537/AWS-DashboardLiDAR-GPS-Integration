#!/usr/bin/env python3
"""
RPLIDAR S3 Interactive 3D Visualizer
Advanced 3D visualization with keyboard controls and different modes
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.animation as animation
from matplotlib.widgets import Button, Slider
import subprocess
import threading
import time
import re
import sys
from collections import deque
import queue

class RPLIDAR3DInteractive:
    def __init__(self, max_scans=80):
        self.max_scans = max_scans
        
        # 3D visualization modes
        self.viz_modes = ['point_cloud', 'surface', 'wireframe', 'voxel']
        self.current_mode = 0
        
        # 3D point storage with timestamps
        self.scans_3d = deque(maxlen=max_scans)  # Each element: (x, y, z, colors, timestamp)
        
        # Current scan building
        self.current_scan_angles = []
        self.current_scan_distances = []
        self.current_scan_qualities = []
        
        # Z-layer management
        self.z_height = 0
        self.z_increment = 30  # mm between layers
        
        # Data processing
        self.data_queue = queue.Queue(maxsize=2000)
        self.process = None
        self.is_running = False
        self.threads = []
        
        # Visualization parameters
        self.view_elevation = 30
        self.view_azimuth = 45
        self.auto_rotate = True
        self.rotate_speed = 1.0
        self.show_trails = True
        self.point_size = 8
        self.alpha = 0.7
        
        # Performance
        self.scan_count = 0
        self.start_time = time.time()
        self.fps = 0
        self.fps_counter = 0
        self.last_fps_time = time.time()
        
        # Setup interactive 3D interface
        self.setup_interactive_3d()
        
    def setup_interactive_3d(self):
        """Setup advanced 3D interface with controls"""
        plt.style.use('dark_background')
        
        # Create figure with space for controls
        self.fig = plt.figure(figsize=(20, 14))
        
        # Main 3D plot (larger)
        self.ax_3d = self.fig.add_subplot(2, 3, (1, 4), projection='3d')
        self.ax_3d.set_facecolor('black')
        self.ax_3d.set_title('RPLIDAR S3 - Interactive 3D Environment', 
                            color='white', fontsize=18)
        
        # Control panels
        self.ax_controls = self.fig.add_subplot(2, 3, 2)
        self.ax_controls.set_facecolor('black')
        self.ax_controls.set_title('Interactive Controls', color='white', fontsize=14)
        self.ax_controls.axis('off')
        
        # Mini views
        self.ax_top = self.fig.add_subplot(2, 3, 3)
        self.ax_top.set_facecolor('black')
        self.ax_top.set_title('Top View', color='white', fontsize=12)
        
        self.ax_side = self.fig.add_subplot(2, 3, 5)
        self.ax_side.set_facecolor('black')
        self.ax_side.set_title('Side View', color='white', fontsize=12)
        
        self.ax_stats = self.fig.add_subplot(2, 3, 6)
        self.ax_stats.set_facecolor('black')
        self.ax_stats.set_title('Performance Stats', color='white', fontsize=12)
        self.ax_stats.axis('off')
        
        # Setup keyboard controls
        self.fig.canvas.mpl_connect('key_press_event', self.on_key_press)
        
        plt.tight_layout()
        self.fig.suptitle('RPLIDAR S3 Interactive 3D Scanner - Press H for Help', 
                         color='white', fontsize=20)
        
    def on_key_press(self, event):
        """Handle keyboard controls"""
        if event.key == 'h':
            self.show_help()
        elif event.key == 'm':
            self.cycle_viz_mode()
        elif event.key == 'r':
            self.auto_rotate = not self.auto_rotate
        elif event.key == 't':
            self.show_trails = not self.show_trails
        elif event.key == 'up':
            self.view_elevation = min(90, self.view_elevation + 5)
        elif event.key == 'down':
            self.view_elevation = max(-90, self.view_elevation - 5)
        elif event.key == 'left':
            self.view_azimuth -= 10
        elif event.key == 'right':
            self.view_azimuth += 10
        elif event.key == '+':
            self.point_size = min(20, self.point_size + 1)
        elif event.key == '-':
            self.point_size = max(1, self.point_size - 1)
        elif event.key == 'c':
            self.clear_point_cloud()
        elif event.key == 's':
            self.save_point_cloud()
            
    def show_help(self):
        """Display help information"""
        help_text = """
🎮 RPLIDAR S3 3D INTERACTIVE CONTROLS
═══════════════════════════════════════
[H] - Show this help
[M] - Cycle visualization modes
[R] - Toggle auto-rotation
[T] - Toggle trail effects
[↑↓] - Adjust elevation
[←→] - Adjust azimuth
[+/-] - Adjust point size
[C] - Clear point cloud
[S] - Save point cloud to file

🎨 VISUALIZATION MODES:
• Point Cloud (default)
• Surface mesh
• Wireframe
• Voxel grid

💡 TIP: Move your RPLIDAR to see 3D structure!
        """
        print(help_text)
        
    def cycle_viz_mode(self):
        """Cycle through visualization modes"""
        self.current_mode = (self.current_mode + 1) % len(self.viz_modes)
        print(f"🎨 Visualization mode: {self.viz_modes[self.current_mode]}")
        
    def clear_point_cloud(self):
        """Clear the 3D point cloud"""
        self.scans_3d.clear()
        self.z_height = 0
        print("🧹 Point cloud cleared")
        
    def save_point_cloud(self):
        """Save point cloud to file"""
        if not self.scans_3d:
            print("❌ No point cloud data to save")
            return
            
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"rplidar_3d_scan_{timestamp}.txt"
        
        try:
            with open(filename, 'w') as f:
                f.write("# RPLIDAR S3 3D Point Cloud\n")
                f.write("# Format: X Y Z Quality Timestamp\n")
                
                for scan_data in self.scans_3d:
                    x, y, z, colors, scan_time = scan_data
                    for i in range(len(x)):
                        f.write(f"{x[i]:.2f} {y[i]:.2f} {z[i]:.2f} {colors[i]:.3f} {scan_time:.3f}\n")
                        
            print(f"💾 Point cloud saved to {filename}")
            
        except Exception as e:
            print(f"❌ Failed to save: {e}")
        
    def start_rplidar_process(self):
        """Start RPLIDAR process"""
        try:
            exe_path = "../rplidar_sdk_dev/output/win32/Release/ultra_simple.exe"
            cmd = [exe_path, "--channel", "--serial", "COM8", "1000000"]
            
            print(f"🚀 Starting Interactive 3D RPLIDAR: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=0
            )
            
            print("✅ RPLIDAR S3 ready for interactive 3D scanning!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start RPLIDAR: {e}")
            return False
            
    def parse_line(self, line):
        """Parse RPLIDAR data"""
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
        """Data collection thread"""
        print("📡 Starting interactive 3D data collection...")
        
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
                        pass
                        
            except Exception as e:
                print(f"⚠️ Data error: {e}")
                break
                
    def scan_processor(self):
        """Process scans into 3D data"""
        while self.is_running:
            try:
                sync_flag, angle, distance, quality = self.data_queue.get(timeout=0.1)
                
                # Filter valid data
                if 100 < distance < 8000:  # 10cm to 8m
                    self.current_scan_angles.append(angle)
                    self.current_scan_distances.append(distance)
                    self.current_scan_qualities.append(quality)
                
                # Complete scan
                if sync_flag and len(self.current_scan_angles) > 30:
                    self.add_scan_to_3d()
                    
                    # Reset
                    self.current_scan_angles = []
                    self.current_scan_distances = []
                    self.current_scan_qualities = []
                    
                    self.scan_count += 1
                    self.z_height += self.z_increment
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"⚠️ Processing error: {e}")
                break
                
    def add_scan_to_3d(self):
        """Add current scan to 3D collection"""
        angles = np.array(self.current_scan_angles)
        distances = np.array(self.current_scan_distances)
        qualities = np.array(self.current_scan_qualities)
        
        # Convert to 3D coordinates
        angles_rad = np.radians(angles)
        x = distances * np.sin(angles_rad)
        y = distances * np.cos(angles_rad)
        z = np.full_like(x, self.z_height)
        
        # Color by quality
        colors = qualities / 63.0
        
        # Add to 3D collection
        scan_data = (x, y, z, colors, time.time())
        self.scans_3d.append(scan_data)
        
    def render_point_cloud(self):
        """Render point cloud mode"""
        all_x, all_y, all_z, all_colors = [], [], [], []
        
        for i, (x, y, z, colors, scan_time) in enumerate(self.scans_3d):
            # Apply trail effect
            if self.show_trails:
                age_factor = i / len(self.scans_3d)
                trail_alpha = age_factor * self.alpha
                
                all_x.extend(x)
                all_y.extend(y)
                all_z.extend(z)
                all_colors.extend(colors * age_factor)
            else:
                all_x.extend(x)
                all_y.extend(y)
                all_z.extend(z)
                all_colors.extend(colors)
        
        if all_x:
            scatter = self.ax_3d.scatter(all_x, all_y, all_z, 
                                        c=all_colors, s=self.point_size,
                                        cmap='plasma', alpha=self.alpha)
        
    def render_surface(self):
        """Render surface mesh mode"""
        if len(self.scans_3d) < 2:
            return
            
        # Get latest few scans for surface
        recent_scans = list(self.scans_3d)[-5:]
        
        for x, y, z, colors, _ in recent_scans:
            if len(x) > 10:
                # Create triangulated surface
                try:
                    self.ax_3d.plot_trisurf(x, y, z, alpha=0.6, cmap='plasma')
                except:
                    # Fallback to wireframe
                    self.ax_3d.plot(x, y, z, alpha=0.8, color='cyan')
        
    def render_wireframe(self):
        """Render wireframe mode"""
        for x, y, z, colors, _ in self.scans_3d:
            if len(x) > 1:
                self.ax_3d.plot(x, y, z, alpha=0.6, linewidth=0.5, color='lime')
        
    def render_voxel(self):
        """Render voxel grid mode"""
        if not self.scans_3d:
            return
            
        # Simple voxel representation
        all_x, all_y, all_z = [], [], []
        
        for x, y, z, colors, _ in self.scans_3d:
            all_x.extend(x)
            all_y.extend(y)
            all_z.extend(z)
        
        if all_x:
            # Voxelize the space
            x_vox = np.array(all_x) // 200  # 20cm voxels
            y_vox = np.array(all_y) // 200
            z_vox = np.array(all_z) // self.z_increment
            
            # Plot voxels
            self.ax_3d.scatter(x_vox * 200, y_vox * 200, z_vox * self.z_increment,
                              s=50, alpha=0.8, c='orange', marker='s')
        
    def stop_process(self):
        """Stop all processes"""
        self.is_running = False
        
        for thread in self.threads:
            thread.join(timeout=2)
            
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print("🛑 Interactive 3D RPLIDAR stopped")
        
    def update_3d_visualization(self, frame):
        """Update the interactive 3D visualization"""
        # Update FPS
        self.fps_counter += 1
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            self.fps = self.fps_counter
            self.fps_counter = 0
            self.last_fps_time = current_time
        
        if not self.scans_3d:
            return
            
        # Clear main 3D plot
        self.ax_3d.clear()
        self.ax_3d.set_facecolor('black')
        
        # Render based on current mode
        mode = self.viz_modes[self.current_mode]
        if mode == 'point_cloud':
            self.render_point_cloud()
        elif mode == 'surface':
            self.render_surface()
        elif mode == 'wireframe':
            self.render_wireframe()
        elif mode == 'voxel':
            self.render_voxel()
        
        # Configure 3D plot
        self.ax_3d.set_title(f'RPLIDAR S3 - Interactive 3D ({mode.title()})', 
                            color='white', fontsize=18)
        self.ax_3d.set_xlabel('X (mm)', color='white')
        self.ax_3d.set_ylabel('Y (mm)', color='white')
        self.ax_3d.set_zlabel('Z (Time)', color='white')
        
        # Set limits
        max_range = 6000
        self.ax_3d.set_xlim([-max_range, max_range])
        self.ax_3d.set_ylim([-max_range, max_range])
        self.ax_3d.set_zlim([0, max(100, self.z_height)])
        
        # Auto-rotate
        if self.auto_rotate:
            self.view_azimuth += self.rotate_speed
            if self.view_azimuth >= 360:
                self.view_azimuth = 0
                
        self.ax_3d.view_init(elev=self.view_elevation, azim=self.view_azimuth)
        self.ax_3d.grid(True, alpha=0.3)
        
        # Update control panel
        self.ax_controls.clear()
        self.ax_controls.set_facecolor('black')
        
        controls_text = f"""
🎮 INTERACTIVE CONTROLS
═════════════════════════
[H] Help     [M] Mode: {mode}
[R] Rotate: {'ON' if self.auto_rotate else 'OFF'}
[T] Trails: {'ON' if self.show_trails else 'OFF'}
[↑↓←→] View Control
[+/-] Point Size: {self.point_size}
[C] Clear    [S] Save

🎨 CURRENT VIEW
═════════════════════════
Elevation: {self.view_elevation:.0f}°
Azimuth: {self.view_azimuth:.0f}°
Mode: {mode.title()}
Alpha: {self.alpha:.1f}

📊 STATUS
═════════════════════════
Scans: {len(self.scans_3d)}/{self.max_scans}
Z Height: {self.z_height}mm
FPS: {self.fps}
        """
        
        self.ax_controls.text(0.05, 0.95, controls_text, transform=self.ax_controls.transAxes,
                             fontsize=10, verticalalignment='top', 
                             fontfamily='monospace', color='cyan')
        self.ax_controls.axis('off')
        
        # Update mini views and stats (simplified for performance)
        if frame % 5 == 0:  # Update every 5th frame
            self.update_mini_views()
        
    def update_mini_views(self):
        """Update top and side views"""
        if not self.scans_3d:
            return
            
        # Get latest scan for mini views
        latest_x, latest_y, latest_z, latest_colors, _ = self.scans_3d[-1]
        
        # Top view
        self.ax_top.clear()
        self.ax_top.set_facecolor('black')
        self.ax_top.scatter(latest_x, latest_y, c=latest_colors, s=4, cmap='plasma')
        self.ax_top.set_xlim([-3000, 3000])
        self.ax_top.set_ylim([-3000, 3000])
        self.ax_top.grid(True, alpha=0.3, color='gray')
        
        # Side view
        self.ax_side.clear()
        self.ax_side.set_facecolor('black')
        
        # Show all Z layers
        all_x, all_z = [], []
        for x, y, z, colors, _ in self.scans_3d:
            all_x.extend(x)
            all_z.extend(z)
            
        if all_x:
            self.ax_side.scatter(all_x, all_z, s=2, alpha=0.6, color='orange')
            self.ax_side.set_xlim([-3000, 3000])
            self.ax_side.set_ylim([0, max(100, self.z_height)])
            self.ax_side.grid(True, alpha=0.3, color='gray')
        
        # Stats
        self.ax_stats.clear()
        self.ax_stats.set_facecolor('black')
        
        runtime = time.time() - self.start_time
        total_points = sum(len(scan[0]) for scan in self.scans_3d)
        
        stats_text = f"""
📊 PERFORMANCE
══════════════════
FPS: {self.fps:2d}
Runtime: {runtime:.1f}s
Total Points: {total_points:,}
Scans: {self.scan_count:,}

🌍 3D ENVIRONMENT
══════════════════
Z Layers: {len(self.scans_3d)}
Height: {self.z_height}mm
Mode: {self.viz_modes[self.current_mode]}
        """
        
        self.ax_stats.text(0.05, 0.95, stats_text, transform=self.ax_stats.transAxes,
                          fontsize=9, verticalalignment='top', 
                          fontfamily='monospace', color='lime')
        self.ax_stats.axis('off')
        
    def start_visualization(self):
        """Start the interactive 3D visualization"""
        if not self.start_rplidar_process():
            return
            
        self.is_running = True
        
        # Start threads
        data_thread = threading.Thread(target=self.data_reader, daemon=True)
        scan_thread = threading.Thread(target=self.scan_processor, daemon=True)
        
        self.threads = [data_thread, scan_thread]
        
        for thread in self.threads:
            thread.start()
        
        print("🎮 Starting INTERACTIVE 3D visualization...")
        print("🌍 Press H for help and controls")
        print("🎨 Move your RPLIDAR to build 3D structure!")
        
        # Start animation
        ani = animation.FuncAnimation(self.fig, self.update_3d_visualization, 
                                     interval=100, cache_frame_data=False)
        
        try:
            plt.show()
        except KeyboardInterrupt:
            print("\n⏹️ Interrupted by user")
        finally:
            self.stop_process()

def main():
    print("🎮 RPLIDAR S3 INTERACTIVE 3D SCANNER")
    print("=====================================")
    print("🌍 Advanced 3D visualization with controls")
    print("📡 Port: COM8 | Baud: 1,000,000")
    print("🎨 Multiple visualization modes")
    print("⌨️ Keyboard controls for interaction")
    print()
    
    visualizer = RPLIDAR3DInteractive(max_scans=60)
    visualizer.start_visualization()

if __name__ == "__main__":
    main()
