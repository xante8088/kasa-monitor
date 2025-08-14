# Frequently Asked Questions

## General Questions

### What is Kasa Monitor?
Kasa Monitor is an open-source web application for monitoring TP-Link Kasa smart home devices. It tracks energy consumption, calculates electricity costs, and provides detailed analytics for your smart home devices.

### Which devices are supported?
- **Smart Plugs**: HS103, HS105, HS110, KP115, KP125, EP10, EP25
- **Smart Switches**: HS200, HS210, HS220, KS200M, KS220M
- **Smart Power Strips**: HS300, KP303, KP400, HS107
- **Smart Bulbs**: KL110, KL120, KL130, LB100, LB110, LB130

### Is this official TP-Link software?
No, Kasa Monitor is an independent, open-source project not affiliated with TP-Link.

### Is it free?
Yes, Kasa Monitor is completely free and open-source under the GPL-3.0 license.

## Installation

### Do I need Docker?
Docker is recommended but not required. You can also install manually with Node.js and Python.

### Can I run this on Raspberry Pi?
Yes! Kasa Monitor is optimized for Raspberry Pi. Use the ARM64 Docker image or manual installation.

### What are the system requirements?
- **Minimum**: 512MB RAM, 500MB storage
- **Recommended**: 2GB RAM, 1GB storage
- **OS**: Linux, macOS, or Windows (via Docker)

### Can I run this in the cloud?
Yes, but device discovery won't work. You'll need to manually add devices by IP address.

## Device Discovery

### Why can't I find my devices?
Device discovery depends on your Docker network mode:
- **Bridge mode**: No discovery (use manual IP entry)
- **Host mode**: Full discovery (Linux only)
- **Macvlan mode**: Full discovery with isolation

See [Network Configuration](Network-Configuration) for details.

### How do I find my device IP addresses?
1. **Router admin panel**: Check connected devices
2. **Kasa mobile app**: Device settings → Device Info
3. **Network scan**: `nmap -sn 192.168.1.0/24`

### Can I add devices manually?
Yes! Go to Settings → Device Management → Add Device Manually.

### Do devices need to be on the same network?
Yes, devices must be on the same network as Kasa Monitor for local communication.

## Energy Monitoring

### How accurate is the power monitoring?
Accuracy depends on your device:
- Devices with energy monitoring (HS110, KP115): ±1% accuracy
- Devices without monitoring: Estimated based on state

### What's the difference between power and energy?
- **Power (W)**: Instantaneous consumption (like speedometer)
- **Energy (kWh)**: Total consumption over time (like odometer)

### How often is data collected?
Default polling interval is 60 seconds. Can be adjusted in settings.

### How long is data stored?
- SQLite: Unlimited (limited by disk space)
- InfluxDB: Configurable retention policy

## Cost Calculation

### How are costs calculated?
Costs are calculated using your configured electricity rates:
- Simple rate: kWh × rate
- Time-of-use: kWh × rate for time period
- Tiered: kWh × rate for usage tier

### Can I set different rates for different times?
Yes! Configure Time-of-Use rates in Settings → Electricity Rates.

### Are taxes included in calculations?
You can include taxes in your rate configuration.

### Can I export cost data?
Yes, export to CSV from the device detail view.

## Docker & Networking

### Which Docker network mode should I use?
- **Host mode**: Best for home use with discovery
- **Bridge mode**: Most secure, manual device entry
- **Macvlan**: Advanced users, best of both

### Can I use Docker on Windows/Mac?
Yes, but only bridge mode works. Use manual device entry.

### How do I update the Docker image?
```bash
docker pull xante8088/kasa-monitor:latest
docker-compose down
docker-compose up -d
```

### How do I backup my data?
```bash
docker run --rm -v kasa_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/backup.tar.gz -C /data .
```

## Security

### Is it safe to expose to the internet?
Not recommended without additional security:
- Use reverse proxy (nginx, Traefik)
- Enable HTTPS
- Use strong passwords
- Consider VPN access instead

### Are my TP-Link credentials stored?
Optional. Only needed for cloud-connected devices. Stored encrypted if provided.

### What permissions do users have?
Four roles with different permissions:
- **Admin**: Full access
- **Operator**: Control devices, view data
- **Viewer**: Read-only access
- **Guest**: Limited access

### How do I reset admin password?
Delete the database and restart:
```bash
docker exec kasa-monitor rm /app/data/kasa_monitor.db
docker restart kasa-monitor
```

## Troubleshooting

### Web interface won't load
1. Check container is running: `docker ps`
2. Check logs: `docker logs kasa-monitor`
3. Verify ports: `curl http://localhost:3000`

### API returns 401 Unauthorized
Your token has expired. Log in again to get a new token.

### Devices show as offline
1. Check device is powered on
2. Verify network connectivity
3. Try manual connection by IP

### High CPU/memory usage
- Reduce polling interval
- Limit data retention
- Use InfluxDB for large datasets

### Container keeps restarting
Check logs for errors:
```bash
docker logs kasa-monitor --tail 50
```

## Features

### Can I control devices remotely?
Yes, if you have proper network access (VPN, port forwarding).

### Does it work with Home Assistant?
Not directly integrated, but you can use the API.

### Can I set up alerts?
Not built-in, but you can use the API with external monitoring.

### Is there a mobile app?
No native app, but the web interface is mobile-responsive.

### Can I contribute?
Yes! See [Contributing Guide](Contributing).

## Data & Privacy

### Is my data sent anywhere?
No, all data stays local unless you explicitly configure cloud services.

### What data is collected?
- Device power consumption
- Device state (on/off)
- Network statistics
- User actions (if logged in)

### Can I delete my data?
Yes, data can be deleted through the database or by removing volumes.

### GDPR compliance?
Since data is stored locally, you control all data.

## Common Errors

### "Cannot connect to device"
- Verify device IP is correct
- Check network connectivity
- Ensure device is Kasa-compatible

### "Discovery timeout"
- Switch to host network mode
- Use manual device entry
- Check firewall settings

### "Database locked"
- Restart the container
- Check disk space
- Verify file permissions

### "Invalid token"
- Token expired, log in again
- Check system time is correct

## Getting More Help

### Still have questions?

1. Search [existing issues](https://github.com/xante8088/kasa-monitor/issues)
2. Check [Common Issues](Common-Issues) guide
3. Join [Discussions](https://github.com/xante8088/kasa-monitor/discussions)
4. Open a [new issue](https://github.com/xante8088/kasa-monitor/issues/new)

### Want to contribute?
See our [Contributing Guide](Contributing) to get started!

### Found a security issue?
Please report security issues privately. See [Security Policy](Security-Guide#reporting).

---

*Don't see your question? [Ask in Discussions](https://github.com/xante8088/kasa-monitor/discussions/new?category=q-a)*