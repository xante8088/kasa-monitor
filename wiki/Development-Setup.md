# Development Setup

Complete guide for setting up a Kasa Monitor development environment.

## Development Overview

```
┌─────────────────────────────────────┐
│     Development Stack               │
├─────────────────────────────────────┤
│  Frontend: Next.js + TypeScript     │
│  Backend: FastAPI + Python          │
│  Database: SQLite + InfluxDB        │
│  Container: Docker                  │
│  Testing: Jest + Pytest             │
└─────────────────────────────────────┘
```

## Prerequisites

### Required Software

- **Python** 3.8+ 
- **Node.js** 16+ and npm 7+
- **Docker** 20+ and Docker Compose
- **Git** 2.25+

### Optional Tools

- **VS Code** or preferred IDE
- **Postman** or similar for API testing
- **SQLite Browser** for database inspection
- **Python virtual environment** tool (venv, conda, pyenv)

## Initial Setup

### 1. Clone Repository

```bash
# Clone the repository
git clone https://github.com/xante8088/kasa-monitor.git
cd kasa-monitor

# Or fork first, then clone your fork
git clone https://github.com/YOUR_USERNAME/kasa-monitor.git
cd kasa-monitor
git remote add upstream https://github.com/xante8088/kasa-monitor.git
```

### 2. Python Backend Setup

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Install package in development mode
pip install -e .
```

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Return to root
cd ..
```

### 4. Environment Configuration

```bash
# Copy example environment file
cp .env.example .env.development

# Edit environment variables
nano .env.development
```

**.env.development example:**
```bash
# Application
NODE_ENV=development
DEBUG=true
LOG_LEVEL=debug

# Database
DATABASE_URL=sqlite:///./data/kasa_monitor.db
TEST_DATABASE_URL=sqlite:///./data/test.db

# API
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_URL=http://localhost:3000

# Security (generate your own keys!)
JWT_SECRET_KEY=your-development-secret-key-change-this
SESSION_SECRET=another-secret-key-change-this

# Device Discovery
DISCOVERY_ENABLED=true
DISCOVERY_BROADCAST=255.255.255.255

# Optional Services
REDIS_URL=redis://localhost:6379
INFLUXDB_URL=http://localhost:8086
```

### 5. Database Setup

```bash
# Create data directory
mkdir -p data

# Initialize database
python scripts/init_db.py

# Or use migrations
alembic upgrade head

# Seed with test data (optional)
python scripts/seed_data.py
```

## Development Workflow

### Running the Application

#### Method 1: Separate Services

```bash
# Terminal 1: Start backend
source venv/bin/activate
python backend/server.py

# Terminal 2: Start frontend
cd frontend
npm run dev

# Access at:
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

#### Method 2: Docker Compose

```bash
# Build and start all services
docker-compose -f docker-compose.dev.yml up --build

# Or run in background
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop services
docker-compose -f docker-compose.dev.yml down
```

**docker-compose.dev.yml:**
```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.dev
    volumes:
      - ./backend:/app/backend
      - ./data:/app/data
    ports:
      - "8000:8000"
    environment:
      - NODE_ENV=development
      - RELOAD=true
    command: uvicorn backend.server:app --reload --host 0.0.0.0 --port 8000

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=development
    command: npm run dev

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

  influxdb:
    image: influxdb:2.7-alpine
    ports:
      - "8086:8086"
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=admin
      - DOCKER_INFLUXDB_INIT_PASSWORD=password123
      - DOCKER_INFLUXDB_INIT_ORG=kasa-monitor
      - DOCKER_INFLUXDB_INIT_BUCKET=device-data
```

### Hot Reloading

Both frontend and backend support hot reloading in development:

**Backend (FastAPI):**
```python
# Automatic with --reload flag
uvicorn backend.server:app --reload

# Or in code
if __name__ == "__main__":
    uvicorn.run(
        "backend.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Enable hot reload
    )
```

**Frontend (Next.js):**
```json
// package.json
{
  "scripts": {
    "dev": "next dev",
    "dev:debug": "NODE_OPTIONS='--inspect' next dev"
  }
}
```

## IDE Configuration

### VS Code

**.vscode/settings.json:**
```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

**.vscode/launch.json:**
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "backend.server:app",
        "--reload",
        "--port",
        "8000"
      ],
      "jinja": true,
      "justMyCode": true
    },
    {
      "name": "Next.js: debug",
      "type": "node",
      "request": "launch",
      "program": "${workspaceFolder}/frontend/node_modules/.bin/next",
      "args": ["dev"],
      "cwd": "${workspaceFolder}/frontend",
      "console": "integratedTerminal"
    }
  ]
}
```

### PyCharm

1. **Create Python Interpreter:**
   - File → Settings → Project → Python Interpreter
   - Add interpreter → Virtualenv Environment
   - Select existing environment: `./venv`

2. **Configure Run Configuration:**
   - Run → Edit Configurations
   - Add new → Python
   - Script path: `backend/server.py`
   - Environment variables: Load from `.env.development`

## Testing

### Backend Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest tests/test_device_manager.py

# Run with verbose output
pytest -v

# Run only marked tests
pytest -m "not slow"

# Watch mode
ptw
```

