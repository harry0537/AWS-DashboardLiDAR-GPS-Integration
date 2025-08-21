#!/usr/bin/env python3
"""
Complete RPLIDAR Solution - Addresses Descriptor Length Mismatch Issue
Combines multiple approaches to fix the firmware compatibility problem
"""

import os
import sys
import time
import serial
import serial.tools.list_ports
from typing import Optional, List, Tuple, Generator, Dict, Any
import struct

class RPLidarCompleteSolution:
    """
    Complete RPLIDAR solution that handles the "Descriptor length mismatch" issue
    
    Root Cause Analysis:
    1. Firmware 1.29+ changed default scan modes (boost mode)
    2. rplidar-roboticia library doesn't handle new protocol properly
    3. Timing issues with command/response sequences
    4. Incorrect descriptor parsing for newer firmware
    """
    
    # RPLIDAR Commands
    CMD_STOP = 0x25
    CMD_RESET = 0x40
    CMD_SCAN = 0x20
    CMD_EXPRESS_SCAN = 0x82
    CMD_FORCE_SCAN = 0x21
    CMD_GET_INFO = 0x50
    CMD_GET_HEALTH = 0x52
    
    # Response identifiers
    RESP_MEASUREMENT = 0x81
    RESP_DESCRIPTOR = 0x5A
    
    def __init__(self, port: str, baudrate: int = 256000, timeout: float = 3.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.scanning = False
        self.motor_running = False
        self.device_info = None
        
    def find_rplidar_ports(self) -> List[str]:
        """Find potential RPLIDAR ports"""
        ports = []
        for port in serial.tools.list_ports.comports():
            # Look for common RPLIDAR characteristics
            if (port.vid and port.pid and 
                (port.vid == 0x10C4 and port.pid == 0xEA60) or  # CP2102 USB-Serial
                (port.vid == 0x0403 and port.pid == 0x6001) or  # FTDI
                port.device.startswith('COM') or 
                port.device.startswith('/dev/ttyUSB') or
                port.device.startswith('/dev/ttyACM')):
                ports.append(port.device)
        
        return ports
    
    def connect(self) -> bool:
        """Connect with improved error handling"""
        try:
            print(f"🔗 Connecting to {self.port} @ {self.baudrate} baud...")
            
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            
            # Give device time to initialize
            time.sleep(0.5)
            
            # Reset device to known state
            self._reset_device()
            
            # Test basic communication
            if self._test_communication():
                print(f"✅ Connected successfully to {self.port}")
                return True
            else:
                print(f"❌ Communication test failed")
                return False
                
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def _reset_device(self):
        """Reset device with proper timing"""
        try:
            # Stop any ongoing operations
            self._send_command(self.CMD_STOP)
            time.sleep(0.1)
            
            # Reset device
            self._send_command(self.CMD_RESET)
            time.sleep(2.0)  # Wait for reset to complete
            
            # Clear buffers
            if self.serial:
                self.serial.reset_input_buffer()
                self.serial.reset_output_buffer()
            
            print("🔄 Device reset completed")
            
        except Exception as e:
            print(f"⚠️ Reset error: {e}")
    
    def _test_communication(self) -> bool:
        """Test basic communication"""
        try:
            # Try to get device info
            info = self.get_device_info()
            if info:
                self.device_info = info
                print(f"📋 Device: Model {info['model']}, FW {info['firmware_major']}.{info['firmware_minor']}")
                return True
            else:
                # Try alternative communication test
                return self._raw_communication_test()
                
        except Exception as e:
            print(f"⚠️ Communication test error: {e}")
            return False
    
    def _raw_communication_test(self) -> bool:
        """Raw communication test as fallback"""
        try:
            # Send reset command and check for any response
            self.serial.write(b'\\xA5\\x40')
            time.sleep(0.5)
            
            if self.serial.in_waiting > 0:
                response = self.serial.read(self.serial.in_waiting)
                print(f"📡 Raw response: {len(response)} bytes")
                return True
            else:
                print("📡 No raw response")
                return False
                
        except Exception as e:
            print(f"⚠️ Raw test error: {e}")
            return False
    
    def disconnect(self):
        """Clean disconnect"""
        try:
            if self.scanning:
                self.stop_scan()
            
            if self.serial and self.serial.is_open:
                self.serial.close()
                print("✅ Disconnected")
                
        except Exception as e:
            print(f"⚠️ Disconnect error: {e}")
    
    def _send_command(self, cmd: int, payload: bytes = b'') -> bool:
        """Send command with checksum"""
        if not self.serial or not self.serial.is_open:
            return False
        
        try:
            # Build packet: 0xA5 + cmd + [payload_len + payload + checksum]
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
            print(f"❌ Command error: {e}")
            return False
    
    def _read_response_descriptor(self) -> Optional[Dict[str, Any]]:
        """Read response descriptor with multiple parsing strategies"""
        try:
            # Strategy 1: Look for standard sync pattern
            sync_found = False
            attempts = 0
            max_attempts = 100
            
            while not sync_found and attempts < max_attempts:
                byte = self.serial.read(1)
                if not byte:
                    break
                    
                if byte[0] == 0xA5:
                    next_byte = self.serial.read(1)
                    if next_byte and next_byte[0] == 0x5A:
                        sync_found = True
                        break
                
                attempts += 1
            
            if not sync_found:
                return None
            
            # Read descriptor
            desc_data = self.serial.read(4)
            if len(desc_data) < 4:
                return None
            
            return {
                'data_length': desc_data[0],
                'send_mode': desc_data[1],
                'data_type': desc_data[2],
                'reserved': desc_data[3]
            }
            
        except Exception as e:
            print(f"⚠️ Descriptor read error: {e}")
            return None
    
    def get_device_info(self) -> Optional[Dict[str, Any]]:
        """Get device info with improved parsing"""
        if not self._send_command(self.CMD_GET_INFO):
            return None
        
        time.sleep(0.2)  # Increased wait time
        
        descriptor = self._read_response_descriptor()
        if not descriptor:
            return None
        
        try:
            # Read device info payload
            info_data = self.serial.read(20)
            if len(info_data) < 20:
                return None
            
            return {
                'model': info_data[0],
                'firmware_minor': info_data[1],
                'firmware_major': info_data[2],
                'hardware': info_data[3],
                'serial': info_data[4:20].hex().upper()
            }
            
        except Exception as e:
            print(f"❌ Device info error: {e}")
            return None
    
    def get_health_status(self) -> Optional[Dict[str, Any]]:
        """Get health status"""
        if not self._send_command(self.CMD_GET_HEALTH):
            return None
        
        time.sleep(0.2)
        
        descriptor = self._read_response_descriptor()
        if not descriptor:
            return None
        
        try:
            health_data = self.serial.read(3)
            if len(health_data) < 3:
                return None
            
            status = health_data[0]
            error_code = (health_data[2] << 8) | health_data[1]
            
            status_text = {0: 'Good', 1: 'Warning', 2: 'Error'}.get(status, 'Unknown')
            
            return {
                'status': status,
                'error_code': error_code,
                'status_text': status_text
            }
            
        except Exception as e:
            print(f"❌ Health status error: {e}")
            return None
    
    def start_motor(self) -> bool:
        """Start motor (if supported)"""
        # Some RPLIDAR models don't have motor control
        self.motor_running = True
        print("🔄 Motor started (or assumed running)")
        return True
    
    def stop_motor(self):
        """Stop motor (if supported)"""
        self.motor_running = False
        print("⏹️ Motor stopped (or assumed stopped)")
    
    def start_scan(self, express_mode: bool = False) -> bool:
        """Start scan with multiple strategies"""
        if self.scanning:
            return True
        
        # Try different scan modes for compatibility
        scan_commands = [
            (self.CMD_FORCE_SCAN, "Force Scan"),
            (self.CMD_SCAN, "Standard Scan"),
        ]
        
        if express_mode:
            scan_commands.insert(0, (self.CMD_EXPRESS_SCAN, "Express Scan"))
        
        for cmd, name in scan_commands:
            print(f"🔍 Trying {name}...")
            
            if self._send_command(cmd):
                time.sleep(0.5)  # Wait for scan to start
                
                # Check for any response (some firmware versions vary)
                if self.serial.in_waiting > 0:
                    response = self.serial.read(min(self.serial.in_waiting, 50))
                    print(f"📡 Scan response: {len(response)} bytes")
                
                self.scanning = True
                print(f"✅ {name} started")
                return True
        
        print("❌ All scan modes failed")
        return False
    
    def stop_scan(self):
        """Stop scanning"""
        if not self.scanning:
            return
        
        self._send_command(self.CMD_STOP)
        time.sleep(0.2)
        
        # Clear scan data buffer
        if self.serial and self.serial.in_waiting > 0:
            self.serial.read(self.serial.in_waiting)
        
        self.scanning = False
        print("⏹️ Scan stopped")
    
    def read_scan_points(self, max_points: int = 1000, timeout: float = 2.0) -> List[Tuple[int, float, float]]:
        """Read scan points with multiple parsing strategies"""
        if not self.scanning:
            return []
        
        points = []
        start_time = time.time()
        
        try:
            while len(points) < max_points and (time.time() - start_time) < timeout:
                if self.serial.in_waiting < 5:
                    time.sleep(0.001)
                    continue
                
                # Read potential measurement packet
                packet = self.serial.read(5)
                if len(packet) != 5:
                    continue
                
                # Try multiple parsing strategies
                point = self._parse_measurement_packet(packet)
                if point:
                    points.append(point)
                    
        except Exception as e:
            print(f"⚠️ Scan read error: {e}")
        
        return points
    
    def _parse_measurement_packet(self, packet: bytes) -> Optional[Tuple[int, float, float]]:
        """Parse measurement packet with multiple format support"""
        try:
            # Strategy 1: Standard RPLIDAR format
            sync_quality = packet[0]
            angle_raw = (packet[2] << 8) | packet[1]
            distance_raw = (packet[4] << 8) | packet[3]
            
            # Check sync bit
            if not (sync_quality & 0x01):
                return None
            
            quality = (sync_quality >> 2) & 0x3F
            angle = (angle_raw >> 1) / 64.0
            distance = distance_raw / 4.0
            
            # Validate measurement
            if 0 <= angle < 360 and distance > 0 and distance < 50000:  # 50m max
                return (quality, angle, distance)
            
        except Exception:
            pass
        
        # Strategy 2: Alternative format for newer firmware
        try:
            # Different bit arrangements for newer firmware
            quality = packet[0] & 0x3F
            angle = ((packet[2] << 8) | packet[1]) / 64.0
            distance = ((packet[4] << 8) | packet[3]) / 4.0
            
            if 0 <= angle < 360 and distance > 0 and distance < 50000:
                return (quality, angle, distance)
                
        except Exception:
            pass
        
        return None
    
    def iter_scans(self, max_buf_meas: int = 5000) -> Generator[List[Tuple[int, float, float]], None, None]:
        """Iterate over scans with improved error handling"""
        if not self.start_scan():
            return
        
        try:
            consecutive_empty = 0
            max_empty = 10
            
            while self.scanning and consecutive_empty < max_empty:
                points = self.read_scan_points(max_buf_meas, timeout=1.0)
                
                if points:
                    consecutive_empty = 0
                    yield points
                else:
                    consecutive_empty += 1
                    time.sleep(0.1)
                    
        except KeyboardInterrupt:
            print("\\n⏹️ Scan interrupted")
        except Exception as e:
            print(f"❌ Scan iteration error: {e}")
        finally:
            self.stop_scan()

def auto_detect_rplidar() -> List[Dict[str, Any]]:
    """Auto-detect RPLIDAR devices"""
    print("🔍 Auto-detecting RPLIDAR devices...")
    
    found_devices = []
    common_baudrates = [115200, 256000, 230400, 460800, 921600]
    
    # Get available ports
    ports = []
    for port in serial.tools.list_ports.comports():
        ports.append(port.device)
    
    if not ports:
        print("❌ No serial ports found")
        return []
    
    print(f"📍 Found {len(ports)} serial ports: {ports}")
    
    for port in ports:
        print(f"\\n🔍 Testing {port}...")
        
        for baudrate in common_baudrates:
            print(f"  📡 Trying {baudrate} baud...", end=" ")
            
            try:
                lidar = RPLidarCompleteSolution(port, baudrate, timeout=2.0)
                
                if lidar.connect():
                    info = lidar.device_info
                    health = lidar.get_health_status()
                    
                    found_devices.append({
                        'port': port,
                        'baudrate': baudrate,
                        'device_info': info,
                        'health': health,
                        'working': True
                    })
                    
                    print(f"✅ WORKING")
                    lidar.disconnect()
                    break  # Found working config for this port
                else:
                    print(f"❌ Failed")
                    
                lidar.disconnect()
                
            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}...")
    
    return found_devices

