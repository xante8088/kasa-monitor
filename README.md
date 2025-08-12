# Kasa Monitor

A comprehensive web application for monitoring TP-Link Kasa smart devices with advanced electricity cost tracking, user management, and SSL support.

## ✨ Features

### 🔌 Device Management
- **Auto Discovery**: Find Kasa devices on your network automatically
- **Real-time Monitoring**: Live power, voltage, and energy data
- **Device Control**: Turn devices on/off remotely
- **Persistent Storage**: Devices remain saved between sessions
- **IP Management**: Update device IPs when they change

### 💰 Advanced Cost Tracking
- **Complex Rate Structures**: Support for 6+ electricity rate types
- **Time-of-Use Rates**: Peak/off-peak pricing
- **Tiered Usage**: Progressive pricing based on consumption
- **Seasonal Rates**: Different rates by time of year
- **Combined Rates**: Mix multiple rate types
- **Cost Analysis**: Track daily, monthly, and total costs

### 👥 User Management & Security
- **Role-Based Access**: Admin, Operator, Viewer, and Guest roles
- **JWT Authentication**: Secure token-based authentication
- **Granular Permissions**: Fine-grained access control
- **SSL/HTTPS Support**: Full certificate management
- **Network Restrictions**: Local-only access options

### 📊 Data & Visualization
- **Interactive Charts**: Power trends, voltage stability, energy patterns
- **Historical Data**: SQLite + optional InfluxDB support
- **Real-time Updates**: WebSocket connections for live data
- **Export Capabilities**: Data export and analysis tools

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+** with pip
- **Node.js 16+** with npm
- (Optional) InfluxDB for enhanced time-series data

### One-Command Setup
```bash
chmod +x start.sh && ./start.sh
```

That's it! The script will:
- ✅ Create Python virtual environment
- ✅ Install all dependencies
- ✅ Start both backend and frontend servers
- ✅ Show you the URLs to access the application

### Manual Installation

If you prefer manual setup:

```bash
# 1. Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install Node.js dependencies
npm install

# 4. Start backend (Terminal 1)
cd backend && python server.py

# 5. Start frontend (Terminal 2) 
npm run dev
```

## Configuration

### Environment Variables (Optional)

Create a `.env` file in the root directory:

```env
# SQLite Database (default: kasa_monitor.db)
SQLITE_PATH=kasa_monitor.db

# InfluxDB Configuration (optional)
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your-influxdb-token
INFLUXDB_ORG=kasa-monitor
INFLUXDB_BUCKET=device-data
```

## Running the Application

### Start both backend and frontend:

```bash
# Terminal 1: Start the backend server
python backend/server.py

# Terminal 2: Start the frontend development server
npm run dev
```

Or use the provided startup script:

```bash
./start.sh
```

Access the application at `http://localhost:3000`

## First-Time Setup

After running the startup script, you'll need to complete the initial configuration:

1. **Create Admin Account**:
   - Open http://localhost:3000 in your browser
   - You'll be prompted to create the first administrator account
   - Enter username, email, full name, and secure password
   - This admin can later create additional users with different roles

2. **Configure User Access** (Optional):
   - Admin can create users with roles: Admin, Operator, Viewer, Guest
   - Set granular permissions for rate management, device control, etc.
   - Configure network access restrictions if needed

3. **SSL Configuration** (Optional):
   - Import SSL certificates for HTTPS access
   - Configure secure connections for production use

## Usage

1. **Device Discovery**:
   - Click "Discover Devices" to find Kasa devices on your network
   - Optionally provide TP-Link Cloud credentials for newer devices
   - Discovered devices are automatically saved for future monitoring

2. **Configure Electricity Rates**:
   - Click "Electricity Rates" to set up your pricing structure
   - Choose from 6 rate types: Flat, Time-of-Use, Tiered, Seasonal, Combined, Seasonal+Tiered
   - Set usage ranges for tiered pricing (e.g., 0-100 kWh, 101-1000 kWh, 1000+ kWh)

3. **Monitor Devices**:
   - View real-time power consumption on the main dashboard
   - Click on any device for detailed information and interactive charts
   - Track voltage, current, power, and energy consumption over time

