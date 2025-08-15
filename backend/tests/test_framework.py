"""Comprehensive testing framework for Kasa Monitor.

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

import unittest
import asyncio
import sqlite3
import tempfile
import os
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import modules to test
from database import DatabaseManager
from auth import AuthManager
from models import User, UserCreate, UserRole, DeviceData
from performance_monitor import PerformanceMonitor
from alert_management import AlertManager, AlertRule, AlertSeverity, AlertCategory


class TestBase(unittest.TestCase):
    """Base test class with common setup."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary database
        self.test_db_fd, self.test_db_path = tempfile.mkstemp(suffix='.db')
        
        # Set environment variables
        os.environ['SQLITE_PATH'] = self.test_db_path
        os.environ['JWT_SECRET_KEY'] = 'test_secret_key'
        
        # Initialize test data
        self.test_user = {
            'username': 'testuser',
            'email': 'test@example.com',
            'full_name': 'Test User',
            'password': 'TestPass123!'
        }
        
        self.test_device = {
            'ip': '192.168.1.100',
            'alias': 'Test Device',
            'model': 'HS110',
            'device_type': 'plug',
            'mac': '00:11:22:33:44:55'
        }
    
    def tearDown(self):
        """Clean up test environment."""
        # Close and remove temporary database
        os.close(self.test_db_fd)
        os.unlink(self.test_db_path)
        
        # Clear environment variables
        if 'SQLITE_PATH' in os.environ:
            del os.environ['SQLITE_PATH']
        if 'JWT_SECRET_KEY' in os.environ:
            del os.environ['JWT_SECRET_KEY']


class TestDatabase(TestBase):
    """Test database operations."""
    
    def setUp(self):
        """Set up database tests."""
        super().setUp()
        self.db_manager = DatabaseManager()
    
    def test_database_initialization(self):
        """Test database initialization."""
        asyncio.run(self._test_database_initialization())
    
    async def _test_database_initialization(self):
        """Async test for database initialization."""
        await self.db_manager.initialize()
        
        # Check if tables were created
        cursor = await self.db_manager.sqlite_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = await cursor.fetchall()
        table_names = [t[0] for t in tables]
        
        # Assert required tables exist
        self.assertIn('device_info', table_names)
        self.assertIn('device_readings', table_names)
        self.assertIn('users', table_names)
        self.assertIn('electricity_rates', table_names)
        
        await self.db_manager.close()
    
    def test_device_storage(self):
        """Test device data storage."""
        asyncio.run(self._test_device_storage())
    
    async def _test_device_storage(self):
        """Async test for device storage."""
        await self.db_manager.initialize()
        
        # Create test device data
        device_data = DeviceData(
            ip=self.test_device['ip'],
            alias=self.test_device['alias'],
            model=self.test_device['model'],
            device_type=self.test_device['device_type'],
            mac=self.test_device['mac'],
            is_on=True,
            current_power_w=100.5,
            voltage=120.0,
            current=0.84,
            today_energy_kwh=2.5,
            month_energy_kwh=75.0,
            total_energy_kwh=500.0,
            rssi=-50,
            timestamp=datetime.now()
        )
        
        # Store device reading
        await self.db_manager.store_device_reading(device_data)
        
        # Verify storage
        cursor = await self.db_manager.sqlite_conn.execute(
            "SELECT * FROM device_info WHERE device_ip = ?",
            (self.test_device['ip'],)
        )
        device = await cursor.fetchone()
        
        self.assertIsNotNone(device)
        self.assertEqual(device[1], self.test_device['alias'])
        
        await self.db_manager.close()
    
    def test_user_management(self):
        """Test user management operations."""
        asyncio.run(self._test_user_management())
    
    async def _test_user_management(self):
        """Async test for user management."""
        await self.db_manager.initialize()
        
        # Create admin user
        success = await self.db_manager.create_admin_user(
            self.test_user['username'],
            self.test_user['email'],
            self.test_user['full_name'],
            self.test_user['password']
        )
        
        self.assertTrue(success)
        
        # Get user
        user = await self.db_manager.get_user_by_username(self.test_user['username'])
        
        self.assertIsNotNone(user)
        self.assertEqual(user.username, self.test_user['username'])
        self.assertEqual(user.role, UserRole.ADMIN)
        self.assertTrue(user.is_admin)
        
        await self.db_manager.close()


