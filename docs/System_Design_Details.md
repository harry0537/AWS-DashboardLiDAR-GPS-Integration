# System Design Details

This document captures practical integration details for the rover, focusing on wiring, ports, RTK GPS, LiDAR, and power.

## Bill of Materials (core)
- RTK GPS: ArduSimple simpleRTK2B (u-blox ZED-F9P) – rover unit
- RTK GPS Base: simpleRTK2B (or equivalent) with multiband antenna
- LiDAR: SLAMTEC RPLIDAR (A1/A2/A3/Sx per availability)
- Compute: Windows laptop or SBC (e.g., Jetson/RPi) running Python and Flask
- Antenna: Multiband GNSS antenna (L1/L2)
- Cables: USB for GPS and LiDAR; power for LiDAR if needed

## Port and Serial Settings (Windows)
- GPS rover (simpleRTK2B):
  - Serial port: `COM3` (example)
  - Baud: `115200`
  - Output: NMEA (GGA, RMC, VTG at 1–10 Hz)
- RPLIDAR:
  - Serial port: `COM4` (example)
  - Baud: per model (often `256000`)
- Configure `.env` accordingly:
  - `GPS_SERIAL_PORT=COM3`
  - `RPLIDAR_PORT=COM4`

## Wiring Overview
- GPS rover: USB from simpleRTK2B to host compute
- LiDAR: USB-to-serial adapter to host compute; ensure stable 5V power
- Antennas: 
  - Rover: secure multiband antenna; short low-loss cable; sky view
  - Base: rigid mount, clear sky, known coordinates

## RTK Setup (High-level)
- Base Station (simpleRTK2B):
  1. Fix the base antenna at a surveyed position (or average).
  2. Configure base to output RTCM corrections (e.g., via USB, radio, or NTRIP caster).
  3. Optional: publish to an NTRIP caster (RTK2go) and note mountpoint.
- Rover (simpleRTK2B):
  1. Configure rover to receive RTCM via radio or NTRIP client.
  2. Output NMEA (GGA/RMC/VTG) on USB for the host.
  3. Verify RTK status (FIX/FLOAT) and HDOP on device tools.
- Reference: ArduSimple product page for simpleRTK2B: [simpleRTK2B Budget](https://www.ardusimple.com/product/simplertk2b/)

## Software Data Flow
- GPS: `gps_to_dynamodb.py` parses NMEA and writes to `UGVTelemetry`.
- LiDAR: `rplidar_to_dynamodb.py` summarizes scans and writes to `UGVLidarScans`.
- API: `app.py` exposes `/api/telemetry/latest` and `/api/lidar/latest`.
- UI: `script.js` fetches latest telemetry and updates the dashboard.

## DynamoDB Schema
- `UGVTelemetry(device_id:S, timestamp:N)`: lat, lon, speed, heading, gps_accuracy_hdop
- `UGVLidarScans(device_id:S, timestamp:N)`: summary {min,max,median}

## Power and Mounting Notes
- Ensure clean 5V supply for LiDAR; avoid USB hubs with undervoltage.
- Isolate LiDAR mount from vibration; maintain level orientation.
- Antenna cables should be strain-relieved; avoid tight bends.

## Safety and Field Ops
- Always perform an E-stop plan; test manual overrides.
- Verify GNSS lock before moving; confirm RTK Fix when possible.
- Validate obstacle detection in a safe, controlled area before orchard runs.

## Troubleshooting
- GPS shows no lat/lon: check COM port, baud, and that NMEA sentences are present.
- HDOP too high: relocate antenna, ensure RTK corrections, check sky view.
- LiDAR no data: confirm port and power; try a lower baud model setting.
- API empty responses: run `seed_sample_telem.py` to validate end-to-end.

## References
- ArduSimple simpleRTK2B product page: [simpleRTK2B Budget](https://www.ardusimple.com/product/simplertk2b/)
- SLAMTEC RPLIDAR SDK: `https://github.com/slamtec/rplidar_sdk` 