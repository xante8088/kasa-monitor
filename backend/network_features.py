"""Advanced network features for device discovery and management.

Copyright (C) 2025 Kasa Monitor Contributors

This file is part of Kasa Monitor.

Kasa Monitor is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Kasa Monitor is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Kasa Monitor. If not, see <https://www.gnu.org/licenses/>.
"""

import sqlite3
import json
import asyncio
import socket
import ipaddress
import netifaces
import subprocess
import platform
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Set, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
import concurrent.futures
import threading


class NetworkProtocol(Enum):
    """Network discovery protocols."""

    TCP_SCAN = "tcp_scan"
    UDP_BROADCAST = "udp_broadcast"
    MDNS = "mdns"
    UPNP = "upnp"
    ARP = "arp"
    CUSTOM = "custom"


class VLANMode(Enum):
    """VLAN operation modes."""

    TRUNK = "trunk"
    ACCESS = "access"
    HYBRID = "hybrid"


@dataclass
class NetworkInterface:
    """Network interface configuration."""

    name: str
    ip_address: str
    netmask: str
    mac_address: str
    vlan_id: Optional[int] = None
    mtu: int = 1500
    enabled: bool = True
    is_wireless: bool = False

    @property
    def network(self) -> ipaddress.IPv4Network:
        """Get network address."""
        return ipaddress.IPv4Network(f"{self.ip_address}/{self.netmask}", strict=False)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["network"] = str(self.network)
        return data


@dataclass
class VLANConfig:
    """VLAN configuration."""

    vlan_id: int
    name: str
    description: str
    interface: str
    mode: VLANMode
    tagged_ports: Optional[List[int]] = None
    untagged_ports: Optional[List[int]] = None
    ip_range: Optional[str] = None
    priority: int = 0
    enabled: bool = True

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["mode"] = self.mode.value
        return data


@dataclass
class DiscoveryResult:
    """Device discovery result."""

    ip_address: str
    mac_address: Optional[str]
    hostname: Optional[str]
    device_type: Optional[str]
    manufacturer: Optional[str]
    model: Optional[str]
    services: List[str]
    vlan_id: Optional[int]
    interface: str
    protocol: NetworkProtocol
    discovered_at: datetime
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["protocol"] = self.protocol.value
        data["discovered_at"] = self.discovered_at.isoformat()
        return data


class mDNSListener(ServiceListener):
    """mDNS/Bonjour service listener."""

    def __init__(self, discovery_manager):
        """Initialize listener.

        Args:
            discovery_manager: Parent discovery manager
        """
        self.discovery_manager = discovery_manager
        self.discovered_services = {}

    def add_service(self, zeroconf, service_type, name):
        """Service discovered."""
        info = zeroconf.get_service_info(service_type, name)
        if info:
            self.discovered_services[name] = {
                "type": service_type,
                "name": name,
                "addresses": [socket.inet_ntoa(addr) for addr in info.addresses],
                "port": info.port,
                "properties": info.properties,
                "server": info.server,
            }

            # Notify discovery manager
            for address in self.discovered_services[name]["addresses"]:
                self.discovery_manager._process_mdns_device(address, self.discovered_services[name])

    def remove_service(self, zeroconf, service_type, name):
        """Service removed."""
        if name in self.discovered_services:
            del self.discovered_services[name]

    def update_service(self, zeroconf, service_type, name):
        """Service updated."""
        self.remove_service(zeroconf, service_type, name)
        self.add_service(zeroconf, service_type, name)


