#!/bin/bash
# RPLIDAR S3 Data Capture Script for Linux/Raspberry Pi
# This script provides easy-to-use wrappers for capturing data with the RPLIDAR S3

set -e  # Exit on any error

# Default configuration
APP="ultra_simple"
DEVICE="/dev/ttyUSB0"
BAUD_RATE=1000000  # Default for S3
OUTPUT_FILE=""
DURATION=0  # 0 = continuous, >0 = seconds to capture
LIST_PORTS=false
SHOW_HELP=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--app)
            APP="$2"
            shift 2
            ;;
        -d|--device)
            DEVICE="$2"
            shift 2
            ;;
        -b|--baudrate)
            BAUD_RATE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -t|--duration)
            DURATION="$2"
            shift 2
            ;;
        -l|--list-ports)
            LIST_PORTS=true
            shift
            ;;
        -h|--help)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            SHOW_HELP=true
            shift
            ;;
    esac
done

show_help() {
    echo -e "${CYAN}🔍 RPLIDAR S3 Data Capture Script for Linux/Raspberry Pi${NC}"
    echo -e "${CYAN}==========================================================${NC}"
    echo ""
    echo -e "${YELLOW}USAGE:${NC}"
    echo "  ./rplidar_s3_capture_linux.sh [OPTIONS]"
    echo ""
    echo -e "${YELLOW}OPTIONS:${NC}"
    echo "  -a, --app <app>          Application to use (ultra_simple, simple_grabber) [default: ultra_simple]"
    echo "  -d, --device <device>    Serial device (e.g., /dev/ttyUSB0) [default: /dev/ttyUSB0]"
    echo "  -b, --baudrate <rate>    Baud rate for S3 [default: 1000000]"
    echo "  -o, --output <file>      Save output to file (optional)"
    echo "  -t, --duration <sec>     Capture duration in seconds (0 = continuous) [default: 0]"
    echo "  -l, --list-ports         List available serial devices"
    echo "  -h, --help               Show this help message"
    echo ""
    echo -e "${YELLOW}EXAMPLES:${NC}"
    echo "  # Basic capture with ultra_simple"
    echo "  ./rplidar_s3_capture_linux.sh --device /dev/ttyUSB0"
    echo ""
    echo "  # Capture with simple_grabber and save to file"
    echo "  ./rplidar_s3_capture_linux.sh -a simple_grabber -d /dev/ttyUSB0 -o lidar_data.txt"
    echo ""
    echo "  # Capture for 30 seconds"
    echo "  ./rplidar_s3_capture_linux.sh -t 30 -o short_capture.txt"
    echo ""
    echo "  # List available serial devices"
    echo "  ./rplidar_s3_capture_linux.sh --list-ports"
    echo ""
    echo -e "${CYAN}RPLIDAR S3 SPECIFICATIONS:${NC}"
    echo "  • Baud Rate: 1,000,000 bps"
    echo "  • Range: 0.2m - 25m"
    echo "  • Sample Rate: 15.5K Hz"
    echo "  • Resolution: 0.25°"
    echo ""
    echo -e "${YELLOW}RASPBERRY PI SETUP:${NC}"
    echo "  1. Add user to dialout group:"
    echo "     sudo usermod -a -G dialout \$USER"
    echo "  2. Logout and login again"
    echo "  3. Check device permissions:"
    echo "     ls -la /dev/ttyUSB* /dev/ttyACM*"
    echo ""
}

list_serial_ports() {
    echo -e "${CYAN}📡 Available Serial Devices:${NC}"
    
    # Check for USB serial devices
    if ls /dev/ttyUSB* 1> /dev/null 2>&1; then
        for device in /dev/ttyUSB*; do
            if [ -c "$device" ]; then
                echo -e "  ${GREEN}✅ $device (USB Serial)${NC}"
            fi
        done
    fi
    
    # Check for ACM devices (common for some USB-serial adapters)
    if ls /dev/ttyACM* 1> /dev/null 2>&1; then
        for device in /dev/ttyACM*; do
            if [ -c "$device" ]; then
                echo -e "  ${GREEN}✅ $device (ACM Serial)${NC}"
            fi
        done
    fi
    
    # Check for built-in serial devices
    if ls /dev/ttyS* 1> /dev/null 2>&1; then
        for device in /dev/ttyS*; do
            if [ -c "$device" ]; then
                echo -e "  ${GRAY}📍 $device (Built-in Serial)${NC}"
            fi
        done
    fi
    
    echo ""
    echo -e "${YELLOW}💡 TIPS:${NC}"
    echo -e "${GRAY}   • Most USB-Serial devices appear as /dev/ttyUSB0, /dev/ttyUSB1, etc.${NC}"
    echo -e "${GRAY}   • Some appear as /dev/ttyACM0, /dev/ttyACM1, etc.${NC}"
    echo -e "${GRAY}   • Check dmesg after plugging in: sudo dmesg | tail${NC}"
    echo -e "${GRAY}   • Ensure user is in dialout group for permissions${NC}"
}

if [ "$SHOW_HELP" = true ]; then
    show_help
    exit 0
fi

if [ "$LIST_PORTS" = true ]; then
    list_serial_ports
    exit 0
fi

# Validate app selection
if [[ "$APP" != "ultra_simple" && "$APP" != "simple_grabber" ]]; then
    echo -e "${RED}❌ Invalid app: $APP${NC}"
    echo -e "${YELLOW}   Valid options: ultra_simple, simple_grabber${NC}"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RPLIDAR_SDK_ROOT="$PROJECT_ROOT/rplidar_sdk_dev"
