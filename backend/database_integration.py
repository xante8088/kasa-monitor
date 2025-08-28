"""
Integration layer for database systems with retry logic and connection pooling
Provides backward compatibility while enhancing reliability
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from database import DatabaseManager
from database_pool import DatabasePool, init_pool, get_pool
from retry_utils import (
    DATABASE_RETRY_CONFIG,
    RetryConfig,
    retry_async,
    get_retry_stats,
    reset_retry_stats,
)

logger = logging.getLogger(__name__)


class EnhancedDatabaseManager(DatabaseManager):
    """
    Enhanced DatabaseManager with retry logic and connection pooling support
    Maintains backward compatibility while adding reliability features
    """

    def __init__(self, use_pool: bool = True):
        super().__init__()
        self.use_pool = use_pool
        self.pool: Optional[DatabasePool] = None

    async def initialize(self):
        """Initialize enhanced database connections with retry logic and pooling."""
        if self.use_pool:
            await self._initialize_with_pool()
        else:
            await super().initialize()

    async def _initialize_with_pool(self):
        """Initialize using connection pool for better resource management."""
        try:
            # Initialize the global pool if not already done
            self.pool = get_pool()

            # Test pool connectivity
            health = await self.pool.enhanced_health_check()
            if health["status"] != "healthy":
                logger.warning(f"Pool health check shows issues: {health}")

            # Initialize direct connections as fallback
            await super().initialize()

            logger.info("Enhanced database manager initialized with connection pool")

        except Exception as e:
            logger.error(
                f"Failed to initialize with pool, falling back to direct connections: {e}"
            )
            # Fallback to direct connection mode
            self.use_pool = False
            await super().initialize()

    @retry_async(
        config=DATABASE_RETRY_CONFIG, operation_name="enhanced_store_device_reading"
    )
    async def store_device_reading(self, device_data):
        """Enhanced store_device_reading with automatic retry logic."""
        if self.use_pool and self.pool:
            return await self._store_device_reading_with_pool(device_data)
        else:
            return await super().store_device_reading(device_data)

    async def _store_device_reading_with_pool(self, device_data):
        """Store device reading using connection pool."""
        try:
            # Use pooled session for better resource management
            async with self.pool.get_async_db() as session:
                # Execute the storage operation within the pooled session
                await self._store_sqlite_reading(device_data)

                # Store InfluxDB data if configured
                if self.use_influx and self.influx_client:
                    await self._store_influx_reading(device_data)

        except Exception as e:
            logger.error(f"Failed to store device reading with pool: {e}")
            # Fallback to direct connection
            await super().store_device_reading(device_data)

    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status including retry statistics."""
        status = {
            "database_manager": {
                "sqlite_connected": self.sqlite_conn is not None,
                "influx_connected": self.influx_client is not None,
                "using_pool": self.use_pool,
            },
            "retry_statistics": get_retry_stats(),
        }

        # Add pool health if available
        if self.use_pool and self.pool:
            try:
                pool_health = await self.pool.enhanced_health_check()
                status["connection_pool"] = pool_health
            except Exception as e:
                status["connection_pool"] = {"status": "error", "error": str(e)}

        return status

    async def optimize_performance(self) -> Dict[str, Any]:
        """Optimize database performance based on usage patterns."""
        optimizations = []

        try:
            # Optimize pool settings if using pool
            if self.use_pool and self.pool:
                self.pool.optimize_pool()
                optimizations.append("Pool optimization completed")

            # SQLite optimizations
            if self.sqlite_conn:
                await self.sqlite_conn.execute("ANALYZE")
                await self.sqlite_conn.execute("VACUUM")
                optimizations.append("SQLite analysis and vacuum completed")

            # Reset retry statistics for fresh monitoring
            reset_retry_stats()
            optimizations.append("Retry statistics reset")

            return {
                "status": "success",
                "optimizations": optimizations,
                "timestamp": asyncio.get_event_loop().time(),
            }

        except Exception as e:
            logger.error(f"Performance optimization failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "optimizations": optimizations,
            }

    async def close(self):
        """Enhanced close with proper cleanup."""
        try:
            # Close parent connections
            await super().close()

            # Close pool if we own it
            if self.use_pool and self.pool:
                await self.pool.async_close()

            logger.info("Enhanced database manager closed successfully")

        except Exception as e:
            logger.error(f"Error closing enhanced database manager: {e}")


