#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <chrono>
#include <thread>
#include <iomanip>
#include <cstring>

#ifdef _WIN32
#include <windows.h>
#include <setupapi.h>
#pragma comment(lib, "setupapi.lib")
#else
#include <fcntl.h>
#include <termios.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <dirent.h>
#endif

struct RPLidarResponse {
    uint8_t sync_byte1;
    uint8_t sync_byte2;
    uint32_t size_quality;
    uint8_t type;
    uint8_t data[1024];
};

struct TestResult {
    std::string port;
    int baudrate;
    bool raw_communication;
    bool device_info_success;
    bool health_check_success;
    bool scan_start_success;
    int scan_points_received;
    std::string error_message;
    double test_duration_ms;
};

class RPLidarDiagnostic {
private:
#ifdef _WIN32
    HANDLE serial_handle;
#else
    int serial_fd;
#endif
    std::ofstream log_file;
    std::vector<TestResult> results;

public:
    RPLidarDiagnostic() {
#ifdef _WIN32
        serial_handle = INVALID_HANDLE_VALUE;
#else
        serial_fd = -1;
#endif
        log_file.open("rplidar_diagnostic_results.json");
        log_file << "{\n  \"timestamp\": \"" << getCurrentTimeString() << "\",\n";
        log_file << "  \"test_results\": [\n";
    }

    ~RPLidarDiagnostic() {
        closeSerial();
        finalizeLogs();
    }

    std::string getCurrentTimeString() {
        auto now = std::chrono::system_clock::now();
        auto time_t = std::chrono::system_clock::to_time_t(now);
        std::stringstream ss;
        ss << std::put_time(std::localtime(&time_t), "%Y-%m-%d %H:%M:%S");
        return ss.str();
    }

    std::vector<std::string> findSerialPorts() {
        std::vector<std::string> ports;
        
#ifdef _WIN32
        // Windows implementation
        for (int i = 1; i <= 256; ++i) {
            std::string port = "COM" + std::to_string(i);
            HANDLE handle = CreateFileA(port.c_str(), GENERIC_READ | GENERIC_WRITE,
                                      0, NULL, OPEN_EXISTING, 0, NULL);
            if (handle != INVALID_HANDLE_VALUE) {
                ports.push_back(port);
                CloseHandle(handle);
            }
        }
#else
        // Linux implementation
        const char* prefixes[] = {"/dev/ttyUSB", "/dev/ttyACM", "/dev/ttyS"};
        for (const char* prefix : prefixes) {
            for (int i = 0; i < 10; ++i) {
                std::string port = std::string(prefix) + std::to_string(i);
                if (access(port.c_str(), F_OK) == 0) {
                    ports.push_back(port);
                }
            }
        }
#endif
        return ports;
    }

    bool openSerial(const std::string& port, int baudrate) {
        closeSerial();

#ifdef _WIN32
        serial_handle = CreateFileA(port.c_str(),
                                   GENERIC_READ | GENERIC_WRITE,
                                   0, NULL, OPEN_EXISTING,
                                   FILE_ATTRIBUTE_NORMAL, NULL);
        
        if (serial_handle == INVALID_HANDLE_VALUE) {
            return false;
        }

        DCB dcb = {0};
        dcb.DCBlength = sizeof(dcb);
        if (!GetCommState(serial_handle, &dcb)) {
            return false;
        }

        dcb.BaudRate = baudrate;
        dcb.ByteSize = 8;
        dcb.Parity = NOPARITY;
        dcb.StopBits = ONESTOPBIT;
        dcb.fBinary = TRUE;
        dcb.fParity = TRUE;

        if (!SetCommState(serial_handle, &dcb)) {
            return false;
        }

        COMMTIMEOUTS timeouts = {0};
        timeouts.ReadIntervalTimeout = 50;
        timeouts.ReadTotalTimeoutConstant = 1000;
        timeouts.ReadTotalTimeoutMultiplier = 10;
        timeouts.WriteTotalTimeoutConstant = 1000;
        timeouts.WriteTotalTimeoutMultiplier = 10;

        if (!SetCommTimeouts(serial_handle, &timeouts)) {
            return false;
        }
#else
        serial_fd = open(port.c_str(), O_RDWR | O_NOCTTY | O_NDELAY);
        if (serial_fd == -1) {
            return false;
        }

        struct termios options;
        tcgetattr(serial_fd, &options);

        // Set baudrate
        speed_t speed;
        switch (baudrate) {
            case 115200: speed = B115200; break;
            case 230400: speed = B230400; break;
            case 460800: speed = B460800; break;
            case 921600: speed = B921600; break;
            case 256000: speed = B256000; break;
            default: speed = B115200; break;
        }

        cfsetispeed(&options, speed);
        cfsetospeed(&options, speed);

        options.c_cflag |= (CLOCAL | CREAD);
        options.c_cflag &= ~PARENB;
        options.c_cflag &= ~CSTOPB;
        options.c_cflag &= ~CSIZE;
        options.c_cflag |= CS8;
        options.c_cflag &= ~CRTSCTS;

        options.c_lflag &= ~(ICANON | ECHO | ECHOE | ISIG);
        options.c_iflag &= ~(IXON | IXOFF | IXANY);
        options.c_oflag &= ~OPOST;

        options.c_cc[VMIN] = 0;
        options.c_cc[VTIME] = 10; // 1 second timeout

        tcsetattr(serial_fd, TCSANOW, &options);
        tcflush(serial_fd, TCIOFLUSH);
#endif
        return true;
    }

