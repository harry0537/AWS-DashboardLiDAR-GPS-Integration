# RPLIDAR S3 Build Script for Windows
# This script builds the simple_grabber and ultra_simple applications for the RPLIDAR S3

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Release",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Win32", "x64")]
    [string]$Platform = "Win32",
    
    [Parameter(Mandatory=$false)]
    [switch]$Clean,
    
    [Parameter(Mandatory=$false)]
    [switch]$Rebuild
)

# Script configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $ScriptDir
$RPLidarSDKRoot = Join-Path $ProjectRoot "rplidar_sdk_dev"
$WorkspaceDir = Join-Path $RPLidarSDKRoot "workspaces\vc14"
$SolutionFile = Join-Path $WorkspaceDir "sdk_and_demo.sln"
$OutputDir = Join-Path $RPLidarSDKRoot "output\win32\$Configuration"

Write-Host "🔧 RPLIDAR S3 Build Script" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Configuration: $Configuration" -ForegroundColor Yellow
Write-Host "Platform: $Platform" -ForegroundColor Yellow
Write-Host "SDK Root: $RPLidarSDKRoot" -ForegroundColor Gray
Write-Host "Output Directory: $OutputDir" -ForegroundColor Gray
Write-Host ""

# Check if Visual Studio or MSBuild is available
$MSBuildPath = $null

# Try to find MSBuild (Visual Studio 2019/2022)
$VSInstallPath = ""
if (Get-Command "vswhere.exe" -ErrorAction SilentlyContinue) {
    $VSInstallPath = & vswhere.exe -latest -property installationPath
    if ($VSInstallPath) {
        $MSBuildPath = Join-Path $VSInstallPath "MSBuild\Current\Bin\MSBuild.exe"
        if (-not (Test-Path $MSBuildPath)) {
            $MSBuildPath = Join-Path $VSInstallPath "MSBuild\15.0\Bin\MSBuild.exe"
        }
    }
}

# Fallback: try to find MSBuild in standard locations
if (-not $MSBuildPath -or -not (Test-Path $MSBuildPath)) {
    $MSBuildPaths = @(
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\*\MSBuild\Current\Bin\MSBuild.exe",
        "${env:ProgramFiles}\Microsoft Visual Studio\2019\*\MSBuild\Current\Bin\MSBuild.exe",
        "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2019\*\MSBuild\Current\Bin\MSBuild.exe",
        "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022\*\MSBuild\Current\Bin\MSBuild.exe",
        "${env:ProgramFiles(x86)}\MSBuild\14.0\Bin\MSBuild.exe"
    )
    
    foreach ($path in $MSBuildPaths) {
        $foundPaths = Get-ChildItem $path -ErrorAction SilentlyContinue
        if ($foundPaths) {
            $MSBuildPath = $foundPaths[0].FullName
            break
        }
    }
}

if (-not $MSBuildPath -or -not (Test-Path $MSBuildPath)) {
    Write-Host "❌ MSBuild not found! Please install Visual Studio 2019 or later." -ForegroundColor Red
    Write-Host "   Alternatively, install Visual Studio Build Tools." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Found MSBuild: $MSBuildPath" -ForegroundColor Green

# Check if solution file exists
if (-not (Test-Path $SolutionFile)) {
    Write-Host "❌ Solution file not found: $SolutionFile" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Found solution file: $SolutionFile" -ForegroundColor Green

# Prepare build arguments
$BuildArgs = @(
    $SolutionFile
    "/p:Configuration=$Configuration"
    "/p:Platform=$Platform"
    "/p:PlatformToolset=v142"
    "/p:WindowsTargetPlatformVersion=10.0"
    "/m"  # Build in parallel
    "/v:minimal"  # Minimal verbosity
)

if ($Clean -or $Rebuild) {
    Write-Host "🧹 Cleaning previous build..." -ForegroundColor Yellow
    $CleanArgs = $BuildArgs + @("/t:Clean")
    & $MSBuildPath $CleanArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Clean failed with exit code $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    Write-Host "✅ Clean completed successfully" -ForegroundColor Green
}

if (-not $Clean) {
    Write-Host "🔨 Building RPLIDAR SDK and applications..." -ForegroundColor Yellow
    $BuildArgs += @("/t:Build")
    
    & $MSBuildPath $BuildArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Build failed with exit code $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    
    Write-Host "✅ Build completed successfully!" -ForegroundColor Green
    
    # List built executables
    Write-Host ""
    Write-Host "📁 Built Applications:" -ForegroundColor Cyan
    
    $BuiltFiles = @(
        "simple_grabber.exe",
        "ultra_simple.exe",
        "frame_grabber.exe",
        "custom_baudrate.exe"
    )
    
    foreach ($file in $BuiltFiles) {
        $filePath = Join-Path $OutputDir $file
        if (Test-Path $filePath) {
            $fileInfo = Get-Item $filePath
            Write-Host "  ✅ $file (Size: $([math]::Round($fileInfo.Length / 1KB, 2)) KB)" -ForegroundColor Green
        } else {
            Write-Host "  ❌ $file (Not found)" -ForegroundColor Red
        }
    }
    
    Write-Host ""
    Write-Host "🎯 Ready to use with RPLIDAR S3!" -ForegroundColor Cyan
    Write-Host "   Baud rate for S3: 1000000" -ForegroundColor Yellow
    Write-Host "   Example usage:" -ForegroundColor Gray
    Write-Host "     $OutputDir\ultra_simple.exe --channel --serial COM4 1000000" -ForegroundColor Gray
    Write-Host "     $OutputDir\simple_grabber.exe --channel --serial COM4 1000000" -ForegroundColor Gray
}

Write-Host ""
Write-Host "🏁 Build script completed!" -ForegroundColor Green
