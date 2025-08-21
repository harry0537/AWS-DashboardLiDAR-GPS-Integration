#!/usr/bin/env python3
"""
RPLIDAR Results Analyzer
Reads and interprets results from the C++ diagnostic tool
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any

class RPLidarResultsAnalyzer:
    def __init__(self, results_file: str = "rplidar_diagnostic_results.json"):
        self.results_file = results_file
        self.results_data = None
        self.working_configs = []
        self.partial_configs = []
        self.failed_configs = []
        
    def load_results(self) -> bool:
        """Load diagnostic results from JSON file"""
        if not os.path.exists(self.results_file):
            print(f"❌ Results file not found: {self.results_file}")
            print("Run the C++ diagnostic first: ./rplidar_cpp_diagnostic")
            return False
        
        try:
            with open(self.results_file, 'r') as f:
                self.results_data = json.load(f)
            print(f"✅ Loaded results from {self.results_file}")
            return True
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in results file: {e}")
            return False
        except Exception as e:
            print(f"❌ Error reading results file: {e}")
            return False
    
    def analyze_results(self):
        """Analyze and categorize test results"""
        if not self.results_data or 'test_results' not in self.results_data:
            print("❌ No test results found in data")
            return
        
        self.working_configs = []
        self.partial_configs = []
        self.failed_configs = []
        
        for result in self.results_data['test_results']:
            if result['scan_start_success'] and result['scan_points_received'] > 0:
                self.working_configs.append(result)
            elif (result['device_info_success'] or 
                  result['health_check_success'] or 
                  result['raw_communication']):
                self.partial_configs.append(result)
            else:
                self.failed_configs.append(result)
    
    def print_summary(self):
        """Print analysis summary"""
        print("\n" + "="*60)
        print("🔍 RPLIDAR DIAGNOSTIC RESULTS ANALYSIS")
        print("="*60)
        
        if 'timestamp' in self.results_data:
            print(f"📅 Test Date: {self.results_data['timestamp']}")
        
        total_tests = len(self.results_data['test_results'])
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Working Configurations: {len(self.working_configs)}")
        print(f"⚠️  Partial Configurations: {len(self.partial_configs)}")
        print(f"❌ Failed Configurations: {len(self.failed_configs)}")
        
    def print_working_configs(self):
        """Print working configurations"""
        if not self.working_configs:
            print("\n❌ NO WORKING CONFIGURATIONS FOUND")
            return
        
        print(f"\n✅ WORKING CONFIGURATIONS ({len(self.working_configs)}):")
        print("-" * 50)
        
        for i, config in enumerate(self.working_configs, 1):
            print(f"{i}. Port: {config['port']}")
            print(f"   Baudrate: {config['baudrate']:,}")
            print(f"   Scan Points: {config['scan_points_received']}")
            print(f"   Test Duration: {config['test_duration_ms']:.1f}ms")
            print(f"   Device Info: {'✓' if config['device_info_success'] else '✗'}")
            print(f"   Health Check: {'✓' if config['health_check_success'] else '✗'}")
            print()
        
        # Recommend best configuration
        best_config = max(self.working_configs, key=lambda x: x['scan_points_received'])
        print(f"🎯 RECOMMENDED CONFIGURATION:")
        print(f"   Port: {best_config['port']}")
        print(f"   Baudrate: {best_config['baudrate']:,}")
        print(f"   Reason: Highest scan point count ({best_config['scan_points_received']} points)")
    
    def print_partial_configs(self):
        """Print partially working configurations"""
        if not self.partial_configs:
            return
        
        print(f"\n⚠️  PARTIALLY WORKING CONFIGURATIONS ({len(self.partial_configs)}):")
        print("-" * 50)
        
        for i, config in enumerate(self.partial_configs, 1):
            capabilities = []
            if config['raw_communication']:
                capabilities.append("Raw Communication")
            if config['device_info_success']:
                capabilities.append("Device Info")
            if config['health_check_success']:
                capabilities.append("Health Check")
            
            print(f"{i}. Port: {config['port']} @ {config['baudrate']:,} baud")
            print(f"   Working: {', '.join(capabilities)}")
            print(f"   Issue: Scanning failed")
            if config['error_message']:
                print(f"   Error: {config['error_message']}")
            print()
    
    def print_troubleshooting(self):
        """Print troubleshooting recommendations"""
        print("\n🔧 TROUBLESHOOTING RECOMMENDATIONS:")
        print("-" * 50)
        
        if self.working_configs:
            print("✅ Great! You have working configurations.")
            print("   Use the recommended configuration above.")
            print("   Update your Python scripts with these settings:")
            best_config = max(self.working_configs, key=lambda x: x['scan_points_received'])
            print(f"   RPLIDAR_PORT = '{best_config['port']}'")
            print(f"   RPLIDAR_BAUD = {best_config['baudrate']}")
            
        elif self.partial_configs:
            print("⚠️  Device communicates but scanning fails.")
            print("   This suggests a protocol or timing issue.")
            print("   Try these solutions:")
            print("   1. Add delays between commands")
            print("   2. Use different scan modes (if supported)")
            print("   3. Reset device between attempts")
            print("   4. Check for firmware compatibility")
            
        else:
            print("❌ No communication detected.")
            print("   Hardware troubleshooting needed:")
            print("   1. Check USB cable connection")
            print("   2. Verify power supply (5V, adequate current)")
            print("   3. Try different USB port")
            print("   4. Check if device appears in system:")
            if os.name == 'nt':
                print("      Device Manager > Ports (COM & LPT)")
            else:
                print("      dmesg | grep -i usb")
                print("      ls -la /dev/ttyUSB* /dev/ttyACM*")
            print("   5. Test with different computer")
            print("   6. Contact manufacturer if device is new")
    
    def generate_python_config(self):
        """Generate Python configuration file"""
        if not self.working_configs:
            return
        
        best_config = max(self.working_configs, key=lambda x: x['scan_points_received'])
        
        config_content = f'''#!/usr/bin/env python3
"""
Auto-generated RPLIDAR configuration
Generated from C++ diagnostic results on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

