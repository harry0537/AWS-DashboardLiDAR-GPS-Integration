#!/usr/bin/env python3
"""
Team Omega - MAVProxy Launcher
Launches MAVProxy with proper routing for fusion, telemetry, and GCS
"""

import os
import sys
import time
import signal
import subprocess
import logging
from pathlib import Path
from typing import List, Optional
import structlog

# Setup structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
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


class MAVProxyLauncher:
    """MAVProxy launcher with health monitoring and auto-restart"""
    
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.running = False
        self.restart_count = 0
        self.max_restarts = 5
        
        # Load configuration from environment
        self.master_port = os.getenv("MAVPROXY_MASTER_PORT", "/dev/ttyS5")
        self.master_baud = os.getenv("MAVPROXY_MASTER_BAUD", "921600")
        self.local_port = int(os.getenv("MAVPROXY_LOCAL_PORT", "14550"))
        self.fusion_port = int(os.getenv("MAVPROXY_FUSION_PORT", "14551"))
        self.telemetry_port = int(os.getenv("MAVPROXY_TELEMETRY_PORT", "14552"))
        self.gcs_ip = os.getenv("MAVPROXY_GCS_IP", "192.168.1.100")
        self.gcs_port = int(os.getenv("MAVPROXY_GCS_PORT", "14550"))
        
        # Signal handling
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info("Received shutdown signal", signal=signum)
        self.stop()
        sys.exit(0)
    
    def build_mavproxy_command(self) -> List[str]:
        """Build MAVProxy command with routing configuration"""
        cmd = [
            "mavproxy.py",
            f"--master={self.master_port},{self.master_baud}",
            f"--out=127.0.0.1:{self.local_port}",      # Local tools/GCS
            f"--out=127.0.0.1:{self.fusion_port}",     # Fusion publisher input
            f"--out=127.0.0.1:{self.telemetry_port}",  # Telemetry logger
            f"--out={self.gcs_ip}:{self.gcs_port}",    # Remote GCS via 5G/ZeroTier
            "--logfile=/var/log/astra/mavproxy.log",
            "--state-basedir=/var/log/astra/mavproxy",
            "--daemon",
            "--non-interactive"
        ]
        
        logger.info("Built MAVProxy command", command=" ".join(cmd))
        return cmd
    
    def start(self) -> bool:
        """Start MAVProxy process"""
        try:
            # Ensure log directories exist
            Path("/var/log/astra").mkdir(parents=True, exist_ok=True)
            Path("/var/log/astra/mavproxy").mkdir(parents=True, exist_ok=True)
            
            cmd = self.build_mavproxy_command()
            logger.info("Starting MAVProxy", command=" ".join(cmd))
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            self.running = True
            self.restart_count = 0
            
            logger.info("MAVProxy started successfully", pid=self.process.pid)
            return True
            
        except Exception as e:
            logger.error("Failed to start MAVProxy", error=str(e))
            return False
    
    def stop(self):
        """Stop MAVProxy process gracefully"""
        if self.process and self.running:
            logger.info("Stopping MAVProxy", pid=self.process.pid)
            
            try:
                # Send SIGTERM to process group
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                
                # Wait for graceful shutdown
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning("MAVProxy didn't stop gracefully, forcing kill")
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    self.process.wait()
                    
            except Exception as e:
                logger.error("Error stopping MAVProxy", error=str(e))
                # Force kill if needed
                try:
                    self.process.kill()
                except:
                    pass
            
            self.running = False
            logger.info("MAVProxy stopped")
    
    def is_healthy(self) -> bool:
        """Check if MAVProxy is healthy"""
        if not self.process or not self.running:
            return False
        
        # Check if process is still running
        if self.process.poll() is not None:
            logger.warning("MAVProxy process terminated unexpectedly", 
                         return_code=self.process.returncode)
            return False
        
        # Check if ports are listening (basic health check)
        try:
            import socket
            for port in [self.local_port, self.fusion_port, self.telemetry_port]:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                if result != 0:
                    logger.warning("Port not listening", port=port)
                    return False
        except Exception as e:
            logger.warning("Health check failed", error=str(e))
            return False
        
        return True
    
    def restart(self) -> bool:
        """Restart MAVProxy if needed"""
        if self.restart_count >= self.max_restarts:
            logger.error("Max restart attempts reached", max_restarts=self.max_restarts)
            return False
        
        logger.info("Restarting MAVProxy", restart_count=self.restart_count + 1)
        self.stop()
        time.sleep(2)  # Wait for cleanup
        
        self.restart_count += 1
        return self.start()
    
    def run(self):
        """Main run loop with health monitoring"""
        logger.info("Starting MAVProxy launcher")
        
        if not self.start():
            logger.error("Failed to start MAVProxy initially")
            sys.exit(1)
        
        try:
            while self.running:
                time.sleep(30)  # Health check every 30 seconds
                
                if not self.is_healthy():
                    logger.warning("MAVProxy unhealthy, attempting restart")
                    if not self.restart():
                        logger.error("Failed to restart MAVProxy")
                        break
                        
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.stop()
            logger.info("MAVProxy launcher stopped")


def main():
    """Main entry point"""
    launcher = MAVProxyLauncher()
    launcher.run()


if __name__ == "__main__":
    main()
