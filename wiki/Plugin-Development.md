# Plugin Development

Guide for developing plugins and extensions for Kasa Monitor.

## Plugin System Overview

```
┌─────────────────────────────────────┐
│         Plugin Architecture         │
├─────────────────────────────────────┤
│  1. Plugin Discovery & Loading      │
│  2. Hook System                     │
│  3. API Extensions                  │
│  4. UI Components                   │
│  5. Data Processors                 │
└─────────────────────────────────────┘
```

## Getting Started

### Plugin Structure

```
my-plugin/
├── manifest.json          # Plugin metadata
├── index.js              # Main entry point
├── backend/              # Backend components
│   ├── __init__.py
│   ├── api.py           # API endpoints
│   ├── hooks.py         # Hook implementations
│   └── processors.py    # Data processors
├── frontend/             # Frontend components
│   ├── components/      # React components
│   ├── hooks/          # React hooks
│   └── styles/         # CSS/styles
├── config/              # Configuration files
│   └── default.json
├── tests/               # Plugin tests
├── docs/                # Documentation
└── README.md
```

### Plugin Manifest

**manifest.json:**
```json
{
  "name": "my-awesome-plugin",
  "version": "1.0.0",
  "description": "Adds awesome features to Kasa Monitor",
  "author": "Your Name",
  "license": "MIT",
  "homepage": "https://github.com/username/my-plugin",
  
  "kasa": {
    "minVersion": "1.0.0",
    "maxVersion": "2.0.0"
  },
  
  "main": "index.js",
  "backend": "backend/__init__.py",
  
  "permissions": [
    "devices.read",
    "devices.write",
    "api.extend",
    "ui.dashboard"
  ],
  
  "dependencies": {
    "axios": "^1.0.0"
  },
  
  "configuration": {
    "schema": "./config/schema.json",
    "defaults": "./config/default.json"
  },
  
  "hooks": [
    "device.discovered",
    "device.data.received",
    "dashboard.render"
  ],
  
  "api": {
    "endpoints": [
      {
        "path": "/api/plugins/my-plugin",
        "handler": "backend.api.router"
      }
    ]
  },
  
  "ui": {
    "dashboard": {
      "widgets": [
        {
          "id": "my-widget",
          "component": "frontend/components/MyWidget",
          "title": "My Widget",
          "size": "medium"
        }
      ]
    },
    "pages": [
      {
        "path": "/plugins/my-plugin",
        "component": "frontend/components/MainPage",
        "title": "My Plugin",
        "icon": "puzzle"
      }
    ]
  }
}
```

## Backend Plugin Development

### Basic Plugin Structure

```python
# backend/__init__.py
from kasa_monitor.plugin import Plugin
from .hooks import MyHooks
from .api import router
from .processors import DataProcessor

class MyPlugin(Plugin):
    """Main plugin class."""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "my-awesome-plugin"
        self.version = "1.0.0"
        self.hooks = MyHooks()
        self.processor = DataProcessor()
    
    async def initialize(self):
        """Initialize plugin."""
        self.logger.info(f"Initializing {self.name}")
        
        # Register hooks
        self.register_hook('device.discovered', self.hooks.on_device_discovered)
        self.register_hook('device.data.received', self.hooks.on_data_received)
        
        # Register API routes
        self.register_api_router(router, prefix="/my-plugin")
        
        # Register data processor
        self.register_processor('my-processor', self.processor)
    
    async def start(self):
        """Start plugin."""
        self.logger.info(f"Starting {self.name}")
        await self.processor.start()
    
    async def stop(self):
        """Stop plugin."""
        self.logger.info(f"Stopping {self.name}")
        await self.processor.stop()
    
    def get_status(self) -> dict:
        """Get plugin status."""
        return {
            "running": self.is_running,
            "processor_status": self.processor.get_status()
        }

# Export plugin
plugin = MyPlugin
```

### Hook System