class NetworkDiscoveryManager:
    """Advanced network discovery and management."""

    def __init__(self, db_path: str = "kasa_monitor.db"):
        """Initialize network discovery manager.

        Args:
            db_path: Path to database
        """
        self.db_path = db_path
        self.interfaces = {}
        self.vlans = {}
        self.discovered_devices = {}
        self.zeroconf = None
        self.mdns_browser = None
        self.discovery_running = False

        self._init_database()
        self._load_interfaces()
        self._load_vlans()

    def _init_database(self):
        """Initialize network tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Network interfaces table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS network_interfaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                ip_address TEXT NOT NULL,
                netmask TEXT NOT NULL,
                mac_address TEXT NOT NULL,
                vlan_id INTEGER,
                mtu INTEGER DEFAULT 1500,
                enabled BOOLEAN DEFAULT 1,
                is_wireless BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # VLAN configurations table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS vlan_configs (
                vlan_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                interface TEXT NOT NULL,
                mode TEXT NOT NULL,
                tagged_ports TEXT,
                untagged_ports TEXT,
                ip_range TEXT,
                priority INTEGER DEFAULT 0,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Discovery configurations table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS discovery_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                protocols TEXT NOT NULL,
                interfaces TEXT,
                vlans TEXT,
                subnets TEXT,
                port_range TEXT,
                timeout INTEGER DEFAULT 5,
                parallel_scans INTEGER DEFAULT 10,
                enabled BOOLEAN DEFAULT 1
            )
        """
        )

        # Discovered devices table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS discovered_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                mac_address TEXT,
                hostname TEXT,
                device_type TEXT,
                manufacturer TEXT,
                model TEXT,
                services TEXT,
                vlan_id INTEGER,
                interface TEXT,
                protocol TEXT,
                discovered_at TIMESTAMP NOT NULL,
                last_seen TIMESTAMP,
                metadata TEXT,
                UNIQUE(ip_address, interface)
            )
        """
        )

        # Discovery history table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS discovery_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discovery_run_id TEXT NOT NULL,
                started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                interfaces_scanned TEXT,
                protocols_used TEXT,
                devices_found INTEGER DEFAULT 0,
                new_devices INTEGER DEFAULT 0,
                errors TEXT,
                initiated_by TEXT
            )
        """
        )

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_disc_ip ON discovered_devices(ip_address)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_disc_mac ON discovered_devices(mac_address)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_disc_vlan ON discovered_devices(vlan_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_disc_time ON discovered_devices(discovered_at)")

        conn.commit()
        conn.close()

    def detect_interfaces(self) -> List[NetworkInterface]:
        """Detect available network interfaces.

        Returns:
            List of network interfaces
        """
        interfaces = []

        for iface_name in netifaces.interfaces():
            addrs = netifaces.ifaddresses(iface_name)

            # Get IPv4 address
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip = addr.get("addr")
                    netmask = addr.get("netmask")

                    if ip and netmask and not ip.startswith("127."):
                        # Get MAC address
                        mac = None
                        if netifaces.AF_LINK in addrs:
                            mac = addrs[netifaces.AF_LINK][0].get("addr")

                        # Check if wireless
                        is_wireless = "wlan" in iface_name.lower() or "wi" in iface_name.lower()

                        interface = NetworkInterface(
                            name=iface_name,
                            ip_address=ip,
                            netmask=netmask,
                            mac_address=mac or "00:00:00:00:00:00",
                            is_wireless=is_wireless,
                        )
                        interfaces.append(interface)

        return interfaces

    def add_interface(self, interface: NetworkInterface) -> bool:
        """Add network interface configuration.

        Args:
            interface: Network interface

        Returns:
            True if added successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO network_interfaces 
                (name, ip_address, netmask, mac_address, vlan_id, mtu, 
                 enabled, is_wireless)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    interface.name,
                    interface.ip_address,
                    interface.netmask,
                    interface.mac_address,
                    interface.vlan_id,
                    interface.mtu,
                    interface.enabled,
                    interface.is_wireless,
                ),
            )

            conn.commit()
            self.interfaces[interface.name] = interface
            return True

        except Exception:
            return False
        finally:
            conn.close()

    def configure_vlan(self, vlan: VLANConfig) -> bool:
        """Configure VLAN.

        Args:
            vlan: VLAN configuration

        Returns:
            True if configured successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO vlan_configs 
                (vlan_id, name, description, interface, mode, tagged_ports,
                 untagged_ports, ip_range, priority, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    vlan.vlan_id,
                    vlan.name,
                    vlan.description,
                    vlan.interface,
                    vlan.mode.value,
                    json.dumps(vlan.tagged_ports) if vlan.tagged_ports else None,
                    json.dumps(vlan.untagged_ports) if vlan.untagged_ports else None,
                    vlan.ip_range,
                    vlan.priority,
                    vlan.enabled,
                ),
            )

            conn.commit()
            self.vlans[vlan.vlan_id] = vlan

            # Apply VLAN configuration to system (platform-specific)
            self._apply_vlan_config(vlan)

            return True

        except Exception:
            return False
        finally:
            conn.close()

    def _apply_vlan_config(self, vlan: VLANConfig):
        """Apply VLAN configuration to system.

        Args:
            vlan: VLAN configuration
        """
        system = platform.system()

        if system == "Linux":
            # Create VLAN interface using ip command
            try:
                subprocess.run(
                    [
                        "sudo",
                        "ip",
                        "link",
                        "add",
                        "link",
                        vlan.interface,
                        f"name",
                        f"{vlan.interface}.{vlan.vlan_id}",
                        "type",
                        "vlan",
                        "id",
                        str(vlan.vlan_id),
                    ],
                    check=True,
                )

                subprocess.run(
                    [
                        "sudo",
                        "ip",
                        "link",
                        "set",
                        "dev",
                        f"{vlan.interface}.{vlan.vlan_id}",
                        "up",
                    ],
                    check=True,
                )
            except subprocess.CalledProcessError:
                pass  # VLAN might already exist

        elif system == "Darwin":  # macOS
            # Create VLAN interface using ifconfig
            try:
                subprocess.run(
                    [
                        "sudo",
                        "ifconfig",
                        f"vlan{vlan.vlan_id}",
                        "create",
                        "vlan",
                        str(vlan.vlan_id),
                        "vlandev",
                        vlan.interface,
                    ],
                    check=True,
                )
            except subprocess.CalledProcessError:
                pass

    async def discover_devices(
        self,
        protocols: List[NetworkProtocol] = None,
        interfaces: List[str] = None,
        subnets: List[str] = None,
    ) -> List[DiscoveryResult]:
        """Discover devices on network.

        Args:
            protocols: Discovery protocols to use
            interfaces: Interfaces to scan
            subnets: Specific subnets to scan

        Returns:
            List of discovered devices
        """
        if protocols is None:
            protocols = [NetworkProtocol.TCP_SCAN, NetworkProtocol.MDNS]

        if interfaces is None:
            interfaces = list(self.interfaces.keys())

        results = []
        discovery_id = datetime.now().isoformat()

        # Record discovery start
        self._record_discovery_start(discovery_id, interfaces, protocols)

        # Start mDNS discovery if requested
        if NetworkProtocol.MDNS in protocols:
            self._start_mdns_discovery()

        # Perform network scans
        tasks = []
        for interface_name in interfaces:
            interface = self.interfaces.get(interface_name)
            if not interface or not interface.enabled:
                continue

            if NetworkProtocol.TCP_SCAN in protocols:
                if subnets:
                    for subnet in subnets:
                        tasks.append(self._scan_subnet(subnet, interface))
                else:
                    tasks.append(self._scan_subnet(str(interface.network), interface))

            if NetworkProtocol.ARP in protocols:
                tasks.append(self._arp_scan(interface))

        # Execute scans in parallel
        if tasks:
            scan_results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in scan_results:
                if isinstance(result, list):
                    results.extend(result)

        # Stop mDNS discovery
        if NetworkProtocol.MDNS in protocols:
            await asyncio.sleep(5)  # Give mDNS time to discover
            self._stop_mdns_discovery()
            results.extend(self._get_mdns_results())

        # Record discovery completion
        self._record_discovery_complete(discovery_id, len(results))

        return results

    async def _scan_subnet(self, subnet: str, interface: NetworkInterface) -> List[DiscoveryResult]:
        """Scan subnet for devices.

        Args:
            subnet: Subnet to scan
            interface: Network interface

        Returns:
            List of discovered devices
        """
        results = []
        network = ipaddress.IPv4Network(subnet, strict=False)

        # Limit scan to reasonable size
        if network.num_addresses > 1024:
            return results

        # Scan common Kasa device ports
        kasa_ports = [9999, 80, 443]

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = []

            for ip in network.hosts():
                for port in kasa_ports:
                    future = executor.submit(self._check_port, str(ip), port)
                    futures.append((str(ip), port, future))

            for ip, port, future in futures:
                try:
                    if future.result(timeout=1):
                        # Port is open, might be a Kasa device
                        result = DiscoveryResult(
                            ip_address=ip,
                            mac_address=self._get_mac_address(ip),
                            hostname=self._get_hostname(ip),
                            device_type="potential_kasa" if port == 9999 else "unknown",
                            manufacturer=None,
                            model=None,
                            services=[f"tcp:{port}"],
                            vlan_id=interface.vlan_id,
                            interface=interface.name,
                            protocol=NetworkProtocol.TCP_SCAN,
                            discovered_at=datetime.now(),
                        )
                        results.append(result)
                        self._store_discovery_result(result)
                except Exception:
                    pass

        return results

    def _check_port(self, ip: str, port: int, timeout: float = 0.5) -> bool:
        """Check if port is open.

        Args:
            ip: IP address
            port: Port number
            timeout: Connection timeout

        Returns:
            True if port is open
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            result = sock.connect_ex((ip, port))
            return result == 0
        except Exception:
            return False
        finally:
            sock.close()

    async def _arp_scan(self, interface: NetworkInterface) -> List[DiscoveryResult]:
        """Perform ARP scan.

        Args:
            interface: Network interface

        Returns:
            List of discovered devices
        """
        results = []
        system = platform.system()

        try:
            if system == "Linux":
                # Use arp-scan if available
                output = subprocess.run(
                    ["sudo", "arp-scan", "--interface", interface.name, "--local"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                ).stdout

                for line in output.split("\n"):
                    parts = line.split()
                    if len(parts) >= 3 and "." in parts[0]:
                        result = DiscoveryResult(
                            ip_address=parts[0],
                            mac_address=parts[1],
                            hostname=None,
                            device_type=None,
                            manufacturer=parts[2] if len(parts) > 2 else None,
                            model=None,
                            services=[],
                            vlan_id=interface.vlan_id,
                            interface=interface.name,
                            protocol=NetworkProtocol.ARP,
                            discovered_at=datetime.now(),
                        )
                        results.append(result)
                        self._store_discovery_result(result)

            elif system == "Darwin":
                # Use arp command on macOS
                output = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=10).stdout

                for line in output.split("\n"):
                    if "(" in line and ")" in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            ip = parts[1].strip("()")
                            mac = parts[3]
                            if mac != "(incomplete)":
                                result = DiscoveryResult(
                                    ip_address=ip,
                                    mac_address=mac,
                                    hostname=parts[0],
                                    device_type=None,
                                    manufacturer=None,
                                    model=None,
                                    services=[],
                                    vlan_id=interface.vlan_id,
                                    interface=interface.name,
                                    protocol=NetworkProtocol.ARP,
                                    discovered_at=datetime.now(),
                                )
                                results.append(result)
                                self._store_discovery_result(result)
        except Exception:
            pass

        return results

    def _start_mdns_discovery(self):
        """Start mDNS/Bonjour discovery."""
        if not self.zeroconf:
            self.zeroconf = Zeroconf()
            self.mdns_listener = mDNSListener(self)

            # Browse for common smart home services
            services = [
                "_kasa._tcp.local.",
                "_hap._tcp.local.",  # HomeKit
                "_http._tcp.local.",
                "_https._tcp.local.",
                "_smartplug._tcp.local.",
                "_iot._tcp.local.",
            ]

            self.mdns_browsers = []
            for service in services:
                browser = ServiceBrowser(self.zeroconf, service, self.mdns_listener)
                self.mdns_browsers.append(browser)

    def _stop_mdns_discovery(self):
        """Stop mDNS/Bonjour discovery."""
        if self.zeroconf:
            self.zeroconf.close()
            self.zeroconf = None
            self.mdns_browsers = []

    def _get_mdns_results(self) -> List[DiscoveryResult]:
        """Get mDNS discovery results.

        Returns:
            List of discovered devices
        """
        results = []
        # Results are stored by the mDNS listener
        return results

    def _process_mdns_device(self, ip_address: str, service_info: Dict):
        """Process discovered mDNS device.

        Args:
            ip_address: Device IP address
            service_info: Service information
        """
        # Determine interface
        interface_name = self._get_interface_for_ip(ip_address)

        result = DiscoveryResult(
            ip_address=ip_address,
            mac_address=self._get_mac_address(ip_address),
            hostname=service_info.get("server"),
            device_type=self._identify_device_type(service_info),
            manufacturer=None,
            model=None,
            services=[service_info.get("type", "")],
            vlan_id=None,
            interface=interface_name,
            protocol=NetworkProtocol.MDNS,
            discovered_at=datetime.now(),
            metadata=service_info,
        )

        self._store_discovery_result(result)

    def _get_interface_for_ip(self, ip_address: str) -> str:
        """Get interface for IP address.

        Args:
            ip_address: IP address

        Returns:
            Interface name
        """
        ip = ipaddress.IPv4Address(ip_address)
        for name, interface in self.interfaces.items():
            if ip in interface.network:
                return name
        return "unknown"

    def _identify_device_type(self, service_info: Dict) -> str:
        """Identify device type from service info.

        Args:
            service_info: Service information

        Returns:
            Device type
        """
        service_type = service_info.get("type", "").lower()

        if "kasa" in service_type:
            return "kasa_device"
        elif "smartplug" in service_type:
            return "smart_plug"
        elif "hap" in service_type:
            return "homekit_device"

        return "unknown"

    def _get_mac_address(self, ip_address: str) -> Optional[str]:
        """Get MAC address for IP.

        Args:
            ip_address: IP address

        Returns:
            MAC address or None
        """
        # Try to get from ARP cache
        try:
            if platform.system() == "Linux":
                output = subprocess.run(["arp", "-n", ip_address], capture_output=True, text=True).stdout

                for line in output.split("\n"):
                    if ip_address in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            return parts[2]

            elif platform.system() == "Darwin":
                output = subprocess.run(["arp", ip_address], capture_output=True, text=True).stdout

                parts = output.split()
                if len(parts) >= 4:
                    return parts[3]
        except Exception:
            pass

        return None

    def _get_hostname(self, ip_address: str) -> Optional[str]:
        """Get hostname for IP.

        Args:
            ip_address: IP address

        Returns:
            Hostname or None
        """
        try:
            hostname, _, _ = socket.gethostbyaddr(ip_address)
            return hostname
        except Exception:
            return None

    def _store_discovery_result(self, result: DiscoveryResult):
        """Store discovery result in database.

        Args:
            result: Discovery result
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO discovered_devices 
                (ip_address, mac_address, hostname, device_type, manufacturer,
                 model, services, vlan_id, interface, protocol, discovered_at,
                 last_seen, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    result.ip_address,
                    result.mac_address,
                    result.hostname,
                    result.device_type,
                    result.manufacturer,
                    result.model,
                    json.dumps(result.services),
                    result.vlan_id,
                    result.interface,
                    result.protocol.value,
                    result.discovered_at,
                    datetime.now(),
                    json.dumps(result.metadata) if result.metadata else None,
                ),
            )

            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

    def _record_discovery_start(self, discovery_id: str, interfaces: List[str], protocols: List[NetworkProtocol]):
        """Record discovery start.

        Args:
            discovery_id: Discovery run ID
            interfaces: Interfaces being scanned
            protocols: Protocols being used
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO discovery_history 
            (discovery_run_id, started_at, interfaces_scanned, protocols_used,
             initiated_by)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                discovery_id,
                datetime.now(),
                json.dumps(interfaces),
                json.dumps([p.value for p in protocols]),
                "system",
            ),
        )

        conn.commit()
        conn.close()

    def _record_discovery_complete(self, discovery_id: str, devices_found: int):
        """Record discovery completion.

        Args:
            discovery_id: Discovery run ID
            devices_found: Number of devices found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE discovery_history 
            SET completed_at = ?, devices_found = ?
            WHERE discovery_run_id = ?
        """,
            (datetime.now(), devices_found, discovery_id),
        )

        conn.commit()
        conn.close()

    def get_discovered_devices(self, interface: Optional[str] = None, vlan_id: Optional[int] = None) -> List[Dict]:
        """Get discovered devices.

        Args:
            interface: Filter by interface
            vlan_id: Filter by VLAN

        Returns:
            List of discovered devices
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM discovered_devices WHERE 1=1"
        params = []

        if interface:
            query += " AND interface = ?"
            params.append(interface)

        if vlan_id is not None:
            query += " AND vlan_id = ?"
            params.append(vlan_id)

        query += " ORDER BY discovered_at DESC"

        cursor.execute(query, params)

        devices = []
        for row in cursor.fetchall():
            devices.append(
                {
                    "ip_address": row[1],
                    "mac_address": row[2],
                    "hostname": row[3],
                    "device_type": row[4],
                    "manufacturer": row[5],
                    "model": row[6],
                    "services": json.loads(row[7]) if row[7] else [],
                    "vlan_id": row[8],
                    "interface": row[9],
                    "protocol": row[10],
                    "discovered_at": row[11],
                    "last_seen": row[12],
                    "metadata": json.loads(row[13]) if row[13] else None,
                }
            )

        conn.close()
        return devices

    def _load_interfaces(self):
        """Load network interfaces from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT name, ip_address, netmask, mac_address, vlan_id, mtu,
                   enabled, is_wireless
            FROM network_interfaces
            WHERE enabled = 1
        """
        )

        self.interfaces = {}
        for row in cursor.fetchall():
            interface = NetworkInterface(
                name=row[0],
                ip_address=row[1],
                netmask=row[2],
                mac_address=row[3],
                vlan_id=row[4],
                mtu=row[5],
                enabled=bool(row[6]),
                is_wireless=bool(row[7]),
            )
            self.interfaces[interface.name] = interface

        conn.close()

    def _load_vlans(self):
        """Load VLAN configurations from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT vlan_id, name, description, interface, mode, tagged_ports,
                   untagged_ports, ip_range, priority, enabled
            FROM vlan_configs
            WHERE enabled = 1
        """
        )

        self.vlans = {}
        for row in cursor.fetchall():
            vlan = VLANConfig(
                vlan_id=row[0],
                name=row[1],
                description=row[2],
                interface=row[3],
                mode=VLANMode(row[4]),
                tagged_ports=json.loads(row[5]) if row[5] else None,
                untagged_ports=json.loads(row[6]) if row[6] else None,
                ip_range=row[7],
                priority=row[8],
                enabled=bool(row[9]),
            )
            self.vlans[vlan.vlan_id] = vlan

        conn.close()
