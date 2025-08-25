#!/bin/bash
# RPLIDAR S3 Build Script for Linux/Raspberry Pi
# This script builds the simple_grabber and ultra_simple applications for the RPLIDAR S3

set -e  # Exit on any error

# Configuration
CONFIGURATION="${1:-Release}"
CLEAN="${2:-false}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RPLIDAR_SDK_ROOT="$PROJECT_ROOT/rplidar_sdk_dev"
OUTPUT_DIR="$RPLIDAR_SDK_ROOT/output/Linux/$CONFIGURATION"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

echo -e "${CYAN}🔧 RPLIDAR S3 Build Script for Linux/Raspberry Pi${NC}"
echo -e "${CYAN}================================================${NC}"
echo -e "${YELLOW}Configuration: $CONFIGURATION${NC}"
echo -e "${YELLOW}SDK Root: $RPLIDAR_SDK_ROOT${NC}"
echo -e "${GRAY}Output Directory: $OUTPUT_DIR${NC}"
echo ""

# Check if we're in the right directory
if [ ! -d "$RPLIDAR_SDK_ROOT" ]; then
    echo -e "${RED}❌ RPLIDAR SDK directory not found: $RPLIDAR_SDK_ROOT${NC}"
    echo -e "${RED}   Please ensure you're running this script from the correct location.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Found RPLIDAR SDK directory${NC}"

# Check for required tools
echo "🔍 Checking build dependencies..."

# Check for make
if ! command -v make &> /dev/null; then
    echo -e "${RED}❌ make not found! Please install build-essential:${NC}"
    echo -e "${YELLOW}   sudo apt update && sudo apt install build-essential${NC}"
    exit 1
fi

# Check for g++
if ! command -v g++ &> /dev/null; then
    echo -e "${RED}❌ g++ not found! Please install build-essential:${NC}"
    echo -e "${YELLOW}   sudo apt update && sudo apt install build-essential${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Found make: $(which make)${NC}"
echo -e "${GREEN}✅ Found g++: $(which g++)${NC}"

# Check for git (helpful for version info)
if command -v git &> /dev/null; then
    echo -e "${GREEN}✅ Found git: $(which git)${NC}"
fi

# Change to SDK directory
cd "$RPLIDAR_SDK_ROOT"

# Clean if requested
if [ "$CLEAN" = "true" ] || [ "$2" = "clean" ]; then
    echo -e "${YELLOW}🧹 Cleaning previous build...${NC}"
    make clean
    echo -e "${GREEN}✅ Clean completed${NC}"
fi

# Set debug flag if needed
MAKE_FLAGS=""
if [ "$CONFIGURATION" = "Debug" ]; then
    MAKE_FLAGS="DEBUG=1"
fi

# Build the SDK and applications
echo -e "${YELLOW}🔨 Building RPLIDAR SDK and applications...${NC}"
echo -e "${GRAY}   Running: make $MAKE_FLAGS${NC}"

if make $MAKE_FLAGS; then
    echo -e "${GREEN}✅ Build completed successfully!${NC}"
else
    echo -e "${RED}❌ Build failed!${NC}"
    exit 1
fi

# List built executables
echo ""
echo -e "${CYAN}📁 Built Applications:${NC}"

BUILT_FILES=(
    "simple_grabber"
    "ultra_simple"
    "frame_grabber"
)

for file in "${BUILT_FILES[@]}"; do
    file_path="$OUTPUT_DIR/$file"
    if [ -f "$file_path" ]; then
        file_size=$(du -h "$file_path" | cut -f1)
        echo -e "  ${GREEN}✅ $file (Size: $file_size)${NC}"
        
        # Make executable
        chmod +x "$file_path"
    else
        echo -e "  ${RED}❌ $file (Not found)${NC}"
    fi
done

# Check if any executables were built
if [ -f "$OUTPUT_DIR/ultra_simple" ] || [ -f "$OUTPUT_DIR/simple_grabber" ]; then
    echo ""
    echo -e "${CYAN}🎯 Ready to use with RPLIDAR S3!${NC}"
    echo -e "${YELLOW}   Baud rate for S3: 1000000${NC}"
    echo -e "${GRAY}   Example usage:${NC}"
    echo -e "${GRAY}     $OUTPUT_DIR/ultra_simple --channel --serial /dev/ttyUSB0 1000000${NC}"
    echo -e "${GRAY}     $OUTPUT_DIR/simple_grabber --channel --serial /dev/ttyUSB0 1000000${NC}"
    echo ""
    echo -e "${YELLOW}💡 RASPBERRY PI TIPS:${NC}"
    echo -e "${GRAY}   • Add user to dialout group: sudo usermod -a -G dialout \$USER${NC}"
    echo -e "${GRAY}   • Then logout and login again${NC}"
    echo -e "${GRAY}   • Check device: ls -la /dev/ttyUSB* or /dev/ttyACM*${NC}"
    echo -e "${GRAY}   • Test connection: sudo dmesg | tail (after plugging in LiDAR)${NC}"
else
    echo -e "${RED}❌ No executables were built successfully${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🏁 Build script completed!${NC}"
