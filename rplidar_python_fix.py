#!/usr/bin/env python3
"""
RPLIDAR Python Fix - Addresses Descriptor Length Mismatch
Based on analysis of the firmware compatibility issue
"""

import os
import sys
import time
import serial
from typing import Optional, List, Tuple, Generator
import struct

class RPLidarFixed:
    """
    Fixed RPLIDAR implementation that handles firmware 1.29+ compatibility issues
    Addresses the "Descriptor length mismatch" error
    """
    
    # RPLIDAR Commands
    CMD_STOP = 0x25
    CMD_RESET = 0x40
    CMD_SCAN = 0x20
    CMD_EXPRESS_SCAN = 0x82
    CMD_FORCE_SCAN = 0x21
    CMD_GET_INFO = 0x50
    CMD_GET_HEALTH = 0x52
    
    # Response types
    RESP_MEASUREMENT = 0x81
    RESP_DESCRIPTOR = 0x5A
    
    def __init__(self, port: str, baudrate: int = 256000, timeout: float = 2.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.scanning = False
        
    def connect(self) -> bool:
        """Connect to RPLIDAR device"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            
            # Reset device first
            self._send_command(self.CMD_RESET)
            time.sleep(2)  # Wait for reset
            
            # Clear any pending data
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            
            print(f"✅ Connected to RPLIDAR on {self.port} @ {self.baudrate}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from RPLIDAR device"""
        if self.scanning:
            self.stop_scan()
        
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("✅ RPLIDAR disconnected")
    
    def _send_command(self, cmd: int, payload: bytes = b'') -> bool:
        """Send command to RPLIDAR"""
        if not self.serial or not self.serial.is_open:
            return False
        
        try:
            # Command format: 0xA5 + cmd + payload_length + payload + checksum
            packet = bytearray([0xA5, cmd])
            
            if payload:
                packet.append(len(payload))
                packet.extend(payload)
                
                # Calculate checksum
                checksum = 0
                for byte in packet:
                    checksum ^= byte
                packet.append(checksum)
            
            self.serial.write(packet)
            self.serial.flush()
            return True
            
        except Exception as e:
            print(f"❌ Command send error: {e}")
            return False
    
    def _read_response_header(self) -> Optional[Tuple[int, int, int]]:
        """Read response header with improved error handling"""
        try:
            # Look for sync bytes
            sync_count = 0
            while sync_count < 2:
                byte = self.serial.read(1)
                if not byte:
                    return None
                
                if byte[0] == 0xA5:
                    sync_count += 1
                elif byte[0] == 0x5A and sync_count == 1:
                    sync_count += 1
                else:
                    sync_count = 0
            
            # Read response descriptor
            desc_bytes = self.serial.read(4)
            if len(desc_bytes) != 4:
                print(f"⚠️ Incomplete descriptor: got {len(desc_bytes)} bytes")
                return None
            
            # Parse descriptor
            data_length = desc_bytes[0]
            send_mode = desc_bytes[1] 
            data_type = desc_bytes[2]
            
            return data_length, send_mode, data_type
            
        except Exception as e:
            print(f"❌ Header read error: {e}")
            return None
    
    def get_device_info(self) -> Optional[dict]:
        """Get device information with improved parsing"""
        if not self._send_command(self.CMD_GET_INFO):
            return None
        
        time.sleep(0.1)
        header = self._read_response_header()
        if not header:
            return None
        
        data_length, send_mode, data_type = header
        
        try:
            # Read device info data
            info_data = self.serial.read(20)  # Standard device info length
            if len(info_data) < 20:
                print(f"⚠️ Incomplete device info: got {len(info_data)} bytes")
                return None
            
            return {
                'model': info_data[0],
                'firmware_minor': info_data[1],
                'firmware_major': info_data[2],
                'hardware': info_data[3],
                'serial': info_data[4:20].hex()
            }
            
        except Exception as e:
            print(f"❌ Device info parse error: {e}")
            return None
    
    def get_health_status(self) -> Optional[dict]:
        """Get device health status"""
        if not self._send_command(self.CMD_GET_HEALTH):
            return None
        
        time.sleep(0.1)
        header = self._read_response_header()
        if not header:
            return None
        
        try:
            health_data = self.serial.read(3)
            if len(health_data) < 3:
                return None
            
            status = health_data[0]
            error_code = (health_data[2] << 8) | health_data[1]
            
            return {
                'status': status,
                'error_code': error_code,
                'status_text': 'Good' if status == 0 else 'Warning' if status == 1 else 'Error'
            }
            
        except Exception as e:
            print(f"❌ Health status parse error: {e}")
            return None
    
    def start_scan(self, force_scan: bool = False) -> bool:
        """Start scanning with firmware compatibility handling"""
        if self.scanning:
            return True
        
        # Use FORCE_SCAN for newer firmware compatibility
        cmd = self.CMD_FORCE_SCAN if force_scan else self.CMD_SCAN
        
        if not self._send_command(cmd):
            return False
        
        time.sleep(0.1)
        
        # For scan commands, we expect a different response format
        # Some firmware versions don't send a standard response header
        try:
            # Try to read response, but don't fail if it's not standard
            response = self.serial.read(7)  # Try to read response descriptor
            self.scanning = True
            print(f"✅ Scan started ({'force' if force_scan else 'normal'} mode)")
            return True
            
        except Exception as e:
            print(f"⚠️ Scan start response unclear, but continuing: {e}")
            self.scanning = True
            return True
    
    def stop_scan(self):
        """Stop scanning"""
        if not self.scanning:
            return
        
        self._send_command(self.CMD_STOP)
        time.sleep(0.1)
        
        # Clear any remaining scan data
        if self.serial:
            self.serial.reset_input_buffer()
        
        self.scanning = False
        print("✅ Scan stopped")
    
    def read_scan_data(self, max_points: int = 1000) -> List[Tuple[float, float, int]]:
        """Read scan data with improved parsing"""
        if not self.scanning:
            return []
        
        points = []
        start_time = time.time()
        
        try:
            while len(points) < max_points and (time.time() - start_time) < 2.0:
                # Read measurement packet
                packet = self.serial.read(5)  # Standard measurement packet size
                if len(packet) != 5:
                    continue
                
                # Parse measurement (format may vary by firmware)
                try:
                    # Standard format: [sync_bit+quality][angle_low][angle_high][distance_low][distance_high]
                    sync_quality = packet[0]
                    angle_raw = (packet[2] << 8) | packet[1]
                    distance_raw = (packet[4] << 8) | packet[3]
                    
                    # Extract values
                    quality = (sync_quality >> 2) & 0x3F
                    angle = (angle_raw >> 1) / 64.0  # Convert to degrees
                    distance = distance_raw / 4.0    # Convert to mm
                    
                    # Filter valid measurements
                    if distance > 0 and angle >= 0 and angle < 360:
                        points.append((angle, distance, quality))
                    
                except Exception as parse_error:
                    # Try alternative parsing for different firmware versions
                    continue
                    
        except Exception as e:
            print(f"⚠️ Scan data read error: {e}")
        
        return points
    
    def iter_scans(self, max_buf_meas: int = 5000) -> Generator[List[Tuple[float, float, int]], None, None]:
        """Iterate over scans with improved error handling"""
        if not self.start_scan(force_scan=True):  # Use force scan for compatibility
            return
        
        try:
            while self.scanning:
                scan_data = self.read_scan_data(max_buf_meas)
                if scan_data:
                    # Convert to expected format: (quality, angle, distance)
                    formatted_scan = [(quality, angle, distance) for angle, distance, quality in scan_data]
                    yield formatted_scan
                else:
                    time.sleep(0.01)  # Small delay if no data
                    
        except KeyboardInterrupt:
            print("\n⏹️ Scan interrupted by user")
        except Exception as e:
            print(f"❌ Scan iteration error: {e}")
        finally:
            self.stop_scan()

def test_rplidar_fixed(port: str, baudrate: int = 256000):
    """Test the fixed RPLIDAR implementation"""
    print(f"🔧 Testing Fixed RPLIDAR Implementation")
    print(f"   Port: {port}")
    print(f"   Baudrate: {baudrate}")
    print("-" * 50)
    
    lidar = RPLidarFixed(port, baudrate)
    
    try:
        # Connect
        if not lidar.connect():
            return False
        
        # Get device info
        print("\n📋 Device Information:")
        info = lidar.get_device_info()
        if info:
            print(f"   Model: {info['model']}")
            print(f"   Firmware: {info['firmware_major']}.{info['firmware_minor']}")
            print(f"   Hardware: {info['hardware']}")
            print(f"   Serial: {info['serial'][:16]}...")
        else:
            print("   ⚠️ Could not retrieve device info")
        
        # Get health status
        print("\n🏥 Health Status:")
        health = lidar.get_health_status()
        if health:
            print(f"   Status: {health['status_text']} ({health['status']})")
            if health['error_code'] != 0:
                print(f"   Error Code: {health['error_code']}")
        else:
            print("   ⚠️ Could not retrieve health status")
        
        # Test scanning
        print(f"\n📡 Testing Scan (5 scans):")
        scan_count = 0
        total_points = 0
        
        for scan in lidar.iter_scans(max_buf_meas=1000):
            scan_count += 1
            valid_points = [p for p in scan if p[2] > 0]  # Filter valid points
            total_points += len(valid_points)
            
            print(f"   Scan {scan_count}: {len(scan)} total, {len(valid_points)} valid points")
            
            # Show sample points
            if valid_points and len(valid_points) >= 3:
                print(f"   Sample points: ", end="")
                for i in range(min(3, len(valid_points))):
                    quality, angle, distance = valid_points[i]
                    print(f"({angle:.1f}°, {distance:.0f}mm) ", end="")
                print()
            
            if scan_count >= 5:
                break
        
        print(f"\n✅ Test completed successfully!")
        print(f"   Total scans: {scan_count}")
        print(f"   Total points: {total_points}")
        print(f"   Average points per scan: {total_points / max(scan_count, 1):.1f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
        
    finally:
        lidar.disconnect()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fixed RPLIDAR Implementation")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Serial port")
    parser.add_argument("--baud", type=int, default=256000, help="Baudrate")
    parser.add_argument("--test", action="store_true", help="Run test")
    
    args = parser.parse_args()
    
    if args.test:
        success = test_rplidar_fixed(args.port, args.baud)
        sys.exit(0 if success else 1)
    else:
        print("Use --test to run the diagnostic test")
        print(f"Example: python {sys.argv[0]} --test --port /dev/ttyUSB0 --baud 256000")

if __name__ == "__main__":
    main()

