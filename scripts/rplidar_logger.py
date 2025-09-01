#!/usr/bin/env python3
"""
RPLIDAR S3 Data Logger
Logs scan data to CSV with statistics
"""

import serial
import csv
import time
import argparse
import re
from datetime import datetime

class RPLIDARLogger:
    def __init__(self, com_port='COM8', baud_rate=1000000, output_file=None):
        self.com_port = com_port
        self.baud_rate = baud_rate
        self.output_file = output_file or f"rplidar_s3_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        self.serial_port = None
        self.csv_writer = None
        self.csv_file = None
        
        # Statistics
        self.scan_count = 0
        self.point_count = 0
        self.start_time = None
        
    def connect(self):
        """Connect to RPLIDAR"""
        try:
            print(f"🔌 Connecting to RPLIDAR S3 on {self.com_port}...")
            self.serial_port = serial.Serial(
                port=self.com_port,
                baudrate=self.baud_rate,
                timeout=1.0
            )
            print("✅ Connected successfully!")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
            
    def setup_csv(self):
        """Setup CSV file for logging"""
        try:
            self.csv_file = open(self.output_file, 'w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            
            # Write header
            header = ['timestamp', 'scan_id', 'angle_deg', 'distance_mm', 'quality', 'sync_flag']
            self.csv_writer.writerow(header)
            
            print(f"📝 Logging to: {self.output_file}")
            return True
        except Exception as e:
            print(f"❌ CSV setup failed: {e}")
            return False
            
    def parse_line(self, line):
        """Parse RPLIDAR data line"""
        pattern = r'([S\s]*)\s*theta:\s*([\d.]+)\s+Dist:\s*([\d.]+)(?:\s+Q:\s*(\d+))?'
        match = re.match(pattern, line.strip())
        
        if match:
            sync_flag = 'S' in match.group(1)
            angle = float(match.group(2))
            distance = float(match.group(3))
            quality = int(match.group(4)) if match.group(4) else 30
            
            return sync_flag, angle, distance, quality
        return None
        
    def log_data(self, duration=None):
        """Log data for specified duration (None = continuous)"""
        if not self.connect() or not self.setup_csv():
            return
            
        self.start_time = time.time()
        current_scan_id = 0
        
        print("📡 Starting data logging...")
        if duration:
            print(f"⏱️ Duration: {duration} seconds")
        else:
            print("⏱️ Duration: Continuous (Ctrl+C to stop)")
        print()
        
        try:
            while True:
                # Check duration
                if duration and (time.time() - self.start_time) > duration:
                    print(f"\n⏰ Reached {duration} second limit")
                    break
                    
                if self.serial_port.in_waiting:
                    line = self.serial_port.readline().decode('utf-8', errors='ignore')
                    parsed = self.parse_line(line)
                    
                    if parsed:
                        sync_flag, angle, distance, quality = parsed
                        
                        # Skip invalid readings
                        if distance > 0:
                            timestamp = time.time()
                            
                            if sync_flag:
                                current_scan_id += 1
                                self.scan_count += 1
                                
                            # Write to CSV
                            row = [timestamp, current_scan_id, angle, distance, quality, sync_flag]
                            self.csv_writer.writerow(row)
                            
                            self.point_count += 1
                            
                            # Print progress every 1000 points
                            if self.point_count % 1000 == 0:
                                elapsed = time.time() - self.start_time
                                rate = self.point_count / elapsed
                                print(f"📊 Points: {self.point_count:,} | Scans: {self.scan_count} | Rate: {rate:.0f} pts/sec")
                                
        except KeyboardInterrupt:
            print("\n⏹️ Stopped by user")
        except Exception as e:
            print(f"\n❌ Error: {e}")
        finally:
            self.cleanup()
            
    def cleanup(self):
        """Cleanup connections and files"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            
        if self.csv_file:
            self.csv_file.close()
            
        # Print final statistics
        if self.start_time:
            elapsed = time.time() - self.start_time
            print(f"\n📈 Final Statistics:")
            print(f"   ⏱️ Duration: {elapsed:.1f}s")
            print(f"   📊 Total Points: {self.point_count:,}")
            print(f"   🔄 Total Scans: {self.scan_count}")
            print(f"   📡 Average Rate: {self.point_count/elapsed:.0f} pts/sec")
            print(f"   📝 File: {self.output_file}")
            
def main():
    parser = argparse.ArgumentParser(description='RPLIDAR S3 Data Logger')
    parser.add_argument('--port', default='COM8', help='COM port (default: COM8)')
    parser.add_argument('--baud', type=int, default=1000000, help='Baud rate (default: 1000000)')
    parser.add_argument('--output', help='Output CSV file (default: auto-generated)')
    parser.add_argument('--duration', type=int, help='Duration in seconds (default: continuous)')
    
    args = parser.parse_args()
    
    print("📝 RPLIDAR S3 Data Logger")
    print("========================")
    print(f"Port: {args.port}")
    print(f"Baud: {args.baud}")
    print(f"Output: {args.output or 'auto-generated'}")
    print(f"Duration: {args.duration or 'continuous'}")
    print()
    
    logger = RPLIDARLogger(args.port, args.baud, args.output)
    logger.log_data(args.duration)

if __name__ == "__main__":
    main()
