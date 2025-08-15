#!/bin/bash
# Docker entrypoint script for Kasa Monitor
# Copyright (C) 2025 Kasa Monitor Contributors
# Licensed under GPL v3

set -e

echo "🔌 Starting Kasa Monitor in Docker..."
echo "🐧 Optimized for Raspberry Pi 5"
echo "=================================="

# Check if we're running on ARM64 (Raspberry Pi)
ARCH=$(uname -m)
echo "📟 Architecture: $ARCH"

# Create data directory if it doesn't exist
mkdir -p /app/data /app/logs

# Set up database path
export SQLITE_PATH=${SQLITE_PATH:-/app/data/kasa_monitor.db}

echo "💾 Database path: $SQLITE_PATH"

# Initialize database if it doesn't exist
if [ ! -f "$SQLITE_PATH" ]; then
    echo "🗄️  Initializing new database..."
fi

# Start backend in background
echo "🐍 Starting Python backend..."
cd /app
python backend/server.py &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to initialize..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/devices >/dev/null 2>&1; then
        echo "✅ Backend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start within 30 seconds"
        exit 1
    fi
    sleep 1
done

# Start frontend
echo "🎨 Starting Next.js frontend..."
cd /app/frontend
npm run start &
FRONTEND_PID=$!

# Wait for frontend to start
echo "⏳ Waiting for frontend to initialize..."
for i in {1..30}; do
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        echo "✅ Frontend is ready!"
        break
    fi
    sleep 1
done

echo ""
echo "🎉 Kasa Monitor is running in Docker!"
echo "=================================="
echo "🌐 Frontend:    http://localhost:3000"
echo "🔌 Backend API: http://localhost:8000"
echo "📚 API Docs:    http://localhost:8000/docs"
echo ""

# Check if this is first time setup
if [ ! -f "/app/data/kasa_monitor.db" ]; then
    echo "⚠️  FIRST TIME SETUP REQUIRED!"
    echo "   Visit http://your-pi-ip:3000 after startup"
    echo "   You'll be prompted to create an admin user"
    echo ""
fi

echo "💡 Features available:"
echo "   • Device discovery and monitoring"
echo "   • Advanced electricity rate calculations"
echo "   • User management with role-based access"
echo "   • SSL/HTTPS support"
echo "   • Cost tracking and analysis"
echo ""
echo "🐳 Container optimized for Raspberry Pi 5"
echo "📊 Monitor performance with: docker stats kasa-monitor"
echo ""

# Function to handle shutdown
cleanup() {
    echo ""
    echo "🛑 Shutting down Kasa Monitor..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "👋 Container stopped gracefully!"
    exit 0
}

# Set up trap for clean shutdown
trap cleanup SIGTERM SIGINT

# Wait for processes and handle signals
while true; do
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo "❌ Backend process died, shutting down..."
        kill $FRONTEND_PID 2>/dev/null || true
        exit 1
    fi
    
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "❌ Frontend process died, shutting down..."
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    
    sleep 5
done