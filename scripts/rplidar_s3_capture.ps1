# RPLIDAR S3 Data Capture Script
# This script provides easy-to-use wrappers for capturing data with the RPLIDAR S3

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("ultra_simple", "simple_grabber")]
    [string]$App = "ultra_simple",
    
    [Parameter(Mandatory=$false)]
    [string]$COMPort = "COM4",
    
    [Parameter(Mandatory=$false)]
    [int]$BaudRate = 1000000,  # Default for S3
    
    [Parameter(Mandatory=$false)]
    [string]$OutputFile = "",
    
    [Parameter(Mandatory=$false)]
    [int]$Duration = 0,  # 0 = continuous, >0 = seconds to capture
    
    [Parameter(Mandatory=$false)]
    [switch]$ListPorts,
    
    [Parameter(Mandatory=$false)]
    [switch]$Help
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $ScriptDir
$RPLidarSDKRoot = Join-Path $ProjectRoot "rplidar_sdk_dev"
$ExeDir = Join-Path $RPLidarSDKRoot "output\win32\Release"

function Show-Help {
    Write-Host "🔍 RPLIDAR S3 Data Capture Script" -ForegroundColor Cyan
    Write-Host "=================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "USAGE:" -ForegroundColor Yellow
    Write-Host "  .\rplidar_s3_capture.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "OPTIONS:" -ForegroundColor Yellow
    Write-Host "  -App <app>          Application to use (ultra_simple, simple_grabber) [default: ultra_simple]"
    Write-Host "  -COMPort <port>     Serial port (e.g., COM4) [default: COM4]"
    Write-Host "  -BaudRate <rate>    Baud rate for S3 [default: 1000000]"
    Write-Host "  -OutputFile <file>  Save output to file (optional)"
    Write-Host "  -Duration <sec>     Capture duration in seconds (0 = continuous) [default: 0]"
    Write-Host "  -ListPorts          List available COM ports"
    Write-Host "  -Help               Show this help message"
    Write-Host ""
    Write-Host "EXAMPLES:" -ForegroundColor Yellow
    Write-Host "  # Basic capture with ultra_simple"
    Write-Host "  .\rplidar_s3_capture.ps1 -COMPort COM4"
    Write-Host ""
    Write-Host "  # Capture with simple_grabber and save to file"
    Write-Host "  .\rplidar_s3_capture.ps1 -App simple_grabber -COMPort COM4 -OutputFile lidar_data.txt"
    Write-Host ""
    Write-Host "  # Capture for 30 seconds"
    Write-Host "  .\rplidar_s3_capture.ps1 -Duration 30 -OutputFile short_capture.txt"
    Write-Host ""
    Write-Host "  # List available COM ports"
    Write-Host "  .\rplidar_s3_capture.ps1 -ListPorts"
    Write-Host ""
    Write-Host "RPLIDAR S3 SPECIFICATIONS:" -ForegroundColor Cyan
    Write-Host "  • Baud Rate: 1,000,000 bps"
    Write-Host "  • Range: 0.2m - 25m"
    Write-Host "  • Sample Rate: 15.5K Hz"
    Write-Host "  • Resolution: 0.25°"
    Write-Host ""
}

function Get-COMPorts {
    Write-Host "📡 Available COM Ports:" -ForegroundColor Cyan
    $ports = Get-WmiObject -Class Win32_SerialPort | Select-Object DeviceID, Description, PNPDeviceID
    
    if ($ports) {
        foreach ($port in $ports) {
            $deviceInfo = ""
            if ($port.Description -match "USB.*Serial|UART|CP210") {
                $deviceInfo = " (Likely USB-Serial)"
            }
            Write-Host "  ✅ $($port.DeviceID) - $($port.Description)$deviceInfo" -ForegroundColor Green
        }
    } else {
        Write-Host "  ❌ No COM ports found" -ForegroundColor Red
    }
    
    # Also check for ports in use
    Write-Host ""
    Write-Host "💡 TIP: Common RPLIDAR ports are usually COM3, COM4, COM5, etc." -ForegroundColor Yellow
    Write-Host "       If your RPLIDAR doesn't appear, check Device Manager." -ForegroundColor Yellow
}