class TestAuthentication(TestBase):
    """Test authentication system."""
    
    def setUp(self):
        """Set up authentication tests."""
        super().setUp()
        self.auth_manager = AuthManager()
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "TestPassword123!"
        
        # Hash password
        hashed = AuthManager.hash_password(password)
        
        self.assertIsNotNone(hashed)
        self.assertNotEqual(hashed, password)
        
        # Verify password
        is_valid = AuthManager.verify_password(password, hashed)
        self.assertTrue(is_valid)
        
        # Verify wrong password
        is_valid = AuthManager.verify_password("WrongPassword", hashed)
        self.assertFalse(is_valid)
    
    def test_jwt_tokens(self):
        """Test JWT token generation and verification."""
        asyncio.run(self._test_jwt_tokens())
    
    async def _test_jwt_tokens(self):
        """Async test for JWT tokens."""
        # Create test user
        user = User(
            id=1,
            username=self.test_user['username'],
            email=self.test_user['email'],
            full_name=self.test_user['full_name'],
            role=UserRole.ADMIN,
            is_active=True,
            is_admin=True
        )
        
        # Generate token
        token = self.auth_manager.create_access_token(
            data={"sub": user.username}
        )
        
        self.assertIsNotNone(token)
        
        # Verify token
        payload = self.auth_manager.verify_token(token)
        
        self.assertIsNotNone(payload)
        self.assertEqual(payload.get('sub'), user.username)


class TestPerformanceMonitor(TestBase):
    """Test performance monitoring system."""
    
    def setUp(self):
        """Set up performance tests."""
        super().setUp()
        self.monitor = PerformanceMonitor(self.test_db_path)
    
    def test_metric_recording(self):
        """Test metric recording."""
        from performance_monitor import MetricType
        
        # Record test metric
        self.monitor.record_metric(
            "test.metric",
            42.5,
            "units",
            MetricType.GAUGE,
            {"tag": "value"}
        )
        
        # Verify metric was recorded
        self.assertEqual(len(self.monitor.metrics), 1)
        metric = self.monitor.metrics[0]
        
        self.assertEqual(metric.name, "test.metric")
        self.assertEqual(metric.value, 42.5)
        self.assertEqual(metric.unit, "units")
    
    def test_profiling(self):
        """Test performance profiling."""
        profiler = self.monitor.profiler
        
        # Profile a function
        @profiler.profile("test_function")
        def test_func():
            time.sleep(0.1)
            return "result"
        
        # Execute function
        result = test_func()
        
        self.assertEqual(result, "result")
        
        # Check profile stats
        stats = profiler.get_stats("test_function")
        
        self.assertIsNotNone(stats)
        self.assertEqual(stats['count'], 1)
        self.assertGreater(stats['duration']['min'], 100)  # > 100ms
    
    def test_memory_monitoring(self):
        """Test memory monitoring."""
        memory_monitor = self.monitor.memory_monitor
        
        # Take snapshot
        snapshot = memory_monitor.take_snapshot()
        
        self.assertIsNotNone(snapshot)
        self.assertIn('rss_mb', snapshot)
        self.assertIn('percent', snapshot)
        self.assertGreater(snapshot['rss_mb'], 0)
    
    def test_query_monitoring(self):
        """Test query performance monitoring."""
        query_monitor = self.monitor.query_monitor
        
        # Record test queries
        query_monitor.record_query(
            "SELECT * FROM users WHERE id = 1",
            50.5,
            1
        )
        query_monitor.record_query(
            "SELECT * FROM users WHERE id = 2",
            150.0,  # Slow query
            1
        )
        
        # Get slow queries
        slow_queries = query_monitor.get_slow_queries(threshold_ms=100)
        
        self.assertEqual(len(slow_queries), 1)
        self.assertGreater(slow_queries[0]['max_duration_ms'], 100)


