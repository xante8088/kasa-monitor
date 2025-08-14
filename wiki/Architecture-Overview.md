# Architecture Overview

Comprehensive overview of Kasa Monitor's system architecture, design patterns, and technical implementation.

## System Architecture

```
┌────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │   UI     │ │  State   │ │   API    │ │   Auth   │     │
│  │Components│ │Management│ │  Client  │ │  Context │     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
└────────────────────────────────────────────────────────────┘
                              │
                              ▼
                     ┌──────────────┐
                     │   WebSocket  │
                     │   (Real-time)│
                     └──────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │   API    │ │  Device  │ │   Auth   │ │Scheduling│     │
│  │ Endpoints│ │ Manager  │ │  Manager │ │  Engine  │     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
└────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │  SQLite  │  │InfluxDB  │  │  Redis   │
        │(Metadata)│  │(Metrics) │  │ (Cache)  │
        └──────────┘  └──────────┘  └──────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   Kasa Devices   │
                    │  (Smart Plugs)   │
                    └──────────────────┘
```

## Core Components

### Frontend Layer

#### Next.js Application

```typescript
// Frontend structure
src/
├── app/                    # Next.js 13+ app directory
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Home page
│   ├── dashboard/         # Dashboard routes
│   ├── devices/           # Device management
│   └── api/               # API routes
├── components/            # React components
│   ├── ui/               # UI components
│   ├── charts/           # Chart components
│   └── layouts/          # Layout components
├── contexts/             # React contexts
│   ├── auth-context.tsx  # Authentication
│   └── theme-context.tsx # Theme management
├── hooks/                # Custom React hooks
├── lib/                  # Utility libraries
├── services/             # API services
└── types/                # TypeScript types
```

#### State Management

```typescript
// Zustand store example
import { create } from 'zustand';

interface DeviceStore {
  devices: Device[];
  selectedDevice: Device | null;
  loading: boolean;
  error: string | null;
  
  fetchDevices: () => Promise<void>;
  selectDevice: (device: Device) => void;
  updateDevice: (id: string, data: Partial<Device>) => Promise<void>;
}

const useDeviceStore = create<DeviceStore>((set, get) => ({
  devices: [],
  selectedDevice: null,
  loading: false,
  error: null,
  
  fetchDevices: async () => {
    set({ loading: true, error: null });
    try {
      const response = await fetch('/api/devices');
      const devices = await response.json();
      set({ devices, loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },
  
  selectDevice: (device) => set({ selectedDevice: device }),
  
  updateDevice: async (id, data) => {
    const response = await fetch(`/api/devices/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
    const updated = await response.json();
    
    set(state => ({
      devices: state.devices.map(d => 
        d.id === id ? updated : d
      )
    }));
  }
}));
```

### Backend Layer

#### FastAPI Application

```python
# Backend structure
backend/
├── __init__.py
├── server.py              # Main application
├── api/                   # API endpoints
│   ├── __init__.py
│   ├── devices.py        # Device endpoints
│   ├── auth.py           # Authentication
│   ├── costs.py          # Cost calculations
│   └── websocket.py      # WebSocket handlers
├── core/                  # Core functionality
│   ├── config.py         # Configuration
│   ├── security.py       # Security utilities
│   └── database.py       # Database setup
├── managers/              # Business logic
│   ├── device_manager.py # Device management
│   ├── auth_manager.py   # Authentication
│   └── rate_manager.py   # Rate calculations
├── models/                # Data models
│   ├── device.py         # Device models
│   ├── user.py           # User models
│   └── reading.py        # Reading models
├── services/              # External services
│   ├── discovery.py      # Device discovery
│   ├── influxdb.py       # InfluxDB client
│   └── redis.py          # Redis client
└── utils/                 # Utilities
    ├── scheduler.py      # Task scheduling
    └── logger.py         # Logging setup
```

#### Request Flow

```python
# Request processing pipeline
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Middleware stack
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {process_time:.3f}s")
    return response

# Dependency injection
async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = await verify_token(token)
    if not user:
        raise HTTPException(status_code=401)
    return user

# Route handler
@app.get("/api/devices")
async def get_devices(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return await device_manager.get_user_devices(user.id, db)
```

### Data Layer

#### Database Schema

```sql
-- Core tables structure
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT,
    role TEXT,
    created_at TIMESTAMP
);

CREATE TABLE devices (
    device_ip TEXT PRIMARY KEY,
    device_name TEXT,
    device_type TEXT,
    mac_address TEXT UNIQUE,
    is_active BOOLEAN,
    user_id INTEGER REFERENCES users(id)
);

