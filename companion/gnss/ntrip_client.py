#!/usr/bin/env python3
"""
Team Omega - NTRIP Client for RTK GNSS
Connects to NTRIP caster and feeds RTCM3 corrections to Pixhawk
"""

import os
import sys
import time
import socket
import threading
import structlog
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import serial

# Setup structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class RTKStatus(Enum):
    """RTK status enumeration"""
    NO_RTK = "NO_RTK"
    RTK_FLOAT = "RTK_FLOAT"
    RTK_FIX = "RTK_FIX"


@dataclass
class RTKState:
    """RTK state information"""
    status: RTKStatus
    hdop: float
    vdop: float
    satellites: int
    last_fix_time: float
    baseline_length: Optional[float] = None


class NTRIPClient:
    """NTRIP client for RTK correction data"""
    
    def __init__(self):
        # Load configuration from environment
        self.caster_url = os.getenv("NTRIP_CASTER_URL")
        self.username = os.getenv("NTRIP_USERNAME")
        self.password = os.getenv("NTRIP_PASSWORD")
        self.mountpoint = os.getenv("NTRIP_MOUNTPOINT")
        self.ntrip_port = int(os.getenv("NTRIP_PORT", "2101"))
        
        # GPS serial configuration
        self.gps_port = os.getenv("GPS_SERIAL_PORT", "/dev/ttyS5")
        self.gps_baud = int(os.getenv("GPS_BAUD_RATE", "921600"))
        
        # State tracking
        self.connected = False
        self.socket: Optional[socket.socket] = None
        self.serial: Optional[serial.Serial] = None
        self.rtk_state = RTKState(
            status=RTKStatus.NO_RTK,
            hdop=999.0,
            vdop=999.0,
            satellites=0,
            last_fix_time=0.0
        )
        
        # Metrics
        self.rtcm_packets_received = 0
        self.rtcm_bytes_received = 0
        self.last_rtcm_time = 0.0
        self.connection_attempts = 0
        
        # Threading
        self.running = False
        self.rtk_monitor_thread: Optional[threading.Thread] = None
        
    def connect_ntrip(self) -> bool:
        """Connect to NTRIP caster"""
        try:
            if not all([self.caster_url, self.username, self.password, self.mountpoint]):
                logger.error("Missing NTRIP configuration", 
                           caster_url=bool(self.caster_url),
                           username=bool(self.username),
                           password=bool(self.password),
                           mountpoint=bool(self.mountpoint))
                return False
            
            # Parse caster URL
            if self.caster_url.startswith("http://"):
                host = self.caster_url[7:]
            elif self.caster_url.startswith("https://"):
                host = self.caster_url[8:]
            else:
                host = self.caster_url
            
            # Remove port if present
            if ":" in host:
                host, port_str = host.split(":", 1)
                port = int(port_str)
            else:
                port = self.ntrip_port
            
            logger.info("Connecting to NTRIP caster", host=host, port=port, mountpoint=self.mountpoint)
            
            # Create socket connection
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(30)
            self.socket.connect((host, port))
            
            # Send NTRIP request
            request = (
                f"GET /{self.mountpoint} HTTP/1.0\r\n"
                f"User-Agent: TeamOmega-NTRIP-Client/1.0\r\n"
                f"Authorization: Basic {self._encode_auth()}\r\n"
                f"\r\n"
            )
            
            self.socket.send(request.encode())
            
            # Read response
            response = self.socket.recv(1024).decode()
            if "ICY 200 OK" in response or "HTTP/1.0 200 OK" in response:
                logger.info("Successfully connected to NTRIP caster")
                self.connected = True
                self.connection_attempts = 0
                return True
            else:
                logger.error("NTRIP connection failed", response=response.strip())
                return False
                
        except Exception as e:
            logger.error("Failed to connect to NTRIP caster", error=str(e))
            self.connection_attempts += 1
            return False
    
    def _encode_auth(self) -> str:
        """Encode username:password for Basic auth"""
        import base64
        auth_string = f"{self.username}:{self.password}"
        return base64.b64encode(auth_string.encode()).decode()
    
    def connect_gps_serial(self) -> bool:
        """Connect to GPS serial port for RTCM injection"""
        try:
            logger.info("Connecting to GPS serial port", port=self.gps_port, baud=self.gps_baud)
            
            self.serial = serial.Serial(
                port=self.gps_port,
                baudrate=self.gps_baud,
                timeout=1,
                write_timeout=1
            )
            
            logger.info("Successfully connected to GPS serial port")
            return True
            
        except Exception as e:
            logger.error("Failed to connect to GPS serial port", error=str(e))
            return False
    
    def start_rtk_monitoring(self):
        """Start RTK status monitoring thread"""
        if self.rtk_monitor_thread and self.rtk_monitor_thread.is_alive():
            return
        
        self.rtk_monitor_thread = threading.Thread(target=self._rtk_monitor_loop, daemon=True)
        self.rtk_monitor_thread.start()
        logger.info("Started RTK monitoring thread")
    
    def _rtk_monitor_loop(self):
        """RTK status monitoring loop"""
        while self.running:
            try:
                # Monitor RTK status from GPS data
                # This would typically read from MAVLink GPS_RAW_INT messages
                # For now, we'll simulate status updates
                self._update_rtk_status()
                time.sleep(1)
                
            except Exception as e:
                logger.error("Error in RTK monitoring loop", error=str(e))
                time.sleep(5)
    
    def _update_rtk_status(self):
        """Update RTK status (placeholder - would read from MAVLink)"""
        # TODO: Implement actual MAVLink GPS status reading
        # For now, simulate status updates
        current_time = time.time()
        
        # Simulate RTK status changes
        if self.rtcm_packets_received > 0 and (current_time - self.last_rtcm_time) < 30:
            if self.rtk_state.status == RTKStatus.NO_RTK:
                self.rtk_state.status = RTKStatus.RTK_FLOAT
                logger.info("RTK status changed to FLOAT")
            elif self.rtk_state.status == RTKStatus.RTK_FLOAT and self.rtk_state.hdop < 2.0:
                self.rtk_state.status = RTKStatus.RTK_FIX
                logger.info("RTK status changed to FIX")
        else:
            if self.rtk_state.status != RTKStatus.NO_RTK:
                self.rtk_state.status = RTKStatus.NO_RTK
                logger.warning("RTK status changed to NO_RTK")
    
    def read_rtcm_data(self) -> Optional[bytes]:
        """Read RTCM data from NTRIP connection"""
        if not self.connected or not self.socket:
            return None
        
        try:
            # Read RTCM data (non-blocking)
            self.socket.settimeout(0.1)
            data = self.socket.recv(1024)
            
            if data:
                self.rtcm_packets_received += 1
                self.rtcm_bytes_received += len(data)
                self.last_rtcm_time = time.time()
                
                logger.debug("Received RTCM data", 
                           packet_size=len(data), 
                           total_packets=self.rtcm_packets_received)
                
                return data
            
        except socket.timeout:
            pass  # No data available
        except Exception as e:
            logger.error("Error reading RTCM data", error=str(e))
            self.connected = False
        
        return None
    
    def inject_rtcm_to_gps(self, rtcm_data: bytes) -> bool:
        """Inject RTCM data to GPS via serial"""
        if not self.serial or not self.serial.is_open:
            return False
        
        try:
            self.serial.write(rtcm_data)
            self.serial.flush()
            
            logger.debug("Injected RTCM data to GPS", bytes_injected=len(rtcm_data))
            return True
            
        except Exception as e:
            logger.error("Failed to inject RTCM data to GPS", error=str(e))
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current NTRIP client status"""
        return {
            "connected": self.connected,
            "rtk_status": self.rtk_state.status.value,
            "rtcm_packets_received": self.rtcm_packets_received,
            "rtcm_bytes_received": self.rtcm_bytes_received,
            "last_rtcm_time": self.last_rtcm_time,
            "connection_attempts": self.connection_attempts,
            "hdop": self.rtk_state.hdop,
            "vdop": self.rtk_state.vdop,
            "satellites": self.rtk_state.satellites
        }
    
    def run(self):
        """Main run loop"""
        logger.info("Starting NTRIP client")
        self.running = True
        
        # Start RTK monitoring
        self.start_rtk_monitoring()
        
        try:
            while self.running:
                # Ensure NTRIP connection
                if not self.connected:
                    if not self.connect_ntrip():
                        logger.warning("NTRIP connection failed, retrying in 30 seconds")
                        time.sleep(30)
                        continue
                
                # Ensure GPS serial connection
                if not self.serial or not self.serial.is_open:
                    if not self.connect_gps_serial():
                        logger.warning("GPS serial connection failed, retrying in 10 seconds")
                        time.sleep(10)
                        continue
                
                # Read and inject RTCM data
                rtcm_data = self.read_rtcm_data()
                if rtcm_data:
                    self.inject_rtcm_to_gps(rtcm_data)
                
                # Log status periodically
                if int(time.time()) % 60 == 0:  # Every minute
                    status = self.get_status()
                    logger.info("NTRIP client status", **status)
                
                time.sleep(0.1)  # 10Hz loop
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.stop()
    
    def stop(self):
        """Stop NTRIP client"""
        logger.info("Stopping NTRIP client")
        self.running = False
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        if self.serial:
            try:
                self.serial.close()
            except:
                pass
        
        logger.info("NTRIP client stopped")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Team Omega NTRIP Client")
    parser.add_argument("--caster-url", help="NTRIP caster URL")
    parser.add_argument("--username", help="NTRIP username")
    parser.add_argument("--password", help="NTRIP password")
    parser.add_argument("--mountpoint", help="NTRIP mountpoint")
    parser.add_argument("--gps-port", help="GPS serial port")
    parser.add_argument("--gps-baud", type=int, help="GPS baud rate")
    
    args = parser.parse_args()
    
    # Override environment variables with command line args
    if args.caster_url:
        os.environ["NTRIP_CASTER_URL"] = args.caster_url
    if args.username:
        os.environ["NTRIP_USERNAME"] = args.username
    if args.password:
        os.environ["NTRIP_PASSWORD"] = args.password
    if args.mountpoint:
        os.environ["NTRIP_MOUNTPOINT"] = args.mountpoint
    if args.gps_port:
        os.environ["GPS_SERIAL_PORT"] = args.gps_port
    if args.gps_baud:
        os.environ["GPS_BAUD_RATE"] = str(args.gps_baud)
    
    client = NTRIPClient()
    client.run()


if __name__ == "__main__":
    main()