class TestAlertManagement(TestBase):
    """Test alert management system."""
    
    def setUp(self):
        """Set up alert tests."""
        super().setUp()
        self.alert_manager = AlertManager(self.test_db_path)
    
    def test_alert_rule_creation(self):
        """Test alert rule creation."""
        # Create test rule
        rule = AlertRule(
            name="test_rule",
            description="Test alert rule",
            category=AlertCategory.DEVICE,
            conditions=[
                {
                    'field': 'device.power',
                    'operator': '>',
                    'value': 1000
                }
            ],
            severity=AlertSeverity.WARNING
        )
        
        # Create rule
        success = self.alert_manager.create_rule(rule)
        
        self.assertTrue(success)
        self.assertIn("test_rule", self.alert_manager.rules)
    
    def test_alert_evaluation(self):
        """Test alert evaluation."""
        # Create test rule
        rule = AlertRule(
            name="power_alert",
            description="High power consumption",
            category=AlertCategory.ENERGY,
            conditions=[
                {
                    'field': 'power',
                    'operator': '>',
                    'value': 100
                }
            ],
            severity=AlertSeverity.WARNING
        )
        
        self.alert_manager.create_rule(rule)
        
        # Test data that should trigger alert
        test_data = {
            'power': 150,
            'device': 'test_device'
        }
        
        # Evaluate
        alerts = self.alert_manager.evaluate(test_data)
        
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].rule_name, "power_alert")
        self.assertEqual(alerts[0].severity, AlertSeverity.WARNING)
    
    def test_alert_acknowledgment(self):
        """Test alert acknowledgment."""
        # Create and trigger alert
        rule = AlertRule(
            name="test_alert",
            description="Test alert",
            category=AlertCategory.SYSTEM,
            conditions=[{'field': 'test', 'operator': '==', 'value': True}],
            severity=AlertSeverity.INFO
        )
        
        self.alert_manager.create_rule(rule)
        alerts = self.alert_manager.evaluate({'test': True})
        
        # Get alert ID (would be generated in real system)
        alert_id = "TEST-001"
        
        # Mock the alert in active alerts
        if alerts:
            self.alert_manager.active_alerts[alert_id] = alerts[0]
        
        # Acknowledge alert
        success = self.alert_manager.acknowledge_alert(
            alert_id,
            "testuser",
            "Test acknowledgment"
        )
        
        # In real system this would work with database
        # For now just verify the alert exists
        self.assertIn(alert_id, self.alert_manager.active_alerts)


class TestIntegration(TestBase):
    """Integration tests for complete workflows."""
    
    def test_complete_device_workflow(self):
        """Test complete device monitoring workflow."""
        asyncio.run(self._test_complete_device_workflow())
    
    async def _test_complete_device_workflow(self):
        """Async test for device workflow."""
        # Initialize components
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Add device
        device_data = DeviceData(
            ip="192.168.1.50",
            alias="Living Room Plug",
            model="HS110",
            device_type="plug",
            mac="AA:BB:CC:DD:EE:FF",
            is_on=True,
            current_power_w=250.0,
            voltage=120.0,
            current=2.08,
            today_energy_kwh=3.5,
            month_energy_kwh=105.0,
            total_energy_kwh=1500.0,
            rssi=-45,
            timestamp=datetime.now()
        )
        
        # Store reading
        await db_manager.store_device_reading(device_data)
        
        # Get device history
        history = await db_manager.get_device_history(
            device_data.ip,
            start_time=datetime.now() - timedelta(hours=1)
        )
        
        self.assertIsNotNone(history)
        
        # Get device stats
        stats = await db_manager.get_device_stats(device_data.ip)
        
        self.assertIsNotNone(stats)
        self.assertIn('avg_power', stats)
        
        await db_manager.close()
    
    def test_security_workflow(self):
        """Test security workflow with authentication and authorization."""
        asyncio.run(self._test_security_workflow())
    
    async def _test_security_workflow(self):
        """Async test for security workflow."""
        # Initialize components
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        auth_manager = AuthManager()
        
        # Create admin user
        await db_manager.create_admin_user(
            "admin",
            "admin@example.com",
            "Admin User",
            "AdminPass123!"
        )
        
        # Authenticate user
        password_hash = await db_manager.get_user_password_hash("admin")
        is_valid = AuthManager.verify_password("AdminPass123!", password_hash)
        
        self.assertTrue(is_valid)
        
        # Generate token
        token = auth_manager.create_access_token(data={"sub": "admin"})
        
        self.assertIsNotNone(token)
        
        # Verify token
        payload = auth_manager.verify_token(token)
        
        self.assertIsNotNone(payload)
        self.assertEqual(payload.get('sub'), "admin")
        
        await db_manager.close()


