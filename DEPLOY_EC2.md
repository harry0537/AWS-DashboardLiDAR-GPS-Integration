# EC2 Deployment Guide (API + DynamoDB Local + optional Nginx)

This guide helps you deploy the Flask API on an EC2 instance to serve real-time rover data.

## 1. Provision EC2
- AMI: Ubuntu 22.04 LTS
- Instance type: t3.small (or higher)
- Storage: 20 GB gp3
- Security Group:
  - Inbound: 22 (SSH), 80 (HTTP) if using Nginx, 5000 (Flask API, or keep internal), 8000 (DDB Local, dev only – restrict)
  - Outbound: allow all
- Key pair: create/download

## 2. SSH and Install Docker
```bash
sudo apt-get update -y
sudo apt-get install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER
newgrp docker
```

## 3. Pull repo and set env
```bash
git clone https://github.com/harry0537/AWS-DashboardLiDAR-GPS-Integration.git
cd AWS-DashboardLiDAR-GPS-Integration
cp .env.example .env
# Edit env for prod: set AWS_REGION, DDB_ENDPOINT_URL (remove if using AWS DynamoDB),
# DDB_TABLE_NAME, LIDAR_TABLE_NAME, DEVICE_ID, FLASK_HOST/PORT
```

If using AWS DynamoDB (recommended for production), remove `DDB_ENDPOINT_URL` from `.env` or set to empty.

## 4. Run (compose)
- Dev (with DynamoDB Local):
```bash
docker compose up -d --build
```
- API only (if using AWS DynamoDB):
```bash
# Stop/remove ddb service or delete from compose before building
sed -i '/^  ddb:/,/^$/d' docker-compose.yml
sed -i '/depends_on:/,/^$/d' docker-compose.yml

docker compose up -d --build
```

## 5. Create DynamoDB tables (one-time)
```bash
docker compose exec api python scripts/create_dynamodb_table.py
```

## 6. Test
- API health: `curl http://<EC2_PUBLIC_IP>:5000/api/telemetry/latest`
- If fronted by Nginx (optional), set `config.js` to `http://<EC2_PUBLIC_IP>` and hit `/api/...`

## 7. Security notes
- Prefer AWS DynamoDB (managed) over DynamoDB Local in production.
- Consider API Gateway in front of Flask, and restrict CORS in `app.py`.
- Use HTTPS (ACM + ALB or Nginx with certs).
- Lock down SG to trusted IPs for admin ports.

## 8. Sync flow overview
- Rover (on-site) runs `gps_to_dynamodb.py` (and optionally `rplidar_to_dynamodb.py`) pointing to same DynamoDB.
- EC2 API queries latest telemetry by `device_id` and serves the dashboard.
- The dashboard points `API_BASE_URL` to the EC2 API URL/IP in `config.js`.

## 9. Troubleshooting
- 502 via Nginx: check `api` container logs, service naming, and port mapping.
- Empty data: verify tables exist and that rover scripts are writing to the same region/table.
- CORS: if browser blocks, configure Flask CORS for your dashboard origin. 