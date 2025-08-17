#!/bin/bash
echo "=== Kasa Monitor Macvlan Deployment Status ==="
echo
echo "Container Status:"
docker-compose ps
echo
echo "Network Configuration:"
docker inspect kasa-monitor | grep -A 10 "kasa-macvlan"
echo
echo "Container Health:"
docker exec kasa-monitor curl -s http://localhost:5272/health
echo
echo
echo "=== Access Information ==="
CONTAINER_IP=$(docker inspect kasa-monitor | grep -A 15 "kasa-macvlan" | grep "IPAddress" | head -1 | cut -d'"' -f4)
echo "Container IP: $CONTAINER_IP"
echo "Frontend URL: http://$CONTAINER_IP:3000"
echo "Backend API: http://$CONTAINER_IP:5272"
echo "API Docs: http://$CONTAINER_IP:5272/docs"
echo
echo "=== Important Notes ==="
echo "• The container has direct network access for device discovery"
echo "• Access from other devices on the 192.168.1.x network should work"
echo "• macOS host access may be limited due to Docker Desktop networking"
echo "• For testing from this host, use: docker exec kasa-monitor <command>"