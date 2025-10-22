# Multi-stage Dockerfile for Kasa Monitor - Optimized for Raspberry Pi 5
# Copyright (C) 2025 Kasa Monitor Contributors
# Licensed under GPL v3
# syntax=docker/dockerfile:1

# Stage 1: Build Frontend
FROM node:25-alpine AS frontend-builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install ALL dependencies with BuildKit cache mount
RUN --mount=type=cache,target=/root/.npm,id=npm-frontend \
    npm ci --no-audit --no-fund --prefer-offline

# Copy frontend source
COPY src/ ./src/

# Copy public directory (now exists with .gitkeep)
COPY public/ ./public/

# Copy Next.js configuration files
COPY next.config.js ./
COPY tailwind.config.js ./
COPY tsconfig.json ./
COPY postcss.config.js ./
COPY next-env.d.ts ./

# Build the frontend
RUN npm run build

# Stage 2: Python Backend Base
FROM python:3.14-slim AS backend-base

# Install system dependencies for ARM64/Raspberry Pi
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY backend/requirements.txt ./

# Install Python dependencies with BuildKit cache mount
RUN --mount=type=cache,target=/root/.cache/pip,id=pip-backend \
    --mount=type=cache,target=/tmp/pip-build,id=pip-build-backend \
    pip install --no-cache-dir -r requirements.txt

# Stage 3: Final Runtime Image
FROM python:3.14-slim AS runtime

# Install Node.js and runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && node --version \
    && npm --version

# Create app user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy Python dependencies from backend-base
COPY --from=backend-base /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=backend-base /usr/local/bin /usr/local/bin

# Copy backend source
COPY backend/ ./backend/
COPY LICENSE ./
COPY README.md ./

# Copy built frontend from frontend-builder
COPY --from=frontend-builder /app/.next ./frontend/.next
COPY --from=frontend-builder /app/public ./frontend/public
COPY --from=frontend-builder /app/package.json ./frontend/
COPY --from=frontend-builder /app/next.config.js ./frontend/
COPY --from=frontend-builder /app/node_modules ./frontend/node_modules

# Copy startup scripts
COPY start.sh ./
COPY docker-entrypoint.sh ./

# Make scripts executable
RUN chmod +x start.sh docker-entrypoint.sh

# Create directories and set permissions
RUN mkdir -p /app/data /app/logs \
    && chown -R appuser:appuser /app \
    && chmod 755 /app/data /app/logs

# Expose ports
EXPOSE 5272 3000

# Set environment variables
ENV PYTHONPATH=/app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV SQLITE_PATH=/app/data/kasa_monitor.db

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:5272/health || exit 1

# Use app user
USER appuser

# Default command
CMD ["./docker-entrypoint.sh"]