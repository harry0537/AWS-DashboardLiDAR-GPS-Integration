# System Architecture

This document outlines the high-level components, data flows, and interfaces of the autonomous vehicle system for orchard operations.

## Components
- Onboard sensors and bridges
  - RTK GPS (simpleRTK2B, ZED-F9P) → `gps_to_dynamodb.py`
  - LiDAR (SLAMTEC RPLIDAR) → `rplidar_to_dynamodb.py`
- Backend API
  - Flask (`app.py`), environment-driven
  - DynamoDB tables: `UGVTelemetry`, `UGVLidarScans`
- Frontend dashboard
  - `index.html`, `script.js`, `config.js`
  - Leaflet map, RealSense/WebRTC placeholder

## Architecture Diagram
```mermaid
graph TD
  subgraph Onboard
    GPS[RTK GPS simpleRTK2B] -->|NMEA via Serial| GPSBRIDGE[gps_to_dynamodb.py]
    LIDAR[RPLIDAR] -->|Serial| LIDARBRIDGE[rplidar_to_dynamodb.py]
  end

  GPSBRIDGE -->|PutItem| DDB[(DynamoDB UGVTelemetry)]
  LIDARBRIDGE -->|PutItem| DDBL[(DynamoDB UGVLidarScans)]

  subgraph Cloud/API
    API[Flask API app.py]
  end

  DDB -->|Query latest| API
  DDBL -->|Query latest| API

  subgraph Operator
    UI[Browser Dashboard]
  end

  UI -->|/api/telemetry/latest| API
  UI -->|/api/lidar/latest| API
  UI -.->|WebRTC Offer| STREAM[Video Stream Service]
```

## Data Model (DynamoDB)
- `UGVTelemetry`
  - PK: `device_id` (S)
  - SK: `timestamp` (N)
  - Attributes: `lat`, `lon`, `speed`, `heading`, `gps_accuracy_hdop`
- `UGVLidarScans`
  - PK: `device_id` (S)
  - SK: `timestamp` (N)
  - Attributes: `summary` (min, max, median distances)

## Telemetry Flow (Sequence)
```mermaid
sequenceDiagram
  autonumber
  participant GPS as GPS (simpleRTK2B)
  participant GBr as gps_to_dynamodb.py
  participant DDB as DynamoDB UGVTelemetry
  participant API as Flask API
  participant UI as Dashboard

  GPS->>GBr: NMEA (GGA/RMC/VTG)
  GBr->>DDB: PutItem {device_id, timestamp, lat, lon, speed, heading, hdop}
  UI->>API: GET /api/telemetry/latest
  API->>DDB: Query latest by device_id
  DDB-->>API: Item
  API-->>UI: JSON telemetry
  UI->>UI: Update map, speed, GPS accuracy
```

## Configuration
- Backend: `.env` → `AWS_REGION`, `DDB_ENDPOINT_URL`, `DDB_TABLE_NAME`, `LIDAR_TABLE_NAME`, `DEVICE_ID`, `FLASK_HOST/PORT`
- Frontend: `config.js` → `API_BASE_URL`, `WEBRTC_OFFER_URL`
- Serial: `GPS_SERIAL_PORT`, `RPLIDAR_PORT`

## Operational Notes
- Replace Scan with Query for reads (done) and maintain time-ordered writes.
- Ensure RTK correction setup for simpleRTK2B; antenna quality is critical. Reference: [simpleRTK2B Budget](https://www.ardusimple.com/product/simplertk2b/)
- For LiDAR, the Python wrapper is used for summaries; consider the official SDK for advanced use: `https://github.com/slamtec/rplidar_sdk` 