```python
# backend/hooks.py
from kasa_monitor.hooks import Hook
from typing import Any, Dict

class MyHooks:
    """Plugin hook implementations."""
    
    async def on_device_discovered(self, device: Dict[str, Any]) -> Dict[str, Any]:
        """
        Called when a new device is discovered.
        
        Args:
            device: Device information
            
        Returns:
            Modified device information
        """
        # Add custom fields
        device['custom_field'] = 'custom_value'
        
        # Perform custom validation
        if self.is_supported_device(device):
            device['plugin_supported'] = True
        
        return device
    
    async def on_data_received(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Called when device data is received.
        
        Args:
            data: Device data
            
        Returns:
            Modified or enriched data
        """
        # Process data
        data['processed_value'] = self.process_value(data.get('power_w', 0))
        
        # Add calculations
        if 'power_w' in data:
            data['power_kwh'] = data['power_w'] / 1000
        
        return data
    
    async def on_before_save(self, data: Dict[str, Any]) -> bool:
        """
        Called before data is saved to database.
        
        Returns:
            True to continue, False to skip
        """
        # Validate data
        if not self.validate_data(data):
            return False
        
        # Transform data
        data['timestamp'] = self.normalize_timestamp(data['timestamp'])
        
        return True
    
    def is_supported_device(self, device: Dict[str, Any]) -> bool:
        """Check if device is supported by plugin."""
        supported_models = ['HS110', 'KP115']
        return device.get('model') in supported_models
    
    def process_value(self, value: float) -> float:
        """Process power value."""
        # Apply custom calculation
        return value * 1.05  # 5% adjustment
```

### API Extensions

```python
# backend/api.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from kasa_monitor.auth import get_current_user
from kasa_monitor.database import get_db

router = APIRouter()

class PluginSettings(BaseModel):
    enabled: bool
    threshold: float
    notification_email: Optional[str]

class DeviceExtension(BaseModel):
    device_ip: str
    custom_name: str
    category: str
    tags: List[str]

@router.get("/status")
async def get_plugin_status(user = Depends(get_current_user)):
    """Get plugin status."""
    return {
        "status": "active",
        "version": "1.0.0",
        "devices_monitored": 10
    }

@router.get("/settings")
async def get_settings(user = Depends(get_current_user)):
    """Get plugin settings."""
    settings = await load_user_settings(user.id)
    return settings

@router.post("/settings")
async def update_settings(
    settings: PluginSettings,
    user = Depends(get_current_user)
):
    """Update plugin settings."""
    await save_user_settings(user.id, settings.dict())
    return {"status": "updated"}

@router.get("/devices")
async def get_extended_devices(
    db = Depends(get_db),
    user = Depends(get_current_user)
):
    """Get devices with plugin extensions."""
    devices = await get_user_devices(user.id, db)
    
    # Add plugin-specific data
    for device in devices:
        device['extensions'] = await get_device_extensions(device['device_ip'])
    
    return devices

@router.post("/devices/{device_ip}/extend")
async def extend_device(
    device_ip: str,
    extension: DeviceExtension,
    user = Depends(get_current_user)
):
    """Add plugin extensions to device."""
    # Verify device ownership
    if not await user_owns_device(user.id, device_ip):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Save extensions
    await save_device_extensions(device_ip, extension.dict())
    
    return {"status": "extended"}

@router.get("/analytics")
async def get_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user = Depends(get_current_user)
):
    """Get plugin analytics."""
    data = await calculate_analytics(
        user.id,
        start_date,
        end_date
    )
    
    return {
        "period": f"{start_date} to {end_date}",
        "metrics": data
    }
```

### Data Processors

```python
# backend/processors.py
from kasa_monitor.processor import DataProcessor
import asyncio
from typing import Dict, Any

class CustomDataProcessor(DataProcessor):
    """Custom data processor for plugin."""
    
    def __init__(self):
        super().__init__()
        self.processing_queue = asyncio.Queue()
        self.is_running = False
    
    async def start(self):
        """Start processor."""
        self.is_running = True
        asyncio.create_task(self.process_loop())
    
    async def stop(self):
        """Stop processor."""
        self.is_running = False
    
    async def process_loop(self):
        """Main processing loop."""
        while self.is_running:
            try:
                # Get data from queue
                data = await asyncio.wait_for(
                    self.processing_queue.get(),
                    timeout=1.0
                )
                
                # Process data
                processed = await self.process_data(data)
                
                # Store or forward processed data
                await self.store_processed_data(processed)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Processing error: {e}")
    
    async def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming data.
        
        Args:
            data: Raw data
            
        Returns:
            Processed data
        """
        processed = data.copy()
        
        # Apply transformations
        if 'power_w' in data:
            processed['power_adjusted'] = self.adjust_power(data['power_w'])
            processed['efficiency'] = self.calculate_efficiency(data['power_w'])
        
        # Add metadata
        processed['processed_at'] = datetime.utcnow()
        processed['processor_version'] = '1.0.0'
        
        return processed
    
    def adjust_power(self, power: float) -> float:
        """Adjust power reading based on calibration."""
        calibration_factor = 1.02  # 2% adjustment
        return power * calibration_factor
    
    def calculate_efficiency(self, power: float) -> float:
        """Calculate device efficiency."""
        # Example calculation
        max_power = 1800  # Maximum rated power
        return (power / max_power) * 100
    
    async def store_processed_data(self, data: Dict[str, Any]):
        """Store processed data."""
        # Store in database or forward to another service
        await self.db.store_plugin_data('my-plugin', data)
    
    def get_status(self) -> Dict[str, Any]:
        """Get processor status."""
        return {
            "running": self.is_running,
            "queue_size": self.processing_queue.qsize(),
            "processed_count": self.processed_count
        }
```