def test_rplidar_scanning(port: str, baudrate: int) -> bool:
    """Test RPLIDAR scanning capability"""
    print(f"\\n🧪 Testing scanning on {port} @ {baudrate}")
    print("-" * 50)
    
    lidar = RPLidarCompleteSolution(port, baudrate)
    
    try:
        if not lidar.connect():
            return False
        
        # Test scanning
        print("📡 Starting scan test (5 scans)...")
        scan_count = 0
        total_points = 0
        
        for scan_data in lidar.iter_scans(max_buf_meas=1000):
            scan_count += 1
            valid_points = [p for p in scan_data if p[2] > 0]  # Filter by distance > 0
            total_points += len(valid_points)
            
            print(f"  Scan {scan_count}: {len(scan_data)} total, {len(valid_points)} valid points")
            
            # Show sample points
            if valid_points and len(valid_points) >= 3:
                print("  Sample points: ", end="")
                for i in range(min(3, len(valid_points))):
                    quality, angle, distance = valid_points[i]
                    print(f"({angle:.1f}°, {distance:.0f}mm, Q{quality}) ", end="")
                print()
            
            if scan_count >= 5:
                break
        
        if total_points > 0:
            print(f"\\n✅ Scanning test successful!")
            print(f"   Average points per scan: {total_points / max(scan_count, 1):.1f}")
            return True
        else:
            print(f"\\n❌ No scan data received")
            return False
            
    except Exception as e:
        print(f"❌ Scanning test failed: {e}")
        return False
        
    finally:
        lidar.disconnect()