# RPLIDAR Configuration - WORKING SETTINGS
RPLIDAR_PORT = "{best_config['port']}"
RPLIDAR_BAUD = {best_config['baudrate']}

# Diagnostic Results
SCAN_POINTS_RECEIVED = {best_config['scan_points_received']}
DEVICE_INFO_SUCCESS = {str(best_config['device_info_success']).lower()}
HEALTH_CHECK_SUCCESS = {str(best_config['health_check_success']).lower()}
TEST_DURATION_MS = {best_config['test_duration_ms']:.1f}

# Usage Example:
if __name__ == "__main__":
    print(f"RPLIDAR Configuration:")
    print(f"  Port: {{RPLIDAR_PORT}}")
    print(f"  Baudrate: {{RPLIDAR_BAUD:,}}")
    print(f"  Expected scan points: {{SCAN_POINTS_RECEIVED}}")
    
    # Update your environment variables:
    import os
    os.environ["RPLIDAR_PORT"] = RPLIDAR_PORT
    os.environ["RPLIDAR_BAUD"] = str(RPLIDAR_BAUD)
    
    print("Environment variables updated!")
'''
        
        config_file = "rplidar_config.py"
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        print(f"\n📝 Generated Python configuration: {config_file}")
        print("   You can import this in your scripts:")
        print(f"   from rplidar_config import RPLIDAR_PORT, RPLIDAR_BAUD")
    
    def create_test_script(self):
        """Create a test script using the working configuration"""
        if not self.working_configs:
            return
        
        best_config = max(self.working_configs, key=lambda x: x['scan_points_received'])
        
        test_script = f'''#!/usr/bin/env python3
"""
RPLIDAR Test Script
Auto-generated from C++ diagnostic results
"""

import time
import sys

# Configuration from diagnostic
RPLIDAR_PORT = "{best_config['port']}"
RPLIDAR_BAUD = {best_config['baudrate']}

def test_rplidar():
    """Test RPLIDAR with verified working configuration"""
    try:
        from rplidar import RPLidar
    except ImportError:
        print("❌ RPLidar library not installed")
        print("Install with: pip install rplidar-roboticia")
        return False
    
    print(f"🔍 Testing RPLIDAR with verified configuration:")
    print(f"   Port: {{RPLIDAR_PORT}}")
    print(f"   Baudrate: {{RPLIDAR_BAUD:,}}")
    
    try:
        # Connect with verified settings
        lidar = RPLidar(RPLIDAR_PORT, baudrate=RPLIDAR_BAUD, timeout=2)
        
        # Get device info
        print("\\n📋 Device Information:")
        info = lidar.get_info()
        print(f"   Model: {{info.model}}")
        print(f"   Firmware: {{info.firmware}}")
        print(f"   Hardware: {{info.hardware}}")
        print(f"   Serial: {{info.serial}}")
        
        # Check health
        health = lidar.get_health()
        print(f"\\n🏥 Health Status: {{health.status}} (0=Good)")
        if health.status != 0:
            print(f"   Error Code: {{health.error_code}}")
        
        # Start motor and scan
        print("\\n🔄 Starting motor...")
        lidar.start_motor()
        time.sleep(2)
        
        print("📡 Starting scan (collecting 5 scans)...")
        scan_count = 0
        total_points = 0
        
        for scan in lidar.iter_scans(max_buf_meas=5000):
            scan_count += 1
            points_in_scan = len(scan)
            total_points += points_in_scan
            
            # Show sample points
            valid_points = [(angle, dist) for _, angle, dist in scan if dist > 0]
            print(f"   Scan {{scan_count}}: {{points_in_scan}} total points, {{len(valid_points)}} valid points")
            
            if valid_points and len(valid_points) >= 5:
                print("   Sample points (angle, distance):")
                for i in range(min(5, len(valid_points))):
                    angle, dist = valid_points[i]
                    print(f"     {{angle:6.1f}}° {{dist:8.1f}}mm")
            
            if scan_count >= 5:
                break
        
        print(f"\\n✅ Test completed successfully!")
        print(f"   Total scans: {{scan_count}}")
        print(f"   Total points: {{total_points}}")
        print(f"   Average points per scan: {{total_points / scan_count:.1f}}")
        
        # Stop motor
        lidar.stop_motor()
        lidar.disconnect()
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {{e}}")
        return False

if __name__ == "__main__":
    success = test_rplidar()
    sys.exit(0 if success else 1)
'''
        
        test_file = "rplidar_verified_test.py"
        with open(test_file, 'w') as f:
            f.write(test_script)
        
        os.chmod(test_file, 0o755)  # Make executable
        
        print(f"🧪 Generated test script: {test_file}")
        print("   Run with: python rplidar_verified_test.py")
    
    def run_analysis(self):
        """Run complete analysis"""
        if not self.load_results():
            return False
        
        self.analyze_results()
        self.print_summary()
        self.print_working_configs()
        self.print_partial_configs()
        self.print_troubleshooting()
        
        if self.working_configs:
            self.generate_python_config()
            self.create_test_script()
        
        return True

def main():
    """Main entry point"""
    analyzer = RPLidarResultsAnalyzer()
    
    if len(sys.argv) > 1:
        analyzer.results_file = sys.argv[1]
    
    success = analyzer.run_analysis()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