    void closeSerial() {
#ifdef _WIN32
        if (serial_handle != INVALID_HANDLE_VALUE) {
            CloseHandle(serial_handle);
            serial_handle = INVALID_HANDLE_VALUE;
        }
#else
        if (serial_fd != -1) {
            close(serial_fd);
            serial_fd = -1;
        }
#endif
    }

    bool writeData(const uint8_t* data, size_t length) {
#ifdef _WIN32
        DWORD bytes_written;
        return WriteFile(serial_handle, data, length, &bytes_written, NULL) && 
               bytes_written == length;
#else
        return write(serial_fd, data, length) == (ssize_t)length;
#endif
    }

    int readData(uint8_t* buffer, size_t max_length, int timeout_ms = 1000) {
#ifdef _WIN32
        DWORD bytes_read;
        if (ReadFile(serial_handle, buffer, max_length, &bytes_read, NULL)) {
            return bytes_read;
        }
        return -1;
#else
        fd_set readfds;
        struct timeval timeout;
        
        FD_ZERO(&readfds);
        FD_SET(serial_fd, &readfds);
        
        timeout.tv_sec = timeout_ms / 1000;
        timeout.tv_usec = (timeout_ms % 1000) * 1000;
        
        int result = select(serial_fd + 1, &readfds, NULL, NULL, &timeout);
        if (result > 0 && FD_ISSET(serial_fd, &readfds)) {
            return read(serial_fd, buffer, max_length);
        }
        return 0;
#endif
    }

    TestResult testPort(const std::string& port, int baudrate) {
        TestResult result;
        result.port = port;
        result.baudrate = baudrate;
        result.raw_communication = false;
        result.device_info_success = false;
        result.health_check_success = false;
        result.scan_start_success = false;
        result.scan_points_received = 0;
        result.error_message = "";

        auto start_time = std::chrono::high_resolution_clock::now();

        std::cout << "Testing " << port << " at " << baudrate << " baud..." << std::endl;

        if (!openSerial(port, baudrate)) {
            result.error_message = "Failed to open serial port";
            auto end_time = std::chrono::high_resolution_clock::now();
            result.test_duration_ms = std::chrono::duration<double, std::milli>(end_time - start_time).count();
            return result;
        }

        // Test 1: Raw communication test
        std::cout << "  Testing raw communication..." << std::endl;
        uint8_t reset_cmd[] = {0xA5, 0x40};  // RESET command
        if (writeData(reset_cmd, 2)) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            uint8_t buffer[256];
            int bytes = readData(buffer, 256, 500);
            if (bytes > 0) {
                result.raw_communication = true;
                std::cout << "    ✓ Raw communication successful (" << bytes << " bytes)" << std::endl;
            } else {
                std::cout << "    ✗ No response to reset command" << std::endl;
            }
        }

