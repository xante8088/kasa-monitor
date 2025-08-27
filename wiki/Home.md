# Kasa Monitor Wiki

Welcome to the Kasa Monitor wiki! This comprehensive guide will help you install, configure, and use Kasa Monitor to track your smart home devices' energy consumption.

<div align="center">
  <img src="https://raw.githubusercontent.com/xante8088/kasa-monitor/main/public/logo.png" alt="Kasa Monitor Logo" width="200">
  
  [![Docker Pulls](https://img.shields.io/docker/pulls/xante8088/kasa-monitor)](https://hub.docker.com/r/xante8088/kasa-monitor)
  [![GitHub Release](https://img.shields.io/github/release/xante8088/kasa-monitor.svg)](https://github.com/xante8088/kasa-monitor/releases)
  [![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](https://github.com/xante8088/kasa-monitor/blob/main/LICENSE)
</div>

## 📚 Documentation Overview

### Getting Started
- **[Installation Guide](Installation)** - Docker, manual setup, Raspberry Pi
- **[Quick Start](Quick-Start)** - Get up and running in 5 minutes
- **[Network Configuration](Network-Configuration)** - Docker networking options
- **[First Time Setup](First-Time-Setup)** - Initial configuration walkthrough

### User Guides
- **[Dashboard Overview](Dashboard-Overview)** - Understanding the main interface
- **[Device Management](Device-Management)** - Adding and managing devices
- **[Energy Monitoring](Energy-Monitoring)** - Tracking power consumption
- **[Cost Analysis](Cost-Analysis)** - Understanding your electricity costs
- **[Electricity Rates](Electricity-Rates)** - Configuring rate structures

### Advanced Topics
- **[API Documentation](API-Documentation)** - REST API reference
- **[Database Schema](Database-Schema)** - SQLite and InfluxDB structure
- **[Security Guide](Security-Guide)** - Best practices and hardening
- **[Docker Deployment](Docker-Deployment)** - Production deployment guide
- **[Backup & Recovery](Backup-Recovery)** - Data protection strategies

### Administration
- **[User Management](User-Management)** - Roles and permissions
- **[System Configuration](System-Configuration)** - Advanced settings
- **[Monitoring & Alerts](Monitoring-Alerts)** - Setting up notifications
- **[Performance Tuning](Performance-Tuning)** - Optimization for Raspberry Pi

### Development
- **[Contributing Guide](Contributing)** - How to contribute
- **[Development Setup](Development-Setup)** - Local development environment
- **[Architecture Overview](Architecture)** - System design and components
- **[Plugin Development](Plugin-Development)** - Extending functionality

### Troubleshooting
- **[Common Issues](Common-Issues)** - Frequently encountered problems
- **[Device Discovery](Device-Discovery-Issues)** - Network troubleshooting
- **[Docker Issues](Docker-Issues)** - Container-specific problems
- **[FAQ](FAQ)** - Frequently asked questions

## 🚀 Quick Links

### Essential Pages
- 🏁 [Quick Start Guide](Quick-Start)
- 🐳 [Docker Installation](Installation#docker)
- 🔧 [Manual Device Entry](Device-Management#manual-entry)
- 🔒 [Security Best Practices](Security-Guide)
- ❓ [FAQ](FAQ)

### External Resources
- [GitHub Repository](https://github.com/xante8088/kasa-monitor)
- [Docker Hub](https://hub.docker.com/r/xante8088/kasa-monitor)
- [Issue Tracker](https://github.com/xante8088/kasa-monitor/issues)
- [Releases](https://github.com/xante8088/kasa-monitor/releases)

## 🆕 Latest Release (v1.2.1)

### New Features
- ✅ **Time Period Selectors** - Customizable time ranges for each chart (24h, 7d, 30d, 3m, 6m, 1y, custom)
- ✅ **Enhanced Charts** - Time-aware formatting and intelligent data aggregation
- ✅ **Performance Optimizations** - 40% faster load times, 60% more responsive charts
- ✅ **Improved API** - Time period support with automatic aggregation

### Recent Enhancements (v1.2.0)
- ✅ **Enhanced Authentication System** - Token refresh, structured 401 responses, session management
- ✅ **Secure Data Export System** - Permission-based exports with audit logging and rate limiting
- ✅ **SSL Certificate Persistence** - Docker volume support for persistent SSL certificates
- ✅ **Device Persistence Fix** - Reliable device discovery across Docker updates
- ✅ **Comprehensive Audit Logging** - GDPR/SOX compliant activity tracking

## 💡 Features

### Core Functionality
- ✅ Real-time device monitoring
- ✅ Power consumption tracking
- ✅ Cost calculation with complex rate structures
- ✅ Historical data analysis
- ✅ Multi-user support with roles
- ✅ Docker support with multiple network modes
- ✅ Raspberry Pi optimized
- ✅ Secure data export with retention policies
- ✅ Session management with token refresh
- ✅ SSL/TLS with persistent certificate storage

### Supported Devices
- Kasa Smart Plugs (HS103, HS105, HS110, KP115, KP125)
- Kasa Smart Switches (HS200, HS210, HS220)
- Kasa Smart Power Strips (HS300, KP303, KP400)
- Kasa Smart Bulbs (KL110, KL120, KL130, LB100, LB130)

## 🤝 Community

### Getting Help
- Check the [FAQ](FAQ) first
- Browse [Common Issues](Common-Issues)
- Search [existing issues](https://github.com/xante8088/kasa-monitor/issues)
- Join our [Discussions](https://github.com/xante8088/kasa-monitor/discussions)

### Contributing
We welcome contributions! See our [Contributing Guide](Contributing) to get started.

## 📄 License

Kasa Monitor is licensed under the [GNU General Public License v3.0](https://github.com/xante8088/kasa-monitor/blob/main/LICENSE).

---

**Document Version:** 1.2.1  
**Last Updated:** 2025-08-27  
**Review Status:** Current  
**Change Summary:** Updated for v1.2.1 release with time period selectors, performance improvements, and device persistence fixes