## Frontend Plugin Development

### React Components

```typescript
// frontend/components/MyWidget.tsx
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { usePluginData } from '../hooks/usePluginData';

export const MyWidget: React.FC = () => {
  const { data, loading, error } = usePluginData();
  const [settings, setSettings] = useState({});
  
  useEffect(() => {
    // Load plugin settings
    loadSettings();
  }, []);
  
  const loadSettings = async () => {
    const response = await fetch('/api/plugins/my-plugin/settings');
    const data = await response.json();
    setSettings(data);
  };
  
  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>My Plugin Widget</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <span className="font-semibold">Status:</span>
            <span className="ml-2">{data.status}</span>
          </div>
          <div>
            <span className="font-semibold">Devices:</span>
            <span className="ml-2">{data.deviceCount}</span>
          </div>
          <CustomChart data={data.analytics} />
        </div>
      </CardContent>
    </Card>
  );
};

// Custom chart component
const CustomChart: React.FC<{ data: any }> = ({ data }) => {
  return (
    <div className="h-64">
      {/* Chart implementation */}
    </div>
  );
};
```

### Custom Hooks

```typescript
// frontend/hooks/usePluginData.ts
import { useState, useEffect } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';

interface PluginData {
  status: string;
  deviceCount: number;
  analytics: any;
}

export const usePluginData = () => {
  const [data, setData] = useState<PluginData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  
  const ws = useWebSocket('/ws/plugins/my-plugin');
  
  useEffect(() => {
    fetchData();
    
    // Subscribe to WebSocket updates
    if (ws) {
      ws.on('update', handleUpdate);
    }
    
    return () => {
      if (ws) {
        ws.off('update', handleUpdate);
      }
    };
  }, [ws]);
  
  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/plugins/my-plugin/status');
      
      if (!response.ok) {
        throw new Error('Failed to fetch data');
      }
      
      const data = await response.json();
      setData(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleUpdate = (update: Partial<PluginData>) => {
    setData(prev => prev ? { ...prev, ...update } : null);
  };
  
  return { data, loading, error, refetch: fetchData };
};
```

### Plugin Pages

```typescript
// frontend/components/MainPage.tsx
import React from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { SettingsPanel } from './SettingsPanel';
import { AnalyticsPanel } from './AnalyticsPanel';
import { DevicesPanel } from './DevicesPanel';

export const MainPage: React.FC = () => {
  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">My Awesome Plugin</h1>
      
      <Tabs defaultValue="dashboard">
        <TabsList>
          <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
          <TabsTrigger value="devices">Devices</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>
        
        <TabsContent value="dashboard">
          <DashboardContent />
        </TabsContent>
        
        <TabsContent value="devices">
          <DevicesPanel />
        </TabsContent>
        
        <TabsContent value="analytics">
          <AnalyticsPanel />
        </TabsContent>
        
        <TabsContent value="settings">
          <SettingsPanel />
        </TabsContent>
      </Tabs>
    </div>
  );
};

const DashboardContent: React.FC = () => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <StatCard title="Active Devices" value="12" />
      <StatCard title="Total Savings" value="$45.67" />
      <StatCard title="Efficiency" value="92%" />
    </div>
  );
};

const StatCard: React.FC<{ title: string; value: string }> = ({ title, value }) => {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-sm font-medium text-gray-500">{title}</h3>
      <p className="text-2xl font-bold mt-2">{value}</p>
    </div>
  );
};
```

## Plugin Configuration

### Configuration Schema

```json
// config/schema.json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "enabled": {
      "type": "boolean",
      "default": true,
      "description": "Enable or disable the plugin"
    },
    "apiKey": {
      "type": "string",
      "description": "API key for external service"
    },
    "threshold": {
      "type": "number",
      "minimum": 0,
      "maximum": 100,
      "default": 50,
      "description": "Alert threshold percentage"
    },
    "notifications": {
      "type": "object",
      "properties": {
        "email": {
          "type": "boolean",
          "default": true
        },
        "push": {
          "type": "boolean",
          "default": false
        }
      }
    },
    "advanced": {
      "type": "object",
      "properties": {
        "pollingInterval": {
          "type": "integer",
          "minimum": 10,
          "default": 60,
          "description": "Polling interval in seconds"
        },
        "retryAttempts": {
          "type": "integer",
          "minimum": 0,
          "maximum": 10,
          "default": 3
        }
      }
    }
  },
  "required": ["enabled"]
}
```

