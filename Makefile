# Team Omega - Project Astra Makefile
# Common tasks for development, building, and deployment

.PHONY: help dev build test deploy-ec2 deploy-nuc clean install-deps setup-env

# Default target
help:
	@echo "Team Omega - Project Astra"
	@echo "=========================="
	@echo ""
	@echo "Available targets:"
	@echo "  help          - Show this help message"
	@echo "  dev           - Start development environment"
	@echo "  build         - Build all components"
	@echo "  test          - Run test suite"
	@echo "  deploy-ec2    - Deploy to EC2 instance"
	@echo "  deploy-nuc    - Deploy to NUC companion"
	@echo "  clean         - Clean build artifacts"
	@echo "  install-deps  - Install dependencies"
	@echo "  setup-env     - Setup environment files"
	@echo "  docker-up     - Start cloud stack with Docker"
	@echo "  docker-down   - Stop cloud stack"
	@echo "  lint          - Run code linting"
	@echo "  format        - Format code with black"

# Development environment
dev: setup-env
	@echo "🚀 Starting Team Omega development environment..."
	@echo "📡 Starting MAVProxy launcher..."
	@cd companion && python -m companion.mav.mavproxy_launcher &
	@echo "🛰️ Starting NTRIP client..."
	@cd companion && python -m companion.gnss.ntrip_client &
	@echo "🔍 Starting RPLIDAR driver..."
	@cd companion && python -m companion.sensing.lidar_rplidar &
	@echo "📊 Starting cloud API..."
	@cd cloud && python -m cloud.api.main &
	@echo "🌐 Starting dashboard..."
	@cd cloud/dashboard && npm run dev &
	@echo "✅ Development environment started!"
	@echo "📋 Use 'make docker-up' to start cloud stack"

# Build all components
build: install-deps
	@echo "🔨 Building Team Omega components..."
	@echo "📦 Building companion modules..."
	@cd companion && python -m pip install -e .
	@echo "🌐 Building dashboard..."
	@cd cloud/dashboard && npm run build
	@echo "🐳 Building Docker images..."
	@cd cloud/infra && docker-compose build
	@echo "✅ Build completed!"

# Run test suite
test:
	@echo "🧪 Running Team Omega test suite..."
	@echo "📋 Running unit tests..."
	@python -m pytest tests/ -v
	@echo "🔍 Running integration tests..."
	@python -m pytest tests/integration/ -v
	@echo "📊 Running performance tests..."
	@python -m pytest tests/performance/ -v
	@echo "✅ Test suite completed!"

# Deploy to EC2
deploy-ec2: build
	@echo "☁️ Deploying to EC2 instance..."
	@echo "📡 Copying files to EC2..."
	@scp -i $(EC2_KEY_PATH) -r cloud/ $(EC2_USER)@$(EC2_IP):/opt/astra/
	@echo "🔧 Installing dependencies on EC2..."
	@ssh -i $(EC2_KEY_PATH) $(EC2_USER)@$(EC2_IP) "cd /opt/astra/cloud && pip install -r requirements.txt"
	@echo "🐳 Starting services on EC2..."
	@ssh -i $(EC2_KEY_PATH) $(EC2_USER)@$(EC2_IP) "cd /opt/astra/cloud/infra && docker-compose up -d"
	@echo "✅ EC2 deployment completed!"

