#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <string.h>
#include <unistd.h>

#include "sl_lidar.h" 
#include "sl_lidar_driver.h"

using namespace sl;

bool ctrl_c_pressed = false;
void ctrlc(int)
{
    ctrl_c_pressed = true;
}

int main(int argc, char* argv[])
{
    printf("🔍 Custom RPLIDAR S3 Application\n");
    printf("===============================\n");
    
    // Create a communication channel instance for S3 (1M baud rate)
    IChannel* _channel;
    auto channel_result = createSerialPortChannel("/dev/ttyUSB0", 1000000);
    if (!channel_result) {
        fprintf(stderr, "❌ Failed to create serial channel\n");
        return -1;
    }
    _channel = *channel_result;
    
    // Create a LIDAR driver instance
    ILidarDriver * lidar = *createLidarDriver();
    if (!lidar) {
        fprintf(stderr, "❌ Failed to create LIDAR driver\n");
        delete _channel;
        return -2;
    }
    
    // Connect to the LIDAR
    printf("🔌 Connecting to RPLIDAR S3...\n");
    sl_result res = lidar->connect(_channel);
    if (SL_IS_FAIL(res)) {
        fprintf(stderr, "❌ Failed to connect to LIDAR. Error: %08x\n", res);
        delete lidar;
        delete _channel;
        return -3;
    }
    
    printf("✅ Connected successfully!\n");
    
    // Get device information
    sl_lidar_response_device_info_t deviceInfo;
    res = lidar->getDeviceInfo(deviceInfo);
    if (SL_IS_OK(res)) {
        printf("\n📋 RPLIDAR S3 Information:\n");
        printf("   Model: %d\n", deviceInfo.model);
        printf("   Firmware Version: %d.%02d\n", 
               deviceInfo.firmware_version >> 8, 
               deviceInfo.firmware_version & 0xFF);
        printf("   Hardware Version: %d\n", deviceInfo.hardware_version);
        
        // Print serial number
        printf("   Serial Number: ");
        for (int i = 0; i < 16; i++) {
            printf("%02X", deviceInfo.serialnum[i]);
        }
        printf("\n");
    } else {
        fprintf(stderr, "❌ Failed to get device information. Error: %08x\n", res);
    }
    
    // Check health status
    sl_lidar_response_device_health_t healthInfo;
    res = lidar->getHealth(healthInfo);
    if (SL_IS_OK(res)) {
        printf("   Health Status: ");
        switch (healthInfo.status) {
            case SL_LIDAR_STATUS_OK:
                printf("✅ OK");
                break;
            case SL_LIDAR_STATUS_WARNING:
                printf("⚠️ Warning");
                break;
            case SL_LIDAR_STATUS_ERROR:
                printf("❌ Error");
                break;
            default:
                printf("❓ Unknown");
                break;
        }
        printf(" (Error code: %d)\n", healthInfo.error_code);
        
        if (healthInfo.status == SL_LIDAR_STATUS_ERROR) {
            fprintf(stderr, "❌ LIDAR reports error status. Please check power and connections.\n");
            goto cleanup;
        }
    } else {
        fprintf(stderr, "❌ Failed to get health status. Error: %08x\n", res);
    }
    
    // Start the motor (critical for S3)
    printf("\n🚀 Starting motor...\n");
    res = lidar->setMotorSpeed();
    if (SL_IS_FAIL(res)) {
        fprintf(stderr, "❌ Failed to start motor. Error: %08x\n", res);
        goto cleanup;
    }
    
    // Wait for motor to spin up
    printf("⏳ Waiting for motor to spin up...\n");
    sleep(3);
    
    // Get supported scan modes
    std::vector<LidarScanMode> scanModes;
    res = lidar->getAllSupportedScanModes(scanModes);
    if (SL_IS_OK(res) && !scanModes.empty()) {
        printf("📊 Available scan modes:\n");
        for (size_t i = 0; i < scanModes.size(); i++) {
            printf("   Mode %zu: %s (max_distance: %.1fm, ans_type: %d)\n", 
                   i, scanModes[i].scan_mode, 
                   scanModes[i].max_distance, 
                   scanModes[i].ans_type);
        }
        
        // Start scanning with the first available mode (usually highest performance)
        printf("\n🔄 Starting scan mode: %s\n", scanModes[0].scan_mode);
        res = lidar->startScanExpress(false, scanModes[0].id);
    } else {
        // Fallback to standard scan mode
        printf("\n🔄 Starting standard scan mode...\n");
        res = lidar->startScan(false, true);
    }
    
    if (SL_IS_FAIL(res)) {
        fprintf(stderr, "❌ Failed to start scan. Error: %08x\n", res);
        goto cleanup;
    }
    
    printf("✅ Scanning started successfully!\n");
    printf("📡 Real-time scan data (Press Ctrl+C to stop):\n");
    printf("   Format: [Angle°] [Distance mm] [Quality]\n\n");
    
    // Set up Ctrl+C handler
    signal(SIGINT, ctrlc);
    
    // Main scanning loop
    int scan_count = 0;
    while (!ctrl_c_pressed) {
        sl_lidar_response_measurement_node_hq_t nodes[8192];
        size_t count = sizeof(nodes) / sizeof(sl_lidar_response_measurement_node_hq_t);
        
        res = lidar->grabScanDataHq(nodes, count);
        if (SL_IS_OK(res) || res == SL_RESULT_OPERATION_TIMEOUT) {
            lidar->ascendScanData(nodes, count);
            
            scan_count++;
            if (scan_count % 10 == 1) {  // Print every 10th scan to avoid spam
                printf("📊 Scan %d - %zu points:\n", scan_count, count);
                
                // Show first 10 points of each scan
                for (size_t i = 0; i < count && i < 10; i++) {
                    float angle = (nodes[i].angle_z_q14 * 90.f) / 16384.f;
                    float distance = nodes[i].dist_mm_q2 / 4.f;
                    int quality = nodes[i].quality >> SL_LIDAR_RESP_MEASUREMENT_QUALITY_SHIFT;
                    
                    printf("   %s[%06.2f°] [%08.1f mm] [Q:%02d]\n",
                           (nodes[i].flag & SL_LIDAR_RESP_HQ_FLAG_SYNCBIT) ? "🔄 " : "   ",
                           angle, distance, quality);
                }
                printf("\n");
            }
        } else {
            fprintf(stderr, "❌ Failed to grab scan data. Error: %08x\n", res);
            break;
        }
        
        usleep(100000);  // 100ms delay
    }
    
cleanup:
    printf("\n🛑 Stopping scan...\n");
    lidar->stop();
    
    printf("🛑 Stopping motor...\n");
    lidar->setMotorSpeed(0);
    
    // Cleanup
    if (lidar) {
        delete lidar;
        lidar = NULL;
    }
    if (_channel) {
        delete _channel;
        _channel = NULL;
    }
    
    printf("🏁 Application ended.\n");
    return 0;
}
