#!/bin/bash
# Build script for custom RPLIDAR S3 application

echo "🔧 Building Custom RPLIDAR S3 Application"
echo "========================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SDK_ROOT="$PROJECT_ROOT/rplidar_sdk_dev"

# Check if SDK exists
if [ ! -d "$SDK_ROOT" ]; then
    echo "❌ RPLIDAR SDK not found at: $SDK_ROOT"
    echo "   Please ensure the SDK is properly linked."
    exit 1
fi

echo "✅ SDK found at: $SDK_ROOT"

# Build the SDK first
echo "🔨 Building RPLIDAR SDK..."
cd "$SDK_ROOT"
make

if [ $? -ne 0 ]; then
    echo "❌ Failed to build RPLIDAR SDK"
    exit 1
fi

echo "✅ SDK built successfully"

# Build our custom application
echo "🔨 Building custom S3 application..."
cd "$SCRIPT_DIR"

# Compile the custom application
g++ -o rplidar_s3_custom \
    rplidar_s3_custom.cpp \
    -I"$SDK_ROOT/sdk/include" \
    -L"$SDK_ROOT/output/Linux/Release" \
    -lsl_lidar_sdk \
    -lpthread \
    -std=c++11

if [ $? -eq 0 ]; then
    echo "✅ Custom S3 application built successfully!"
    echo "📁 Executable: $SCRIPT_DIR/rplidar_s3_custom"
    echo ""
    echo "🚀 To run:"
    echo "   cd $SCRIPT_DIR"
    echo "   ./rplidar_s3_custom"
    echo ""
    echo "⚠️ Make sure your RPLIDAR S3 is connected with adequate power (5V, >2A)"
else
    echo "❌ Failed to build custom application"
    exit 1
fi
