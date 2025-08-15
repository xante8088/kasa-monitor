#!/bin/bash

# Kasa Monitor Local Test Environment Startup Script

echo "🏠 Starting Kasa Monitor Local Test Environment..."
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if port is in use
port_in_use() {
    lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null
}

# Check Python
echo -e "\n${YELLOW}Checking dependencies...${NC}"
if command_exists python3; then
    echo -e "${GREEN}✓${NC} Python3 found: $(python3 --version)"
else
    echo -e "${RED}✗${NC} Python3 not found. Please install Python 3.8+"
    exit 1
fi

# Check if Redis is running (optional)
if command_exists redis-cli; then
    if redis-cli ping >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Redis is running"
    else
        echo -e "${YELLOW}!${NC} Redis is installed but not running. Starting Redis..."
        if command_exists redis-server; then
            redis-server --daemonize yes
            sleep 2
            if redis-cli ping >/dev/null 2>&1; then
                echo -e "${GREEN}✓${NC} Redis started successfully"
            else
                echo -e "${YELLOW}!${NC} Could not start Redis. Cache features will be disabled."
            fi
        fi
    fi
else
    echo -e "${YELLOW}!${NC} Redis not found. Cache features will be disabled."
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "\n${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
fi

# Activate virtual environment
echo -e "\n${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓${NC} Virtual environment activated"

# Install/upgrade dependencies
echo -e "\n${YELLOW}Installing dependencies...${NC}"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo -e "${GREEN}✓${NC} Dependencies installed"

# Create necessary directories
echo -e "\n${YELLOW}Setting up directories...${NC}"
mkdir -p data backups logs
echo -e "${GREEN}✓${NC} Directories created"

# Check ports
echo -e "\n${YELLOW}Checking ports...${NC}"
if port_in_use 8000; then
    echo -e "${RED}✗${NC} Potr38000 is already in use"
    echo "Please stop the service using port 8000 or change the port in the script"
    exit 1
else
    echo -e "${GREEN}✓${NC} Port 8000 is available"
fi

# Set environment variables
export DATABASE_PATH="data/kasa_monitor.db"
export BACKUP_DIR="backups"
export REDIS_URL="redis://localhost:6379/0"
export APP_VERSION="2.0.0"
export ENVIRONMENT="development"
export LOG_LEVEL="INFO"

# Start the application
echo -e "\n${GREEN}Starting Kasa Monitor...${NC}"
echo "================================================"
echo -e "📍 Main Application: ${GREEN}http://localhost:8000${NC}"
echo -e "📊 Test Interface:  ${GREEN}http://localhost:8000/test${NC}"
echo -e "📚 API Docs:        ${GREEN}http://localhost:8000/docs${NC}"
echo -e "📈 Metrics:         ${GREEN}http://localhost:8000/metrics${NC}"
echo -e "🔧 Health Check:    ${GREEN}http://localhost:8000/health/detailed${NC}"
echo "================================================"
echo -e "\nPress ${YELLOW}Ctrl+C${NC} to stop the server\n"

# Start the FastAPI application
cd backend
python3 main.py