class DatabaseHealthMonitor:
    """
    Monitors database health and provides alerts for issues
    """

    def __init__(self, db_manager: EnhancedDatabaseManager, check_interval: int = 60):
        self.db_manager = db_manager
        self.check_interval = check_interval
        self.monitoring = False
        self.last_status = None
        self.alert_threshold = 3  # Number of consecutive failures before alert
        self.consecutive_failures = 0

    async def start_monitoring(self):
        """Start health monitoring background task."""
        if self.monitoring:
            return

        self.monitoring = True
        asyncio.create_task(self._monitoring_loop())
        logger.info("Database health monitoring started")

    async def stop_monitoring(self):
        """Stop health monitoring."""
        self.monitoring = False
        logger.info("Database health monitoring stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                health_status = await self.db_manager.get_health_status()

                # Check for issues
                issues = self._analyze_health_status(health_status)

                if issues:
                    self.consecutive_failures += 1
                    logger.warning(f"Database health issues detected: {issues}")

                    if self.consecutive_failures >= self.alert_threshold:
                        await self._trigger_alert(issues)

                else:
                    self.consecutive_failures = 0

                self.last_status = health_status

            except Exception as e:
                logger.error(f"Health monitoring check failed: {e}")
                self.consecutive_failures += 1

            await asyncio.sleep(self.check_interval)

    def _analyze_health_status(self, status: Dict[str, Any]) -> List[str]:
        """Analyze health status and return list of issues."""
        issues = []

        # Check database manager status
        db_status = status.get("database_manager", {})
        if not db_status.get("sqlite_connected"):
            issues.append("SQLite connection lost")

        # Check connection pool status
        pool_status = status.get("connection_pool", {})
        if pool_status.get("status") == "unhealthy":
            issues.append(
                f"Connection pool unhealthy: {pool_status.get('error', 'Unknown error')}"
            )

        # Check retry statistics for high failure rates
        retry_stats = status.get("retry_statistics", {})
        if retry_stats.get("failed_attempts", 0) > 10:
            success_rate = retry_stats.get("success_rate", 1.0)
            if success_rate < 0.8:  # Less than 80% success rate
                issues.append(
                    f"High failure rate in database operations: {success_rate:.1%}"
                )

        return issues

    async def _trigger_alert(self, issues: List[str]):
        """Trigger alert for persistent issues."""
        logger.error(
            f"Database alert triggered after {self.consecutive_failures} consecutive failures:"
        )
        for issue in issues:
            logger.error(f"  - {issue}")

        # Here you could integrate with alerting systems
        # Example: send email, webhook, or notification

        # Attempt automatic recovery
        try:
            logger.info("Attempting automatic database recovery...")
            await self.db_manager.optimize_performance()
            logger.info("Automatic recovery attempt completed")
        except Exception as e:
            logger.error(f"Automatic recovery failed: {e}")


def create_enhanced_database_manager(
    use_pool: bool = True,
    pool_config: Optional[Dict[str, Any]] = None,
    start_monitoring: bool = True,
) -> EnhancedDatabaseManager:
    """
    Factory function to create an enhanced database manager with optimal settings.

    Args:
        use_pool: Whether to use connection pooling
        pool_config: Configuration for connection pool
        start_monitoring: Whether to start health monitoring

    Returns:
        Configured EnhancedDatabaseManager instance
    """

    # Initialize pool if requested
    if use_pool and pool_config:
        init_pool(**pool_config)

    # Create enhanced manager
    manager = EnhancedDatabaseManager(use_pool=use_pool)

    # Set up monitoring if requested
    if start_monitoring:
        monitor = DatabaseHealthMonitor(manager)
        # Note: monitoring will be started after manager initialization

    return manager


# Default configuration for production use
PRODUCTION_CONFIG = {
    "pool_size": 20,
    "max_overflow": 10,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "echo_pool": False,
    "use_async": True,
}

DEVELOPMENT_CONFIG = {
    "pool_size": 5,
    "max_overflow": 2,
    "pool_timeout": 10,
    "pool_recycle": 1800,
    "echo_pool": True,
    "use_async": True,
}


async def initialize_database_system(
    environment: str = "production",
) -> EnhancedDatabaseManager:
    """
    Initialize the complete database system with appropriate configuration.

    Args:
        environment: 'production', 'development', or 'testing'

    Returns:
        Initialized EnhancedDatabaseManager
    """

    config = PRODUCTION_CONFIG if environment == "production" else DEVELOPMENT_CONFIG

    # Create and initialize manager
    manager = create_enhanced_database_manager(
        use_pool=True, pool_config=config, start_monitoring=environment == "production"
    )

    await manager.initialize()

    # Start monitoring for production
    if environment == "production":
        monitor = DatabaseHealthMonitor(manager)
        await monitor.start_monitoring()

    logger.info(f"Database system initialized for {environment} environment")
    return manager