4. **Device Management**:
   - Enable/disable monitoring for specific devices
   - Update device IP addresses when they change
   - Remove devices from monitoring if no longer needed

5. **Control Devices**:
   - Turn devices on/off from the device detail view
   - Monitor immediate power consumption changes
   - Control multiple devices from the main dashboard

6. **Analyze Costs**:
   - View real-time cost calculations based on your rate structure
   - Track daily, monthly, and total electricity costs
   - Identify top energy consumers and usage patterns
   - Export data for further analysis

## Architecture

### Backend (Python/FastAPI)
- **FastAPI**: REST API and WebSocket support
- **python-kasa**: Communication with Kasa devices
- **SQLite**: Device information and configuration storage
- **InfluxDB** (optional): Time-series data for better performance
- **Socket.IO**: Real-time updates to frontend
- **APScheduler**: Periodic device polling

### Frontend (Next.js/React)
- **Next.js**: React framework with server-side rendering
- **TanStack Query**: Data fetching and caching
- **Recharts**: Interactive data visualization
- **Socket.IO Client**: Real-time data updates
- **Tailwind CSS**: Responsive styling

## Data Storage

### SQLite Tables:
- `device_info`: Device metadata
- `device_readings`: Historical power consumption data
- `electricity_rates`: Rate configurations
- `device_costs`: Calculated costs

### InfluxDB (Optional):
- Better performance for time-series queries
- Automatic data aggregation
- Retention policies for data management

## API Endpoints

- `GET /api/devices` - List all discovered devices
- `POST /api/discover` - Trigger device discovery
- `GET /api/device/{ip}` - Get device details
- `GET /api/device/{ip}/history` - Get historical data
- `GET /api/device/{ip}/stats` - Get device statistics
- `POST /api/device/{ip}/control` - Control device (on/off)
- `GET /api/rates` - Get electricity rates
- `POST /api/rates` - Set electricity rates
- `GET /api/costs` - Calculate electricity costs

## WebSocket Events

- `device_update` - Real-time device data updates
- `subscribe_device` - Subscribe to specific device updates
- `unsubscribe_device` - Unsubscribe from device updates

## Troubleshooting

### Devices not discovered:
- Ensure devices are on the same network
- Check firewall settings for ports 9999 and 20002
- Try using TP-Link Cloud credentials for newer devices

### No power data:
- Not all Kasa devices support energy monitoring
- Ensure device firmware is up to date

### Database errors:
- Check file permissions for SQLite database
- Verify InfluxDB connection if configured

## Contributing

Contributions are welcome! Please submit pull requests or open issues for bugs and feature requests.

## License

Copyright (C) 2025 Kasa Monitor Contributors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

### Important License Notice

This application is licensed under GPL v3 because it uses the python-kasa library,
which is also licensed under GPL v3. This means:

- You are free to use, modify, and distribute this software
- If you distribute modified versions, you must:
  - Make the source code available
  - License your modifications under GPL v3
  - Include appropriate notices and attribution

For detailed license terms, see the [LICENSE](LICENSE) file.

## Acknowledgments and Attribution

This application incorporates or is inspired by the following projects:

### python-kasa
- **Repository**: https://github.com/python-kasa/python-kasa
- **License**: GNU General Public License v3.0
- **Usage**: Core library for TP-Link Kasa device communication
- **Copyright**: python-kasa contributors

### PeaNUT
- **Repository**: https://github.com/brandawg93/peanut
- **License**: Apache License 2.0
- **Usage**: UI design inspiration for monitoring dashboard
- **Copyright**: Brandon Garcia and PeaNUT contributors

### Third-Party Libraries
- FastAPI, Next.js, React - MIT License
- TypeScript - Apache License 2.0
- Various npm packages - See package.json for details

For complete attribution information, see the [NOTICE](NOTICE) file.

## Disclaimer

This project is not affiliated with, endorsed by, or sponsored by TP-Link Technologies Co., Ltd.
Kasa is a trademark of TP-Link Technologies Co., Ltd.