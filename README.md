# AWS Dashboard with GPS (simpleRTK2B) and LiDAR (RPLIDAR)

Web-based dashboard with a Flask API backend and DynamoDB storage, integrating:
- GPS: ArduSimple simpleRTK2B (u-blox ZED-F9P)
- LiDAR: SLAMTEC RPLIDAR

References:
- ArduSimple simpleRTK2B product page: [simpleRTK2B Budget](https://www.ardusimple.com/product/simplertk2b/)
- SLAMTEC RPLIDAR SDK: `https://github.com/slamtec/rplidar_sdk`

## Project structure
- `app.py`: Flask API, env-driven; endpoints:
  - `GET /api/telemetry/latest`: latest GPS telemetry for `DEVICE_ID`
  - `GET /api/lidar/latest`: latest LiDAR summary for `DEVICE_ID`
- `scripts/`: utilities and sensor bridges
  - `create_dynamodb_table.py`: create DynamoDB tables
  - `gps_to_dynamodb.py`: read NMEA from simpleRTK2B and write telemetry
  - `rplidar_to_dynamodb.py`: read RPLIDAR scans and write summaries
  - `seed_sample_telem.py`: insert a sample telemetry item for testing
- Frontend: `index.html`, `script.js`, `styles.css`, `config.js`
  - `config.js` controls `API_BASE_URL` and `WEBRTC_OFFER_URL`

## Requirements
- Python 3.10+
- DynamoDB (local or AWS)
- Hardware (optional for live data):
  - simpleRTK2B on a serial port (NMEA out)
  - RPLIDAR on a serial port

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

## Configure
Copy `.env.example` to `.env` and set values:

- `AWS_REGION`, `DDB_ENDPOINT_URL`, `DDB_TABLE_NAME`, `LIDAR_TABLE_NAME`
- `DEVICE_ID`
- `GPS_SERIAL_PORT`, `RPLIDAR_PORT`

Create tables:

```bash
python scripts/create_dynamodb_table.py
```

## Run
- Start GPS bridge:
  ```bash
  python scripts/gps_to_dynamodb.py
  ```
- Start LiDAR bridge:
  ```bash
  python scripts/rplidar_to_dynamodb.py
  ```
- Start API:
  ```bash
  python app.py
  ```
- Open UI: open `index.html` in a browser (edit `config.js` if API URL differs)

## Quick test without hardware
Seed a sample telemetry row, then refresh the dashboard:

```bash
python scripts/seed_sample_telem.py
```

## Notes
- GPS accuracy displayed as HDOP (`gps_accuracy_hdop`) when available
- DynamoDB schema: Partition key `device_id` (S), Sort key `timestamp` (N)
- For advanced GPS usage, consider UBX via `pyubx2`. For LiDAR, the official SDK offers more control (`https://github.com/slamtec/rplidar_sdk`).

