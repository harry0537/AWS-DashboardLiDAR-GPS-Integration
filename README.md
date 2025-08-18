# 🚀 Team Omega - Project Astra

**Autonomous Orchard Rover with Advanced Perception & RTK Navigation**

[![Build Status](https://github.com/team-omega/project-astra/workflows/CI/badge.svg)](https://github.com/team-omega/project-astra/actions)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-18+-blue.svg)](https://reactjs.org)

## 🌟 Overview

Project Astra is Team Omega's enhanced autonomous vehicle prototype designed for orchard environments. This project builds on existing infrastructure to deliver a **semi-autonomous orchard rover** with reliable 360° perception, centimetre-level navigation, and a secure live dashboard.

### 🎯 **Key Objectives**
- **LiDAR + Camera Integration** - Advanced obstacle detection and image capture
- **RTK GPS Precision** - Centimetre-level navigation accuracy
- **AWS Dashboard** - Real-time monitoring with 2s updates and 95% uptime
- **Image Capture Pipeline** - 500+ images @1080p for future AI analysis
- **Object Avoidance** - ≥90% success rate in 50+ trials

### 🏗️ **Architecture**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Pixhawk 6C   │    │   Intel NUC     │    │   AWS Cloud     │
│   (ArduPilot)  │◄──►│   Companion     │◄──►│   Dashboard     │
│                 │    │                 │    │                 │
│ • RTK GPS      │    │ • MAVProxy      │    │ • Flask API     │
│ • LiDAR        │    │ • NTRIP Client  │    │ • DynamoDB      │
│ • Camera       │    │ • Fusion Engine │    │ • React UI      │
│ • Ultrasonic   │    │ • Telemetry     │    │ • Real-time     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 **Quick Start**

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- RPLIDAR sensor
- RTK GPS (ZED-F9P)
- Pixhawk 6C

### 1. Clone & Setup
```bash
git clone https://github.com/team-omega/project-astra.git
cd project-astra

# Quick setup
make quick-start
```

### 2. Configure Environment
```bash
# Edit companion configuration
cp companion/env.example companion/.env
# Configure NTRIP, sensor ports, etc.

# Edit cloud configuration  
cp cloud/env.example cloud/.env
# Configure AWS credentials, database, etc.
```

### 3. Start Development Environment
```bash
# Start companion services
make dev

# Start cloud stack
make docker-up

# Open dashboard
open http://localhost:3000
```

## 📁 **Project Structure**

```
/astra
├── /companion              # NUC companion computer code
│   ├── /mav               # MAVLink routing & MAVProxy
│   ├── /gnss              # NTRIP client & RTK monitoring
│   ├── /sensing           # LiDAR, camera, ultrasonic drivers
│   ├── /fusion            # Obstacle fusion → MAVLink
│   ├── /telemetry         # Data uplink to cloud
│   ├── /rtb               # Return-to-Base logic
│   └── /utils             # Logging, config, health checks
├── /cloud                  # Cloud infrastructure
│   ├── /api               # Flask/FastAPI backend
│   ├── /ingest            # Telemetry ingest services
│   ├── /db                # Database schemas & migrations
│   ├── /dashboard         # React dashboard (Vite + Tailwind)
│   └── /infra             # Docker, docker-compose, IaC
├── /ops                    # Operations & deployment
│   ├── /zerotier          # VPN configuration
│   ├── /ci                # GitHub Actions CI/CD
│   └── /deploy            # Deployment scripts
├── /firmware              # ArduPilot parameters & missions
├── /docs                  # Documentation & runbooks
└── Makefile               # Common development tasks
```

## 🔧 **Core Components**

### **Companion Services**
- **MAVProxy Launcher** - Stable MAVLink routing with health monitoring
- **NTRIP Client** - RTK correction data with automatic reconnection
- **RPLIDAR Driver** - Enhanced obstacle detection with clustering
- **Fusion Engine** - Multi-sensor obstacle fusion for ArduPilot
- **Telemetry Uplink** - Real-time data transmission to cloud

### **Cloud Infrastructure**
- **Flask API** - RESTful endpoints for telemetry & control
- **React Dashboard** - Real-time monitoring with Leaflet maps
- **DynamoDB** - Scalable telemetry storage
- **Docker Stack** - Containerized deployment

### **Hardware Integration**
- **RTK GPS** - ZED-F9P with NTRIP corrections
- **LiDAR** - RPLIDAR A1/A2/N301 for 360° perception
- **Camera** - UVC/CSI camera for image capture
- **Ultrasonic** - Maxbotix I2C EZ4 for blind spots

## 📊 **Performance Targets**

| Metric | Target | Status |
|--------|--------|--------|
| **RTK Accuracy** | ≤5cm drift over 100m | 🟡 In Progress |
| **Obstacle Detection** | ≥95% success rate | 🟡 In Progress |
| **Avoidance Success** | ≥90% in 50 trials | 🟡 In Progress |
| **Dashboard Updates** | 2s latency | 🟡 In Progress |
| **System Uptime** | ≥95% during tests | 🟡 In Progress |
| **Image Capture** | 500+ @1080p | 🟡 In Progress |

## 🧪 **Testing & Validation**

### **Test Suites**
```bash
# Run all tests
make test

# Specific test categories
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests  
pytest tests/performance/   # Performance tests
```

### **Field Testing**
- **RTK Validation** - 100m line test for GPS accuracy
- **Obstacle Course** - Cone grid at 1-5m distances
- **Avoidance Trials** - 50+ trials in mock orchard rows
- **Endurance Test** - 30-minute continuous operation

## 🚀 **Deployment**

### **NUC Companion**
```bash
# Deploy to NUC
make deploy-nuc

# Check service status
make status
```

### **EC2 Cloud**
```bash
# Deploy to EC2
make deploy-ec2

# Start cloud stack
make docker-up
```

## 📚 **Documentation**

- **[System Architecture](docs/System_Architecture.md)** - Technical design & data flow
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Step-by-step deployment
- **[Testing Guide](docs/TESTING.md)** - Validation procedures
- **[API Reference](docs/API.md)** - Backend API documentation
- **[Hardware Setup](docs/HARDWARE.md)** - Sensor wiring & configuration

## 🤝 **Contributing**

### **Team Omega Members**
- **Harinder Singh** - Project Manager & Cloud Dashboard
- **Param** - RTK GPS & Sensor Integration  
- **Lewis Hall** - UI/UX & Documentation

### **Development Workflow**
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📋 **Roadmap**

### **Phase 1: Core Integration (Week 1-2)**
- [x] Project structure & environment setup
- [x] MAVProxy launcher with health monitoring
- [x] NTRIP client for RTK corrections
- [x] Enhanced RPLIDAR driver with clustering
- [ ] Obstacle fusion engine
- [ ] Basic telemetry uplink

### **Phase 2: Perception & Navigation (Week 3-4)**
- [ ] Camera integration & image capture
- [ ] Multi-sensor obstacle fusion
- [ ] MAVLink OBSTACLE_DISTANCE publishing
- [ ] RTK validation & testing
- [ ] Basic obstacle avoidance

### **Phase 3: Cloud & Dashboard (Week 5-6)**
- [ ] Flask API with real-time endpoints
- [ ] React dashboard with live updates
- [ ] DynamoDB integration
- [ ] Docker deployment
- [ ] Performance optimization

### **Phase 4: Testing & Validation (Week 7-8)**
- [ ] Field testing & validation
- [ ] Performance benchmarking
- [ ] Documentation completion
- [ ] Final presentation preparation

## 🆘 **Support & Troubleshooting**

### **Common Issues**
- **MAVProxy Connection** - Check serial port permissions and baud rate
- **NTRIP Issues** - Verify credentials and network connectivity
- **LiDAR Problems** - Check USB connection and driver installation
- **Dashboard Not Loading** - Verify API endpoints and CORS settings

### **Getting Help**
- 📖 Check the [documentation](docs/)
- 🐛 Report bugs via [GitHub Issues](https://github.com/team-omega/project-astra/issues)
- 💬 Join our [Discord server](https://discord.gg/team-omega)
- 📧 Contact: team-omega@unitec.ac.nz

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 **Acknowledgments**

- **Artem (Project Astra Ltd)** - Project sponsor and hardware provider
- **Jamie Bell** - Academic supervisor
- **Unitec Institute of Technology** - Academic support
- **Previous Team** - Foundation infrastructure and handover

---

**Built with ❤️ by Team Omega for the future of autonomous agriculture**