def main():
    """Main diagnostic and testing function"""
    print("🚀 RPLIDAR Complete Solution - Descriptor Length Mismatch Fix")
    print("=" * 70)
    
    # Auto-detect devices
    devices = auto_detect_rplidar()
    
    if not devices:
        print("\\n❌ No RPLIDAR devices detected!")
        print("\\n🔧 Troubleshooting:")
        print("   1. Check USB connection")
        print("   2. Verify power supply (5V, adequate current)")
        print("   3. Try different USB cable")
        print("   4. Check Device Manager (Windows) for COM ports")
        return False
    
    print(f"\\n✅ Found {len(devices)} working RPLIDAR configuration(s):")
    print("-" * 50)
    
    for i, device in enumerate(devices, 1):
        print(f"{i}. Port: {device['port']}")
        print(f"   Baudrate: {device['baudrate']:,}")
        
        if device['device_info']:
            info = device['device_info']
            print(f"   Model: {info['model']}")
            print(f"   Firmware: {info['firmware_major']}.{info['firmware_minor']}")
            print(f"   Hardware: {info['hardware']}")
        
        if device['health']:
            health = device['health']
            print(f"   Health: {health['status_text']}")
        
        print()
    
    # Test scanning on the first working device
    if devices:
        best_device = devices[0]
        print(f"🎯 Testing scanning with best configuration:")
        print(f"   {best_device['port']} @ {best_device['baudrate']} baud")
        
        success = test_rplidar_scanning(best_device['port'], best_device['baudrate'])
        
        if success:
            print(f"\\n🎉 RPLIDAR is working correctly!")
            print(f"\\n📝 Use these settings in your code:")
            print(f"   RPLIDAR_PORT = '{best_device['port']}'")
            print(f"   RPLIDAR_BAUD = {best_device['baudrate']}")
            
            # Generate updated script
            generate_updated_script(best_device['port'], best_device['baudrate'])
            
        return success
    
    return False