# Deploy to NUC companion
deploy-nuc: build
	@echo "🖥️ Deploying to NUC companion..."
	@echo "📡 Copying companion modules..."
	@scp -r companion/ $(NUC_USER)@$(NUC_IP):/opt/astra/
	@echo "🔧 Installing dependencies on NUC..."
	@ssh $(NUC_USER)@$(NUC_IP) "cd /opt/astra/companion && pip install -r requirements.txt"
	@echo "⚙️ Installing systemd services..."
	@ssh $(NUC_USER)@$(NUC_IP) "sudo cp /opt/astra/ops/deploy/*.service /etc/systemd/system/"
	@ssh $(NUC_USER)@$(NUC_IP) "sudo systemctl daemon-reload"
	@echo "🚀 Enabling and starting services..."
	@ssh $(NUC_USER)@$(NUC_IP) "sudo systemctl enable mavproxy.service ntrip.service fusion.service"
	@ssh $(NUC_USER)@$(NUC_IP) "sudo systemctl start mavproxy.service ntrip.service fusion.service"
	@echo "✅ NUC deployment completed!"

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} +
	@find . -type d -name "build" -exec rm -rf {} +
	@find . -type d -name "dist" -exec rm -rf {} +
	@cd cloud/dashboard && npm run clean 2>/dev/null || true
	@echo "✅ Clean completed!"

# Install dependencies
install-deps:
	@echo "📦 Installing Python dependencies..."
	@pip install -r requirements.txt
	@echo "📦 Installing companion dependencies..."
	@cd companion && pip install -r requirements.txt
	@echo "📦 Installing cloud dependencies..."
	@cd cloud && pip install -r requirements.txt
	@echo "📦 Installing dashboard dependencies..."
	@cd cloud/dashboard && npm install
	@echo "✅ Dependencies installed!"

# Setup environment files
setup-env:
	@echo "⚙️ Setting up environment files..."
	@if [ ! -f companion/.env ]; then \
		echo "📝 Creating companion .env from template..."; \
		cp companion/env.example companion/.env; \
		echo "⚠️ Please edit companion/.env with your configuration"; \
	fi
	@if [ ! -f cloud/.env ]; then \
		echo "📝 Creating cloud .env from template..."; \
		cp cloud/env.example cloud/.env; \
		echo "⚠️ Please edit cloud/.env with your configuration"; \
	fi
	@echo "✅ Environment setup completed!"

# Docker operations
docker-up:
	@echo "🐳 Starting cloud stack with Docker..."
	@cd cloud/infra && docker-compose up -d
	@echo "✅ Cloud stack started!"

docker-down:
	@echo "🐳 Stopping cloud stack..."
	@cd cloud/infra && docker-compose down
	@echo "✅ Cloud stack stopped!"

# Code quality
lint:
	@echo "🔍 Running code linting..."
	@flake8 companion/ cloud/ --max-line-length=100 --ignore=E501,W503
	@echo "✅ Linting completed!"

format:
	@echo "🎨 Formatting code with black..."
	@black companion/ cloud/ --line-length=100
	@echo "✅ Code formatting completed!"

# Quick start for development
quick-start: setup-env install-deps
	@echo "🚀 Quick start setup completed!"
	@echo "📋 Next steps:"
	@echo "  1. Edit companion/.env and cloud/.env"
	@echo "  2. Run 'make dev' to start development environment"
	@echo "  3. Run 'make docker-up' to start cloud stack"
	@echo "  4. Open http://localhost:3000 for dashboard"

# Show system status
status:
	@echo "📊 Team Omega System Status"
	@echo "=========================="
	@echo "🔍 Checking MAVProxy..."
	@systemctl is-active mavproxy.service 2>/dev/null || echo "❌ MAVProxy not running"
	@echo "🛰️ Checking NTRIP client..."
	@systemctl is-active ntrip.service 2>/dev/null || echo "❌ NTRIP client not running"
	@echo "🔍 Checking fusion service..."
	@systemctl is-active fusion.service 2>/dev/null || echo "❌ Fusion service not running"
	@echo "🐳 Checking Docker services..."
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep astra || echo "❌ No Docker services running"

# Environment variables (set these in your shell or .env file)
EC2_KEY_PATH ?= ~/.ssh/astra-key.pem
EC2_USER ?= ubuntu
EC2_IP ?= your-ec2-ip-here
NUC_USER ?= astra
NUC_IP ?= your-nuc-ip-here
