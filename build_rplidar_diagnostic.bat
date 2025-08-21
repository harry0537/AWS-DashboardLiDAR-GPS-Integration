@echo off
REM Build script for RPLIDAR C++ diagnostic tool on Windows

echo 🔨 Building RPLIDAR C++ Diagnostic Tool for Windows...

REM Check if g++ is available
g++ --version >nul 2>&1
if errorlevel 1 (
    echo ❌ g++ not found! Please install MinGW-w64 or MSYS2
    echo 💡 Download from: https://www.mingw-w64.org/downloads/
    echo    Or install with chocolatey: choco install mingw
    pause
    exit /b 1
)

echo 📍 Building for Windows...
g++ -std=c++11 -O2 -o rplidar_cpp_diagnostic.exe rplidar_cpp_diagnostic.cpp

if errorlevel 1 (
    echo ❌ Build failed!
    echo 💡 Make sure you have a C++ compiler installed
    pause
    exit /b 1
)

echo ✅ Build successful!
echo 📝 Run with: rplidar_cpp_diagnostic.exe
echo.
echo 🎯 Next steps:
echo 1. Run the diagnostic: rplidar_cpp_diagnostic.exe
echo 2. Analyze results: python rplidar_results_analyzer.py
echo 3. Use generated config in your Python scripts
echo.
pause