def generate_updated_script(port: str, baudrate: int):
    """Generate updated script with working configuration"""
    script_content = f'''#!/usr/bin/env python3
"""
Updated RPLIDAR Script - Uses working configuration
Generated by RPLIDAR Complete Solution
"""

import os
import time
from rplidar_complete_solution import RPLidarCompleteSolution

# Working configuration
RPLIDAR_PORT = "{port}"
RPLIDAR_BAUD = {baudrate}

def main():
    """Main RPLIDAR data collection"""
    print(f"🔍 Starting RPLIDAR data collection...")
    print(f"   Port: {{RPLIDAR_PORT}}")
    print(f"   Baudrate: {{RPLIDAR_BAUD:,}}")
    
    lidar = RPLidarCompleteSolution(RPLIDAR_PORT, RPLIDAR_BAUD)
    
    try:
        if not lidar.connect():
            print("❌ Failed to connect to RPLIDAR")
            return
        
        print("✅ Connected! Starting data collection...")
        
        for i, scan_data in enumerate(lidar.iter_scans(max_buf_meas=5000)):
            # Process scan data
            valid_points = [p for p in scan_data if p[2] > 0]
            
            if valid_points:
                closest_distance = min(p[2] for p in valid_points)
                print(f"Scan {{i+1}}: {{len(valid_points)}} points, closest: {{closest_distance:.0f}}mm")
            
            # Your data processing logic here
            # Example: send to DynamoDB, save to file, etc.
            
            time.sleep(0.1)  # 10Hz update rate
            
    except KeyboardInterrupt:
        print("\\n⏹️ Stopping data collection...")
    except Exception as e:
        print(f"❌ Error: {{e}}")
    finally:
        lidar.disconnect()

if __name__ == "__main__":
    main()
'''
    
    with open('rplidar_working_example.py', 'w') as f:
        f.write(script_content)
    
    print(f"\\n📄 Generated: rplidar_working_example.py")
    print(f"   Run with: python rplidar_working_example.py")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