EXE_DIR="$RPLIDAR_SDK_ROOT/output/Linux/Release"

echo -e "${CYAN}🔍 RPLIDAR S3 Data Capture${NC}"
echo -e "${CYAN}==========================${NC}"
echo -e "${YELLOW}Application: $APP${NC}"
echo -e "${YELLOW}Device: $DEVICE${NC}"
echo -e "${YELLOW}Baud Rate: $BAUD_RATE${NC}"

# Check if executables exist
APP_EXE="$EXE_DIR/$APP"
if [ ! -f "$APP_EXE" ]; then
    echo ""
    echo -e "${RED}❌ Application not found: $APP_EXE${NC}"
    echo -e "${YELLOW}   Please run the build script first:${NC}"
    echo -e "${GRAY}   ./scripts/rplidar_build_linux.sh${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Found application: $APP_EXE${NC}"

# Check if device exists and is accessible
if [ ! -c "$DEVICE" ]; then
    echo ""
    echo -e "${RED}❌ Device not found or not a character device: $DEVICE${NC}"
    echo -e "${YELLOW}   Available devices:${NC}"
    list_serial_ports
    exit 1
fi

# Check device permissions
if [ ! -r "$DEVICE" ] || [ ! -w "$DEVICE" ]; then
    echo ""
    echo -e "${RED}❌ No permission to access $DEVICE${NC}"
    echo -e "${YELLOW}   Try these solutions:${NC}"
    echo -e "${GRAY}   1. Add user to dialout group: sudo usermod -a -G dialout \$USER${NC}"
    echo -e "${GRAY}   2. Logout and login again${NC}"
    echo -e "${GRAY}   3. Or run with sudo (not recommended)${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Device accessible: $DEVICE${NC}"

# Validate baud rate for S3
if [ "$BAUD_RATE" -ne 1000000 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  WARNING: RPLIDAR S3 typically uses 1,000,000 baud rate${NC}"
    echo -e "${YELLOW}   You specified: $BAUD_RATE${NC}"
    read -p "   Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}   Aborted by user${NC}"
        exit 1
    fi
fi

# Prepare command arguments
APP_ARGS=(
    "--channel"
    "--serial"
    "$DEVICE"
    "$BAUD_RATE"
)

echo ""
echo -e "${GREEN}🚀 Starting data capture...${NC}"
echo -e "${GRAY}   Command: $APP_EXE ${APP_ARGS[*]}${NC}"

if [ -n "$OUTPUT_FILE" ]; then
    echo -e "${GRAY}   Output file: $OUTPUT_FILE${NC}"
fi

if [ "$DURATION" -gt 0 ]; then
    echo -e "${GRAY}   Duration: $DURATION seconds${NC}"
fi

echo ""
echo -e "${CYAN}💡 TIPS:${NC}"
echo -e "${GRAY}   • Press Ctrl+C to stop capture${NC}"
echo -e "${GRAY}   • Make sure RPLIDAR is connected and powered${NC}"
echo -e "${GRAY}   • For S3: Ensure 5V power supply is adequate (>2A recommended)${NC}"
echo -e "${GRAY}   • Check dmesg if device issues: sudo dmesg | tail${NC}"
echo ""

# Create output directory if needed
if [ -n "$OUTPUT_FILE" ]; then
    output_dir=$(dirname "$OUTPUT_FILE")
    if [ "$output_dir" != "." ] && [ ! -d "$output_dir" ]; then
        mkdir -p "$output_dir"
        echo -e "${GREEN}✅ Created output directory: $output_dir${NC}"
    fi
fi

# Execute the application
if [ -n "$OUTPUT_FILE" ]; then
    if [ "$DURATION" -gt 0 ]; then
        # Capture for specific duration with output file
        echo -e "${YELLOW}📊 Capturing data for $DURATION seconds...${NC}"
        timeout "$DURATION" "$APP_EXE" "${APP_ARGS[@]}" > "$OUTPUT_FILE" 2>&1 || true
        echo -e "${GREEN}✅ Capture completed after $DURATION seconds${NC}"
        echo -e "${GREEN}📁 Data saved to: $OUTPUT_FILE${NC}"
        
        # Show file size
        if [ -f "$OUTPUT_FILE" ]; then
            file_size=$(du -h "$OUTPUT_FILE" | cut -f1)
            echo -e "${GRAY}   File size: $file_size${NC}"
        fi
    else
        # Continuous capture with output file
        echo -e "${YELLOW}📊 Capturing data continuously (Ctrl+C to stop)...${NC}"
        "$APP_EXE" "${APP_ARGS[@]}" | tee "$OUTPUT_FILE"
    fi
else
    if [ "$DURATION" -gt 0 ]; then
        # Capture for specific duration without output file
        echo -e "${YELLOW}📊 Capturing data for $DURATION seconds...${NC}"
        timeout "$DURATION" "$APP_EXE" "${APP_ARGS[@]}" || true
        echo -e "${GREEN}✅ Capture completed after $DURATION seconds${NC}"
    else
        # Continuous capture without output file
        echo -e "${YELLOW}📊 Capturing data continuously (Ctrl+C to stop)...${NC}"
        "$APP_EXE" "${APP_ARGS[@]}"
    fi
fi

echo ""
echo -e "${GREEN}🏁 Data capture session ended${NC}"