CREATE TABLE readings (
    id INTEGER PRIMARY KEY,
    device_ip TEXT REFERENCES devices(device_ip),
    timestamp TIMESTAMP,
    power_w REAL,
    energy_kwh REAL,
    voltage_v REAL
);

-- Indexes for performance
CREATE INDEX idx_readings_device_time ON readings(device_ip, timestamp);
CREATE INDEX idx_devices_user ON devices(user_id);
```

#### Data Access Layer

```python
# Repository pattern
class DeviceRepository:
    def __init__(self, db: Session):
        self.db = db
    
    async def get_all(self) -> List[Device]:
        return self.db.query(DeviceModel).all()
    
    async def get_by_ip(self, device_ip: str) -> Optional[Device]:
        return self.db.query(DeviceModel).filter(
            DeviceModel.device_ip == device_ip
        ).first()
    
    async def create(self, device: DeviceCreate) -> Device:
        db_device = DeviceModel(**device.dict())
        self.db.add(db_device)
        self.db.commit()
        self.db.refresh(db_device)
        return db_device
    
    async def update(self, device_ip: str, data: DeviceUpdate) -> Device:
        device = await self.get_by_ip(device_ip)
        for key, value in data.dict(exclude_unset=True).items():
            setattr(device, key, value)
        self.db.commit()
        return device
```

## Communication Patterns

### REST API

```yaml
# API structure
/api:
  /devices:
    GET: List all devices
    POST: Add new device
    /discover:
      GET: Discover devices
    /{device_ip}:
      GET: Get device details
      PATCH: Update device
      DELETE: Remove device
      /toggle:
        POST: Toggle device state
      /stats:
        GET: Get device statistics
  
  /auth:
    /login:
      POST: User login
    /logout:
      POST: User logout
    /refresh:
      POST: Refresh token
    /setup:
      POST: Initial setup
  
  /costs:
    GET: Get cost summary
    /calculate:
      POST: Calculate costs
    /rates:
      GET: Get rates
      POST: Update rates
```

### WebSocket Communication

```python
# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    async def disconnect(self, client_id: str):
        del self.active_connections[client_id]
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Process incoming messages
            await manager.broadcast({"type": "update", "data": data})
    except WebSocketDisconnect:
        await manager.disconnect(client_id)
```

### Event-Driven Architecture

```python
# Event system
from typing import Dict, List, Callable
import asyncio

class EventBus:
    def __init__(self):
        self.listeners: Dict[str, List[Callable]] = {}
    
    def on(self, event: str, callback: Callable):
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append(callback)
    
    async def emit(self, event: str, data: any):
        if event in self.listeners:
            tasks = [
                asyncio.create_task(callback(data))
                for callback in self.listeners[event]
            ]
            await asyncio.gather(*tasks)

# Usage
event_bus = EventBus()

# Register listeners
event_bus.on('device.connected', handle_device_connected)
event_bus.on('device.data', handle_device_data)
event_bus.on('alert.triggered', handle_alert)

# Emit events
await event_bus.emit('device.connected', {'ip': '192.168.1.100'})
```

## Security Architecture

### Authentication Flow

```
┌──────┐     ┌──────────┐     ┌─────────┐     ┌──────────┐
│Client│────▶│  Login   │────▶│Validate │────▶│  Issue   │
└──────┘     │ Request  │     │Creds    │     │  Token   │
             └──────────┘     └─────────┘     └──────────┘
                                                     │
                                                     ▼
             ┌──────────┐     ┌─────────┐     ┌──────────┐
             │  Store   │◀────│ Return  │◀────│  Sign    │
             │  Token   │     │ Token   │     │  Token   │
             └──────────┘     └─────────┘     └──────────┘
                   │
                   ▼
             ┌──────────┐     ┌─────────┐     ┌──────────┐
             │   API    │────▶│ Verify  │────▶│  Grant   │
             │ Request  │     │ Token   │     │ Access   │
             └──────────┘     └─────────┘     └──────────┘
```

### JWT Implementation

```python
# Token management
from datetime import datetime, timedelta
from jose import JWTError, jwt

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
```

## Deployment Architecture

### Container Architecture

```yaml
# Multi-stage Docker build
FROM node:18-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.9-slim AS backend-builder
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.9-slim
WORKDIR /app
COPY --from=backend-builder /usr/local/lib/python3.9 /usr/local/lib/python3.9
COPY --from=frontend-builder /app/out /app/frontend/out
COPY backend/ ./backend/
EXPOSE 3000 8000
CMD ["python", "-m", "backend.server"]
```

### Scaling Architecture

```yaml
# Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kasa-monitor
spec:
  replicas: 3
  selector:
    matchLabels:
      app: kasa-monitor
  template:
    spec:
      containers:
      - name: app
        image: kasa-monitor:latest
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: kasa-monitor-service
spec:
  type: LoadBalancer
  selector:
    app: kasa-monitor
  ports:
    - port: 80
      targetPort: 3000