### Default Configuration

```json
// config/default.json
{
  "enabled": true,
  "threshold": 50,
  "notifications": {
    "email": true,
    "push": false
  },
  "advanced": {
    "pollingInterval": 60,
    "retryAttempts": 3
  }
}
```

## Plugin Testing

### Unit Tests

```python
# tests/test_hooks.py
import pytest
from unittest.mock import Mock, patch
from backend.hooks import MyHooks

@pytest.fixture
def hooks():
    return MyHooks()

@pytest.mark.asyncio
async def test_device_discovered_hook(hooks):
    """Test device discovered hook."""
    device = {
        'device_ip': '192.168.1.100',
        'model': 'HS110'
    }
    
    result = await hooks.on_device_discovered(device)
    
    assert 'custom_field' in result
    assert result['plugin_supported'] is True

@pytest.mark.asyncio
async def test_unsupported_device(hooks):
    """Test unsupported device handling."""
    device = {
        'device_ip': '192.168.1.101',
        'model': 'UNKNOWN'
    }
    
    result = await hooks.on_device_discovered(device)
    
    assert 'plugin_supported' not in result or result['plugin_supported'] is False
```

### Integration Tests

```python
# tests/test_integration.py
import pytest
from fastapi.testclient import TestClient
from kasa_monitor.app import app
from backend import plugin

@pytest.fixture
def client():
    # Initialize plugin
    plugin_instance = plugin({})
    app.include_plugin(plugin_instance)
    
    return TestClient(app)

def test_plugin_status_endpoint(client):
    """Test plugin status endpoint."""
    response = client.get("/api/plugins/my-plugin/status")
    
    assert response.status_code == 200
    assert response.json()["status"] == "active"

def test_plugin_settings(client, auth_token):
    """Test plugin settings endpoints."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Get settings
    response = client.get("/api/plugins/my-plugin/settings", headers=headers)
    assert response.status_code == 200
    
    # Update settings
    new_settings = {"enabled": True, "threshold": 75}
    response = client.post(
        "/api/plugins/my-plugin/settings",
        json=new_settings,
        headers=headers
    )
    assert response.status_code == 200
```

## Plugin Distribution

### Publishing

```bash
# Package plugin
npm run build
python setup.py sdist bdist_wheel

# Create release archive
tar -czf my-plugin-v1.0.0.tar.gz \
  manifest.json \
  index.js \
  backend/ \
  frontend/dist/ \
  config/

# Upload to registry
npm publish
# or
pip upload dist/*
```

### Installation

```bash
# Install from registry
kasa-monitor plugin install my-awesome-plugin

# Install from file
kasa-monitor plugin install ./my-plugin-v1.0.0.tar.gz

# Install from GitHub
kasa-monitor plugin install github:username/my-plugin

# List installed plugins
kasa-monitor plugin list

# Enable/disable plugin
kasa-monitor plugin enable my-awesome-plugin
kasa-monitor plugin disable my-awesome-plugin

# Remove plugin
kasa-monitor plugin remove my-awesome-plugin
```

## Best Practices

1. **Follow Naming Conventions** - Use consistent naming
2. **Handle Errors Gracefully** - Don't crash the main app
3. **Respect Permissions** - Only access allowed resources
4. **Optimize Performance** - Don't block main thread
5. **Document Everything** - Clear API and usage docs
6. **Test Thoroughly** - Unit and integration tests
7. **Version Compatibility** - Support multiple versions
8. **Security First** - Validate all inputs

## Plugin Examples

### Weather Integration Plugin

```python
# Integrates weather data with energy usage
class WeatherPlugin(Plugin):
    async def on_data_received(self, data):
        weather = await self.get_weather(data['device_location'])
        data['temperature'] = weather['temperature']
        data['humidity'] = weather['humidity']
        return data
```

### Smart Scheduling Plugin

```python
# Optimizes device schedules based on usage patterns
class SmartScheduler(Plugin):
    async def analyze_patterns(self, device_ip):
        history = await self.get_device_history(device_ip)
        pattern = self.ml_model.predict(history)
        return self.generate_schedule(pattern)
```

### Energy Optimization Plugin

```python
# Reduces energy consumption through intelligent control
class EnergyOptimizer(Plugin):
    async def optimize(self, devices):
        for device in devices:
            if self.should_turn_off(device):
                await self.turn_off_device(device['device_ip'])
```

## Related Pages

- [Architecture Overview](Architecture-Overview) - System architecture
- [API Documentation](API-Documentation) - Core API reference
- [Contributing Guide](Contributing-Guide) - Contribution guidelines
- [Development Setup](Development-Setup) - Development environment