**Writing Backend Tests:**
```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from backend.server import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_device_discovery():
    response = client.get("/api/devices/discover")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

### Frontend Testing

```bash
# Run tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch

# Run E2E tests
npm run test:e2e
```

**Writing Frontend Tests:**
```tsx
// tests/components/DeviceList.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { DeviceList } from '@/components/DeviceList';
import { server } from '@/mocks/server';
import { rest } from 'msw';

describe('DeviceList', () => {
  it('displays devices', async () => {
    render(<DeviceList />);
    
    await waitFor(() => {
      expect(screen.getByText('Living Room')).toBeInTheDocument();
    });
  });

  it('handles empty state', async () => {
    server.use(
      rest.get('/api/devices', (req, res, ctx) => {
        return res(ctx.json([]));
      })
    );

    render(<DeviceList />);
    
    await waitFor(() => {
      expect(screen.getByText('No devices found')).toBeInTheDocument();
    });
  });
});
```

## Database Management

### Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add device groups"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Database Access

```bash
# SQLite CLI
sqlite3 data/kasa_monitor.db

# Common queries
.tables
.schema devices
SELECT * FROM devices;
.exit

# Python shell
python
>>> from backend.database import get_db
>>> db = next(get_db())
>>> devices = db.execute("SELECT * FROM devices").fetchall()
```

## Debugging

### Backend Debugging

```python
# Use debugger
import pdb

def problematic_function():
    pdb.set_trace()  # Breakpoint
    # Code to debug
    
# Or use ipdb for better interface
import ipdb

def another_function():
    ipdb.set_trace()
```

### Frontend Debugging

```typescript
// Browser DevTools
console.log('Debug data:', data);
debugger; // Breakpoint

// React DevTools
// Install browser extension for component inspection

// VS Code debugging
// Set breakpoints in VS Code and use launch configuration
```

### API Debugging

```bash
# Test endpoints with curl
curl http://localhost:8000/api/devices

# Or with httpie
http GET localhost:8000/api/devices

# Use Postman or Insomnia for complex requests
```

## Code Quality

### Linting

```bash
# Python linting
flake8 backend/
black backend/ --check
isort backend/ --check-only
mypy backend/

# Frontend linting
npm run lint
npm run lint:fix

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

**.pre-commit-config.yaml:**
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.9

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=88]

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: [--profile=black]

  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.0.0
    hooks:
      - id: prettier
        files: \.(js|jsx|ts|tsx|json|css|scss|md)$
```

### Code Formatting

```bash
# Format Python code
black backend/
isort backend/

# Format TypeScript/JavaScript
npm run format

# Format specific files
black backend/server.py
prettier --write "frontend/src/**/*.{ts,tsx}"
```

## Performance Profiling

### Backend Profiling

```python
# Profile with cProfile
import cProfile
import pstats

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Code to profile
    expensive_operation()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)

# Or use line_profiler
# pip install line_profiler
@profile
def function_to_profile():
    # Code here
    pass

# Run with: kernprof -l -v script.py
```

### Frontend Profiling

```typescript
// React DevTools Profiler
// Use the Profiler tab in React DevTools

// Performance API
console.time('ComponentRender');
// Component code
console.timeEnd('ComponentRender');

// Chrome DevTools Performance tab
// Record and analyze performance
```

## Troubleshooting

### Common Issues

**Port already in use:**
```bash
# Find process using port
lsof -i :8000
lsof -i :3000

# Kill process
kill -9 <PID>

# Or change ports in .env
API_PORT=8001
FRONTEND_PORT=3001
```

**Module not found:**
```bash
# Reinstall dependencies
pip install -r requirements.txt
npm install

# Clear caches
pip cache purge
npm cache clean --force
```

**Database locked:**
```bash
# Close all connections
# Restart backend
# Or delete lock files
rm data/*.db-wal
rm data/*.db-shm
```

## Development Tools

### API Documentation

Access interactive API docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Database GUI

- **SQLite Browser**: https://sqlitebrowser.org/
- **DBeaver**: https://dbeaver.io/
- **TablePlus**: https://tableplus.com/

### API Testing

- **Postman**: https://www.postman.com/
- **Insomnia**: https://insomnia.rest/
- **Thunder Client** (VS Code extension)

## Best Practices

1. **Use virtual environments** for Python dependencies
2. **Keep dependencies updated** but test before updating
3. **Write tests** for new features
4. **Use type hints** in Python and TypeScript
5. **Follow code style** guidelines
6. **Document your code** with clear comments
7. **Use meaningful** commit messages
8. **Test locally** before pushing

## Related Pages

- [Contributing Guide](Contributing-Guide) - Contribution guidelines
- [Architecture Overview](Architecture-Overview) - System design
- [API Documentation](API-Documentation) - API reference
- [Plugin Development](Plugin-Development) - Creating plugins