```

## Performance Optimization

### Caching Strategy

```python
# Multi-level caching
class CacheManager:
    def __init__(self):
        self.memory_cache = {}  # L1 cache
        self.redis_client = redis.Redis()  # L2 cache
    
    async def get(self, key: str):
        # Check L1 cache
        if key in self.memory_cache:
            return self.memory_cache[key]
        
        # Check L2 cache
        value = self.redis_client.get(key)
        if value:
            self.memory_cache[key] = value
            return value
        
        return None
    
    async def set(self, key: str, value: any, ttl: int = 300):
        # Set in both caches
        self.memory_cache[key] = value
        self.redis_client.setex(key, ttl, value)
```

### Database Optimization

```python
# Connection pooling
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)

# Query optimization
from sqlalchemy.orm import joinedload

# Eager loading
devices = db.query(Device).options(
    joinedload(Device.readings)
).all()

# Bulk operations
db.bulk_insert_mappings(Reading, readings_data)
db.commit()
```

## Monitoring and Observability

### Logging Architecture

```python
# Structured logging
import structlog

logger = structlog.get_logger()

logger.info(
    "device_polled",
    device_ip="192.168.1.100",
    power_w=150.5,
    response_time=0.234
)

# Log aggregation
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'app.log',
            'maxBytes': 10485760,
            'backupCount': 5
        },
        'elasticsearch': {
            'class': 'elasticsearch_handler.ElasticsearchHandler',
            'hosts': ['localhost:9200'],
            'index': 'kasa-monitor'
        }
    }
}
```

### Metrics Collection

```python
# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

request_count = Counter('http_requests_total', 'Total HTTP requests')
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')
active_devices = Gauge('active_devices', 'Number of active devices')

@app.middleware("http")
async def track_metrics(request: Request, call_next):
    with request_duration.time():
        response = await call_next(request)
    request_count.inc()
    return response
```

## Design Patterns

### Repository Pattern

```python
# Abstract repository
from abc import ABC, abstractmethod

class Repository(ABC):
    @abstractmethod
    async def get(self, id: str):
        pass
    
    @abstractmethod
    async def create(self, entity: dict):
        pass
    
    @abstractmethod
    async def update(self, id: str, entity: dict):
        pass
    
    @abstractmethod
    async def delete(self, id: str):
        pass

# Concrete implementation
class DeviceRepository(Repository):
    def __init__(self, db: Session):
        self.db = db
    
    async def get(self, device_ip: str):
        return self.db.query(Device).filter(
            Device.device_ip == device_ip
        ).first()
```

### Factory Pattern

```python
# Device factory
class DeviceFactory:
    @staticmethod
    def create_device(device_type: str, **kwargs):
        if device_type == "plug":
            return SmartPlug(**kwargs)
        elif device_type == "switch":
            return SmartSwitch(**kwargs)
        elif device_type == "bulb":
            return SmartBulb(**kwargs)
        else:
            raise ValueError(f"Unknown device type: {device_type}")
```

### Observer Pattern

```python
# Observable device
class ObservableDevice:
    def __init__(self):
        self._observers = []
        self._state = None
    
    def attach(self, observer):
        self._observers.append(observer)
    
    def notify(self):
        for observer in self._observers:
            observer.update(self._state)
    
    def set_state(self, state):
        self._state = state
        self.notify()

# Observer
class DeviceMonitor:
    def update(self, state):
        if state['power_w'] > 1000:
            send_alert(f"High power usage: {state['power_w']}W")
```

## Technology Stack

### Core Technologies

- **Frontend**: Next.js 13+, React 18, TypeScript, TailwindCSS
- **Backend**: FastAPI, Python 3.9+, Pydantic, SQLAlchemy
- **Database**: SQLite (primary), InfluxDB (time-series), Redis (cache)
- **Container**: Docker, Docker Compose
- **Testing**: Jest, Pytest, React Testing Library
- **CI/CD**: GitHub Actions, Docker Hub

### Key Libraries

**Frontend:**
- `zustand` - State management
- `react-query` - Data fetching
- `recharts` - Charts and graphs
- `react-hook-form` - Form handling
- `next-auth` - Authentication

**Backend:**
- `python-kasa` - Device communication
- `alembic` - Database migrations
- `celery` - Task queue
- `prometheus-client` - Metrics
- `structlog` - Structured logging

## Related Pages

- [Development Setup](Development-Setup) - Development environment
- [API Documentation](API-Documentation) - API reference
- [Database Schema](Database-Schema) - Database design
- [Plugin Development](Plugin-Development) - Extension architecture