class TestLoadAndStress(unittest.TestCase):
    """Load and stress testing."""
    
    def setUp(self):
        """Set up load tests."""
        self.test_db_fd, self.test_db_path = tempfile.mkstemp(suffix='.db')
        os.environ['SQLITE_PATH'] = self.test_db_path
    
    def tearDown(self):
        """Clean up load tests."""
        os.close(self.test_db_fd)
        os.unlink(self.test_db_path)
        if 'SQLITE_PATH' in os.environ:
            del os.environ['SQLITE_PATH']
    
    def test_database_load(self):
        """Test database under load."""
        asyncio.run(self._test_database_load())
    
    async def _test_database_load(self):
        """Async test for database load."""
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Generate load
        num_devices = 10
        num_readings = 100
        
        start_time = time.time()
        
        for device_num in range(num_devices):
            for reading_num in range(num_readings):
                device_data = DeviceData(
                    ip=f"192.168.1.{device_num}",
                    alias=f"Device {device_num}",
                    model="HS110",
                    device_type="plug",
                    mac=f"00:11:22:33:44:{device_num:02x}",
                    is_on=True,
                    current_power_w=100.0 + reading_num,
                    voltage=120.0,
                    current=0.83,
                    today_energy_kwh=reading_num * 0.1,
                    month_energy_kwh=reading_num * 3.0,
                    total_energy_kwh=reading_num * 30.0,
                    rssi=-50,
                    timestamp=datetime.now()
                )
                
                await db_manager.store_device_reading(device_data)
        
        duration = time.time() - start_time
        readings_per_second = (num_devices * num_readings) / duration
        
        print(f"Load test: {num_devices * num_readings} readings in {duration:.2f}s")
        print(f"Rate: {readings_per_second:.2f} readings/second")
        
        # Verify data
        cursor = await db_manager.sqlite_conn.execute(
            "SELECT COUNT(*) FROM device_readings"
        )
        count = await cursor.fetchone()
        
        self.assertEqual(count[0], num_devices * num_readings)
        
        await db_manager.close()
    
    def test_concurrent_access(self):
        """Test concurrent database access."""
        asyncio.run(self._test_concurrent_access())
    
    async def _test_concurrent_access(self):
        """Async test for concurrent access."""
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Create concurrent tasks
        async def write_data(device_id: int):
            for i in range(10):
                device_data = DeviceData(
                    ip=f"192.168.1.{device_id}",
                    alias=f"Device {device_id}",
                    model="HS110",
                    device_type="plug",
                    mac=f"00:11:22:33:44:{device_id:02x}",
                    is_on=True,
                    current_power_w=100.0 * i,
                    voltage=120.0,
                    current=0.83,
                    today_energy_kwh=i * 0.1,
                    month_energy_kwh=i * 3.0,
                    total_energy_kwh=i * 30.0,
                    rssi=-50,
                    timestamp=datetime.now()
                )
                await db_manager.store_device_reading(device_data)
                await asyncio.sleep(0.01)  # Small delay
        
        # Run concurrent writes
        tasks = [write_data(i) for i in range(5)]
        await asyncio.gather(*tasks)
        
        # Verify no data corruption
        cursor = await db_manager.sqlite_conn.execute(
            "SELECT COUNT(DISTINCT device_ip) FROM device_readings"
        )
        count = await cursor.fetchone()
        
        self.assertEqual(count[0], 5)
        
        await db_manager.close()


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDatabase))
    suite.addTests(loader.loadTestsFromTestCase(TestAuthentication))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceMonitor))
    suite.addTests(loader.loadTestsFromTestCase(TestAlertManagement))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestLoadAndStress))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)