if ($Help) {
    Show-Help
    exit 0
}

if ($ListPorts) {
    Get-COMPorts
    exit 0
}

Write-Host "🔍 RPLIDAR S3 Data Capture" -ForegroundColor Cyan
Write-Host "==========================" -ForegroundColor Cyan
Write-Host "Application: $App" -ForegroundColor Yellow
Write-Host "COM Port: $COMPort" -ForegroundColor Yellow
Write-Host "Baud Rate: $BaudRate" -ForegroundColor Yellow

# Check if executables exist
$AppExe = Join-Path $ExeDir "$App.exe"
if (-not (Test-Path $AppExe)) {
    Write-Host ""
    Write-Host "❌ Application not found: $AppExe" -ForegroundColor Red
    Write-Host "   Please run the build script first:" -ForegroundColor Yellow
    Write-Host "   .\scripts\rplidar_build.ps1" -ForegroundColor Gray
    exit 1
}

Write-Host "✅ Found application: $AppExe" -ForegroundColor Green

# Validate baud rate for S3
if ($BaudRate -ne 1000000) {
    Write-Host ""
    Write-Host "⚠️  WARNING: RPLIDAR S3 typically uses 1,000,000 baud rate" -ForegroundColor Yellow
    Write-Host "   You specified: $BaudRate" -ForegroundColor Yellow
    Write-Host "   Continue anyway? (Y/N): " -NoNewline -ForegroundColor Yellow
    $continue = Read-Host
    if ($continue -notmatch "^[Yy]") {
        Write-Host "   Aborted by user" -ForegroundColor Red
        exit 1
    }
}

# Prepare command arguments
$AppArgs = @(
    "--channel"
    "--serial"
    $COMPort
    $BaudRate.ToString()
)

Write-Host ""
Write-Host "🚀 Starting data capture..." -ForegroundColor Green
Write-Host "   Command: $AppExe $($AppArgs -join ' ')" -ForegroundColor Gray

if ($OutputFile) {
    Write-Host "   Output file: $OutputFile" -ForegroundColor Gray
}

if ($Duration -gt 0) {
    Write-Host "   Duration: $Duration seconds" -ForegroundColor Gray
}

Write-Host ""
Write-Host "💡 TIPS:" -ForegroundColor Cyan
Write-Host "   • Press Ctrl+C to stop capture" -ForegroundColor Gray
Write-Host "   • Make sure RPLIDAR is connected and powered" -ForegroundColor Gray
Write-Host "   • For S3: Ensure 5V power supply is adequate" -ForegroundColor Gray
Write-Host ""

# Execute the application
try {
    if ($OutputFile) {
        if ($Duration -gt 0) {
            # Capture for specific duration with output file
            $process = Start-Process -FilePath $AppExe -ArgumentList $AppArgs -NoNewWindow -PassThru -RedirectStandardOutput $OutputFile
            Start-Sleep -Seconds $Duration
            $process.Kill()
            Write-Host "✅ Capture completed after $Duration seconds" -ForegroundColor Green
            Write-Host "📁 Data saved to: $OutputFile" -ForegroundColor Green
        } else {
            # Continuous capture with output file
            & $AppExe $AppArgs | Tee-Object -FilePath $OutputFile
        }
    } else {
        if ($Duration -gt 0) {
            # Capture for specific duration without output file
            $process = Start-Process -FilePath $AppExe -ArgumentList $AppArgs -NoNewWindow -PassThru
            Start-Sleep -Seconds $Duration
            $process.Kill()
            Write-Host "✅ Capture completed after $Duration seconds" -ForegroundColor Green
        } else {
            # Continuous capture without output file
            & $AppExe $AppArgs
        }
    }
} catch {
    Write-Host ""
    Write-Host "❌ Error running application: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🏁 Data capture session ended" -ForegroundColor Green
