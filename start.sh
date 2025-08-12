#!/bin/bash

# Kasa Monitor Startup Script
# Copyright (C) 2025 Kasa Monitor Contributors
# Licensed under GPL v3

set -e

echo "🔌 Starting Kasa Monitor..."
echo "=================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not installed"
    echo "   Please install Python 3.8 or later"
    exit 1
fi

# Check if Node.js is installed  
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js is required but not installed"
    echo "   Please install Node.js 16 or later"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "📚 Installing/updating Python dependencies..."
pip install -r requirements.txt

# Install Node dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "🎨 Installing Node.js dependencies..."
    npm install
fi

# Check if this is first time setup
SETUP_MSG=""
if [ ! -f "backend/kasa_monitor.db" ]; then
    SETUP_MSG="⚠️  FIRST TIME SETUP REQUIRED! 
   Visit http://localhost:3000 after startup
   You'll be prompted to create an admin user"
fi

# Start backend server
echo "🚀 Starting backend server..."
cd backend
python server.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start frontend server
echo "🎨 Starting frontend server..."
npm run dev &
FRONTEND_PID=$!

# Wait a moment for startup
sleep 2

echo
echo "✅ Kasa Monitor is running!"
echo "=================================="
echo "🌐 Frontend:    http://localhost:3000"
echo "🔌 Backend API: http://localhost:8000"
echo "📚 API Docs:    http://localhost:8000/docs"
echo

if [ ! -z "$SETUP_MSG" ]; then
    echo "$SETUP_MSG"
    echo
fi

echo "💡 Features available:"
echo "   • Device discovery and monitoring"
echo "   • Advanced electricity rate calculations"
echo "   • User management with role-based access"
echo "   • SSL/HTTPS support"
echo "   • Cost tracking and analysis"
echo
echo "Press Ctrl+C to stop all servers"
echo

# Function to handle shutdown
cleanup() {
    echo
    echo "🛑 Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "👋 Goodbye!"
    exit 0
}

# Set up trap for clean shutdown
trap cleanup INT TERM

# Wait for processes
wait $BACKEND_PID $FRONTEND_PID