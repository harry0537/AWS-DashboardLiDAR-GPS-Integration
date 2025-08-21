#!/bin/bash
# Build script for RPLIDAR C++ diagnostic tool

echo "🔨 Building RPLIDAR C++ Diagnostic Tool..."

# Check if we're on Linux or need to cross-compile for Windows
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "📍 Building for Linux..."
    g++ -std=c++11 -O2 -o rplidar_cpp_diagnostic rplidar_cpp_diagnostic.cpp
    
    if [ $? -eq 0 ]; then
        echo "✅ Build successful!"
        echo "📝 Run with: ./rplidar_cpp_diagnostic"
        chmod +x rplidar_cpp_diagnostic
    else
        echo "❌ Build failed!"
        exit 1
    fi
    
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    echo "📍 Building for Windows..."
    g++ -std=c++11 -O2 -o rplidar_cpp_diagnostic.exe rplidar_cpp_diagnostic.cpp
    
    if [ $? -eq 0 ]; then
        echo "✅ Build successful!"
        echo "📝 Run with: ./rplidar_cpp_diagnostic.exe"
    else
        echo "❌ Build failed!"
        exit 1
    fi
    
else
    echo "❓ Unknown OS type: $OSTYPE"
    echo "🔧 Trying generic build..."
    g++ -std=c++11 -O2 -o rplidar_cpp_diagnostic rplidar_cpp_diagnostic.cpp
    
    if [ $? -eq 0 ]; then
        echo "✅ Build successful!"
        echo "📝 Run with: ./rplidar_cpp_diagnostic"
        chmod +x rplidar_cpp_diagnostic 2>/dev/null || true
    else
        echo "❌ Build failed!"
        echo "💡 Try manual compilation:"
        echo "   g++ -std=c++11 -O2 -o rplidar_cpp_diagnostic rplidar_cpp_diagnostic.cpp"
        exit 1
    fi
fi

echo ""
echo "🎯 Next steps:"
echo "1. Run the diagnostic: ./rplidar_cpp_diagnostic"
echo "2. Analyze results: python rplidar_results_analyzer.py"
echo "3. Use generated config in your Python scripts"
