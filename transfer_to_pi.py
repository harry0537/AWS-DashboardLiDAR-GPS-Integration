#!/usr/bin/env python3
"""
Transfer RPLIDAR diagnostic script to Raspberry Pi
Run this from your Windows machine to send the file to your Pi
"""

import os
import subprocess
import sys

def transfer_to_pi():
    """Transfer the diagnostic script to Raspberry Pi"""
    
    # Configuration - UPDATE THESE VALUES
    PI_USERNAME = "artem"  # Your Pi username
    PI_IP = "192.168.1.100"  # Your Pi's IP address
    PI_PATH = "~/AWS-Dashboard"  # Path on Pi
    
    # File to transfer
    local_file = "rplidar_quick_test.py"
    
    if not os.path.exists(local_file):
        print(f"❌ Error: {local_file} not found in current directory")
        print("Make sure you're in the AWS-Dashboard folder")
        return False
    
    print(f"🚀 Transferring {local_file} to Raspberry Pi...")
    print(f"   From: {os.path.abspath(local_file)}")
    print(f"   To: {PI_USERNAME}@{PI_IP}:{PI_PATH}/")
    
    # Build SCP command
    scp_cmd = [
        "scp", 
        local_file, 
        f"{PI_USERNAME}@{PI_IP}:{PI_PATH}/"
    ]
    
    try:
        print(f"\n📡 Running: {' '.join(scp_cmd)}")
        result = subprocess.run(scp_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Transfer successful!")
            print(f"\n🎯 Now on your Raspberry Pi, run:")
            print(f"   cd {PI_PATH}")
            print(f"   python3 {local_file}")
        else:
            print("❌ Transfer failed!")
            print(f"Error: {result.stderr}")
            print(f"\n💡 Troubleshooting:")
            print(f"   1. Check if Pi is accessible: ping {PI_IP}")
            print(f"   2. Verify username: {PI_USERNAME}")
            print(f"   3. Check if directory exists: {PI_PATH}")
            print(f"   4. Try manual SCP: scp {local_file} {PI_USERNAME}@{PI_IP}:{PI_PATH}/")
            
    except FileNotFoundError:
        print("❌ Error: SCP not found!")
        print("💡 Install OpenSSH on Windows or use PuTTY's PSCP")
        print("\nAlternative: Use PuTTY's file transfer feature")
        
    return True

def manual_instructions():
    """Show manual transfer instructions"""
    print("\n📋 MANUAL TRANSFER INSTRUCTIONS:")
    print("=" * 50)
    print("Since SCP might not be available, here are alternatives:")
    print()
    print("Option 1: PuTTY File Transfer")
    print("  1. Open PuTTY and connect to your Pi")
    print("  2. Use PuTTY's file transfer feature (if available)")
    print("  3. Upload rplidar_quick_test.py to ~/AWS-Dashboard/")
    print()
    print("Option 2: Copy-paste content")
    print("  1. On Pi: nano ~/AWS-Dashboard/rplidar_quick_test.py")
    print("  2. Copy the entire content from the file")
    print("  3. Paste and save (Ctrl+X, Y, Enter)")
    print()
    print("Option 3: USB transfer")
    print("  1. Copy file to USB drive")
    print("  2. Mount USB on Pi: sudo mount /dev/sda1 /mnt/usb")
    print("  3. Copy: cp /mnt/usb/rplidar_quick_test.py ~/AWS-Dashboard/")
    print("  4. Unmount: sudo umount /mnt/usb")

if __name__ == "__main__":
    print("🔄 RPLIDAR Diagnostic Transfer Tool")
    print("=" * 40)
    
    # Try automatic transfer first
    if not transfer_to_pi():
        manual_instructions()
    else:
        print("\n🎉 Transfer complete! Check your Pi for the diagnostic script.")
