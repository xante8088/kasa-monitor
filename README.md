# Kasa Monitor

A comprehensive web application for monitoring TP-Link Kasa smart devices with advanced electricity cost tracking, user management, and enterprise-ready deployment options.

![Version](https://img.shields.io/github/v/tag/xante8088/kasa-monitor?label=version)
![Docker Pulls](https://img.shields.io/docker/pulls/xante8088/kasa-monitor)
![License](https://img.shields.io/badge/license-GPL%20v3-blue)

## ✨ Features

### 🔌 Device Management
- **Auto Discovery**: Find Kasa devices on your network automatically
- **Real-time Monitoring**: Live power, voltage, and energy data
- **Device Control**: Turn devices on/off remotely
- **Persistent Storage**: Devices remain saved between sessions
- **IP Management**: Update device IPs when they change
- **Custom Notes**: Add notes to track device purposes

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
- **Granular Permissions**: 20+ distinct permission types
- **SSL/HTTPS Support**: Full certificate management
- **Network Restrictions**: Local-only access options
- **First-Time Setup Wizard**: Guided admin account creation

### 📊 Data & Visualization
- **Interactive Charts**: Power trends, voltage stability, energy patterns
- **Historical Data**: SQLite + optional InfluxDB support
- **Real-time Updates**: WebSocket connections for live data
- **Export Capabilities**: Data export and analysis tools
- **Responsive Design**: Works on desktop, tablet, and mobile

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Quick start with Docker Compose
curl -o docker-compose.yml https://raw.githubusercontent.com/xante8088/kasa-monitor/main/docker-compose.sample.yml
docker-compose up -d

# Access at http://localhost:3000
```

### Option 2: Docker with Auto Network Detection

```bash
# Clone repository
git clone https://github.com/xante8088/kasa-monitor.git
cd kasa-monitor

# Use network helper to avoid conflicts
./docker-network-helper.sh --generate
docker-compose up -d
```

### Option 3: Traditional Installation

```bash
# Clone and setup
git clone https://github.com/xante8088/kasa-monitor.git
cd kasa-monitor

# One-command setup
chmod +x start.sh && ./start.sh
```

## 🐳 Docker Deployment

### Available Images

```bash
# Latest stable
docker pull xante8088/kasa-monitor:latest

# Raspberry Pi optimized
docker pull xante8088/kasa-monitor:pi5

# Specific version
docker pull xante8088/kasa-monitor:1.0.0
```

### Docker Compose Configuration

```yaml
version: '3.8'
services:
  kasa-monitor:
    image: xante8088/kasa-monitor:latest
    ports:
      - "3000:3000"   # Frontend
      - "8000:8000"   # Backend API
    volumes:
      - kasa_data:/app/data
      - kasa_logs:/app/logs
    environment:
      - JWT_SECRET_KEY=your-secret-key-here
      - TZ=America/New_York
    restart: unless-stopped

volumes:
  kasa_data:
  kasa_logs:
```

### Raspberry Pi Deployment

Optimized for Raspberry Pi 4B and 5:

```bash
# Use Pi-optimized image
docker pull xante8088/kasa-monitor:pi5

# Run with memory limits
docker run -d \
  -p 3000:3000 \
  -p 8000:8000 \
  --memory="1g" \
  --name kasa-monitor \
  xante8088/kasa-monitor:pi5
```

## 📋 First-Time Setup

1. **Access the Application**
   - Navigate to http://localhost:3000
   - Automatically redirected to setup wizard

2. **Create Admin Account**
   - Enter admin credentials
   - Secure password (min 8 characters)
   - This account has full system access

3. **Discover Devices**
   - Click "Discover Devices"
   - Devices auto-detected on network
   - Optional: Add TP-Link Cloud credentials

4. **Configure Electricity Rates**
   - Go to Settings → Rates
   - Choose rate structure
   - Enter your utility rates

## 🔧 Configuration

### Environment Variables

Create `.env` file for configuration:

```env
# Security
JWT_SECRET_KEY=generate-with-openssl-rand-hex-32

# Database
SQLITE_PATH=/app/data/kasa_monitor.db

# Timezone
TZ=America/New_York

# Network Security
ALLOW_LOCAL_ONLY=true
ALLOWED_NETWORKS=192.168.0.0/16,10.0.0.0/8

# Optional: TP-Link Cloud
TPLINK_USERNAME=your-email@example.com
TPLINK_PASSWORD=your-password

# Optional: InfluxDB
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=your-token
INFLUXDB_ORG=kasa-monitor
INFLUXDB_BUCKET=device-data

# Performance
NODE_OPTIONS=--max-old-space-size=1024
POLLING_INTERVAL=30
```

## 🛠 API Reference

### Authentication Endpoints
- `POST /api/auth/login` - User login
- `POST /api/auth/setup` - Initial admin setup
- `GET /api/auth/me` - Current user info
- `GET /api/auth/setup-required` - Check setup status

### Device Management
- `GET /api/devices` - List all devices
- `POST /api/discover` - Discover devices
- `GET /api/device/{ip}` - Device details
- `GET /api/device/{ip}/history` - Historical data
- `POST /api/device/{ip}/control` - Control device
- `PUT /api/devices/{ip}/monitoring` - Toggle monitoring
- `DELETE /api/devices/{ip}` - Remove device

### User Management
- `GET /api/users` - List users
- `POST /api/users` - Create user
- `PUT /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user

### Rates & Costs
- `GET /api/rates` - Get electricity rates
- `POST /api/rates` - Update rates
- `GET /api/costs` - Cost analysis

### Permissions
- `GET /api/permissions` - List permissions
- `GET /api/roles/permissions` - Role permissions

## 🔐 Security Features

### Authentication & Authorization
- JWT token-based authentication
- Role-based access control (RBAC)
- Granular permission system
- Secure password hashing (bcrypt)

### Network Security
- Local-only access option
- IP whitelist support
- SSL/HTTPS support
- CORS protection

### User Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| Admin | Full system access | All permissions |
| Operator | Device management | Control devices, manage rates |
| Viewer | Read-only access | View devices and costs |
| Guest | Limited access | View devices only |

## 🔄 CI/CD & Automation

### GitHub Actions
- **Auto-tagging**: Semantic versioning on every push
- **Docker builds**: Multi-architecture images (AMD64/ARM64)
- **PR validation**: Build checks without pushing

### Version Management
- Automatic semantic versioning
- Commit-based version bumping:
  - `feat:` → Minor version bump
  - `fix:` → Patch version bump
  - `BREAKING CHANGE:` → Major version bump

## 📊 Monitoring Features

### Real-time Data
- Power consumption (W)
- Voltage levels (V)
- Current draw (A)
- Energy usage (kWh)
- Device status (on/off)

### Historical Analysis
- Daily/weekly/monthly trends
- Peak usage identification
- Cost projections
- Usage patterns

## 🧪 Development

### Prerequisites
- Python 3.8+
- Node.js 16+
- Docker (optional)

### Local Development

```bash
# Backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd backend && python server.py

# Frontend (new terminal)
npm install
npm run dev
```

### Testing

```bash
# Run endpoint tests
python test-endpoints.py

# Check Docker build
docker build -t kasa-monitor-test .
```

## 📁 Project Structure

```
kasa-monitor/
├── backend/            # Python FastAPI backend
│   ├── server.py      # Main server file
│   ├── database.py    # Database operations
│   ├── auth.py        # Authentication logic
│   └── models.py      # Data models
├── src/               # Next.js frontend
│   ├── app/          # App routes
│   ├── components/   # React components
│   └── contexts/     # React contexts
├── docker-compose.yml # Docker configuration
├── Dockerfile        # Multi-stage build
└── start.sh         # Quick start script
```

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit with conventional commits
4. Submit a pull request

## 📄 License

GNU General Public License v3.0

This application is licensed under GPL v3 because it uses the python-kasa library.
See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- **python-kasa**: Core library for device communication
- **PeaNUT**: UI design inspiration
- **FastAPI & Next.js**: Framework foundations

## ⚠️ Disclaimer

This project is not affiliated with TP-Link Technologies Co., Ltd.
Kasa is a trademark of TP-Link Technologies Co., Ltd.

## 📞 Support

- **Documentation**: [Full Docs](https://github.com/xante8088/kasa-monitor)
- **Issues**: [GitHub Issues](https://github.com/xante8088/kasa-monitor/issues)
- **Docker Hub**: [xante8088/kasa-monitor](https://hub.docker.com/r/xante8088/kasa-monitor)

---

Made with ❤️ for the smart home community