        // Test 2: Get device info
        std::cout << "  Testing device info request..." << std::endl;
        uint8_t info_cmd[] = {0xA5, 0x50};  // GET_INFO command
        if (writeData(info_cmd, 2)) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            uint8_t buffer[256];
            int bytes = readData(buffer, 256, 1000);
            if (bytes >= 7) {  // Minimum response size
                // Check response format
                if (buffer[0] == 0xA5 && buffer[1] == 0x5A) {
                    result.device_info_success = true;
                    std::cout << "    ✓ Device info received (" << bytes << " bytes)" << std::endl;
                    
                    // Extract device info
                    if (bytes >= 20) {
                        std::cout << "      Model: " << (int)buffer[7] << std::endl;
                        std::cout << "      Firmware: " << (int)buffer[8] << "." << (int)buffer[9] << std::endl;
                        std::cout << "      Hardware: " << (int)buffer[10] << std::endl;
                    }
                } else {
                    std::cout << "    ✗ Invalid response header: " << std::hex << 
                                 (int)buffer[0] << " " << (int)buffer[1] << std::dec << std::endl;
                }
            } else {
                std::cout << "    ✗ Insufficient response (" << bytes << " bytes)" << std::endl;
            }
        }

        // Test 3: Get health
        std::cout << "  Testing health check..." << std::endl;
        uint8_t health_cmd[] = {0xA5, 0x52};  // GET_HEALTH command
        if (writeData(health_cmd, 2)) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            uint8_t buffer[256];
            int bytes = readData(buffer, 256, 1000);
            if (bytes >= 10) {
                if (buffer[0] == 0xA5 && buffer[1] == 0x5A) {
                    result.health_check_success = true;
                    uint8_t status = buffer[7];
                    uint16_t error_code = (buffer[9] << 8) | buffer[8];
                    std::cout << "    ✓ Health check successful" << std::endl;
                    std::cout << "      Status: " << (int)status << std::endl;
                    std::cout << "      Error code: " << error_code << std::endl;
                } else {
                    std::cout << "    ✗ Invalid health response header" << std::endl;
                }
            } else {
                std::cout << "    ✗ Health check failed (" << bytes << " bytes)" << std::endl;
            }
        }

        // Test 4: Start scan
        std::cout << "  Testing scan start..." << std::endl;
        uint8_t scan_cmd[] = {0xA5, 0x20};  // START_SCAN command
        if (writeData(scan_cmd, 2)) {
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
            
            // Try to read scan data
            uint8_t buffer[2048];
            int total_points = 0;
            int attempts = 0;
            const int max_attempts = 20;
            
            while (attempts < max_attempts) {
                int bytes = readData(buffer, 2048, 200);
                if (bytes > 0) {
                    // Count potential scan points (each point is typically 5 bytes)
                    int points_in_buffer = bytes / 5;
                    total_points += points_in_buffer;
                    std::cout << "    Read " << bytes << " bytes (" << points_in_buffer << " potential points)" << std::endl;
                    
                    if (total_points > 10) {
                        result.scan_start_success = true;
                        break;
                    }
                } else {
                    std::cout << "    No data received (attempt " << (attempts + 1) << ")" << std::endl;
                }
                attempts++;
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
            }
            
            result.scan_points_received = total_points;
            
            if (result.scan_start_success) {
                std::cout << "    ✓ Scan data received (" << total_points << " points)" << std::endl;
            } else {
                std::cout << "    ✗ No valid scan data received" << std::endl;
            }
        }

        // Stop scan
        uint8_t stop_cmd[] = {0xA5, 0x25};  // STOP command
        writeData(stop_cmd, 2);
        std::this_thread::sleep_for(std::chrono::milliseconds(100));

        closeSerial();

        auto end_time = std::chrono::high_resolution_clock::now();
        result.test_duration_ms = std::chrono::duration<double, std::milli>(end_time - start_time).count();

        return result;
    }

    void runFullDiagnostic() {
        std::cout << "=== RPLIDAR C++ Hardware Diagnostic ===" << std::endl;
        
        auto ports = findSerialPorts();
        if (ports.empty()) {
            std::cout << "No serial ports found!" << std::endl;
            return;
        }

        std::cout << "Found ports: ";
        for (const auto& port : ports) {
            std::cout << port << " ";
        }
        std::cout << std::endl << std::endl;

        std::vector<int> baudrates = {115200, 256000, 230400, 460800, 921600};

        bool first_result = true;
        for (const auto& port : ports) {
            for (int baudrate : baudrates) {
                TestResult result = testPort(port, baudrate);
                results.push_back(result);
                
                // Write to JSON log
                if (!first_result) {
                    log_file << ",\n";
                }
                writeResultToJson(result);
                first_result = false;

                // Summary
                std::cout << "  Result: ";
                if (result.scan_start_success) {
                    std::cout << "✓ WORKING - Scan successful with " << result.scan_points_received << " points" << std::endl;
                } else if (result.device_info_success || result.health_check_success) {
                    std::cout << "⚠ PARTIAL - Device responds but scanning failed" << std::endl;
                } else if (result.raw_communication) {
                    std::cout << "⚠ BASIC - Raw communication only" << std::endl;
                } else {
                    std::cout << "✗ FAILED - " << result.error_message << std::endl;
                }
                
                std::cout << "  Duration: " << std::fixed << std::setprecision(1) << 
                             result.test_duration_ms << "ms" << std::endl << std::endl;
            }
        }

        // Summary
        printSummary();
    }

    void writeResultToJson(const TestResult& result) {
        log_file << "    {\n";
        log_file << "      \"port\": \"" << result.port << "\",\n";
        log_file << "      \"baudrate\": " << result.baudrate << ",\n";
        log_file << "      \"raw_communication\": " << (result.raw_communication ? "true" : "false") << ",\n";
        log_file << "      \"device_info_success\": " << (result.device_info_success ? "true" : "false") << ",\n";
        log_file << "      \"health_check_success\": " << (result.health_check_success ? "true" : "false") << ",\n";
        log_file << "      \"scan_start_success\": " << (result.scan_start_success ? "true" : "false") << ",\n";
        log_file << "      \"scan_points_received\": " << result.scan_points_received << ",\n";
        log_file << "      \"error_message\": \"" << result.error_message << "\",\n";
        log_file << "      \"test_duration_ms\": " << std::fixed << std::setprecision(2) << result.test_duration_ms << "\n";
        log_file << "    }";
    }

    void printSummary() {
        std::cout << "=== DIAGNOSTIC SUMMARY ===" << std::endl;
        
        bool found_working = false;
        for (const auto& result : results) {
            if (result.scan_start_success) {
                std::cout << "✓ WORKING CONFIGURATION FOUND:" << std::endl;
                std::cout << "  Port: " << result.port << std::endl;
                std::cout << "  Baudrate: " << result.baudrate << std::endl;
                std::cout << "  Scan points: " << result.scan_points_received << std::endl;
                found_working = true;
                break;
            }
        }

        if (!found_working) {
            std::cout << "✗ NO WORKING CONFIGURATIONS FOUND" << std::endl;
            std::cout << "\nPartial successes:" << std::endl;
            for (const auto& result : results) {
                if (result.device_info_success || result.health_check_success || result.raw_communication) {
                    std::cout << "  " << result.port << " @ " << result.baudrate << ": ";
                    if (result.device_info_success) std::cout << "DeviceInfo ";
                    if (result.health_check_success) std::cout << "Health ";
                    if (result.raw_communication) std::cout << "RawComm ";
                    std::cout << std::endl;
                }
            }
        }

        std::cout << "\nResults saved to: rplidar_diagnostic_results.json" << std::endl;
    }

    void finalizeLogs() {
        log_file << "\n  ],\n";
        log_file << "  \"summary\": {\n";
        log_file << "    \"total_tests\": " << results.size() << ",\n";
        
        int working_configs = 0;
        int partial_configs = 0;
        for (const auto& result : results) {
            if (result.scan_start_success) {
                working_configs++;
            } else if (result.device_info_success || result.health_check_success || result.raw_communication) {
                partial_configs++;
            }
        }
        
        log_file << "    \"working_configurations\": " << working_configs << ",\n";
        log_file << "    \"partial_configurations\": " << partial_configs << "\n";
        log_file << "  }\n";
        log_file << "}\n";
        log_file.close();
    }
};

int main() {
    RPLidarDiagnostic diagnostic;
    diagnostic.runFullDiagnostic();
    return 0;
}
