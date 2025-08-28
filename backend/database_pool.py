"""
Database connection pooling and session management for Kasa Monitor
Implements SQLAlchemy connection pooling with monitoring and optimization
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, Generator, Optional

import aiosqlite
from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.exc import DBAPIError, DisconnectionError, TimeoutError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool, StaticPool

from retry_utils import DATABASE_RETRY_CONFIG, RetryConfig, retry_async

logger = logging.getLogger(__name__)


class DatabasePool:
    """Manages database connection pooling and session lifecycle"""

    def __init__(
        self,
        database_url: Optional[str] = None,
        pool_size: int = 20,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        echo_pool: bool = False,
        use_async: bool = True,
    ):
        """
        Initialize database connection pool

        Args:
            database_url: Database connection URL
            pool_size: Number of connections to maintain in pool
            max_overflow: Maximum overflow connections allowed
            pool_timeout: Timeout for getting connection from pool
            pool_recycle: Time to recycle connections (seconds)
            echo_pool: Enable pool logging
            use_async: Use async engine and sessions
        """
        self.database_url = database_url or self._get_database_url()
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo_pool = echo_pool
        self.use_async = use_async

        # Connection tracking
        self.active_connections = 0
        self.total_connections = 0
        self.failed_connections = 0
        self.connection_wait_time = []

        # Initialize engines and sessions
        if use_async:
            self._setup_async_engine()
        else:
            self._setup_sync_engine()

        # Setup event listeners
        self._setup_event_listeners()

        # Pool statistics
        self.stats = {
            "created_at": datetime.now(),
            "connections_created": 0,
            "connections_recycled": 0,
            "connections_failed": 0,
            "overflow_created": 0,
            "pool_timeouts": 0,
            "health_checks_performed": 0,
            "health_checks_failed": 0,
            "connections_recovered": 0,
        }
        
        # Health monitoring
        self.last_health_check = None
        self.consecutive_failures = 0
        self.is_healthy = True
        self.health_check_interval = 60  # seconds
        self.max_consecutive_failures = 3

    def _get_database_url(self) -> str:
        """Get database URL from environment or default"""
        # Check for environment variable
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            return db_url

        # Default to SQLite
        db_path = os.getenv("DATABASE_PATH", "data/kasa_monitor.db")

        # For async SQLite
        if self.use_async:
            return f"sqlite+aiosqlite:///{db_path}"
        return f"sqlite:///{db_path}"

    def _setup_sync_engine(self):
        """Setup synchronous SQLAlchemy engine"""
        # Determine poolclass based on database type
        if "sqlite" in self.database_url:
            # SQLite doesn't support true connection pooling
            poolclass = StaticPool if ":memory:" in self.database_url else NullPool
            pool_kwargs = {"connect_args": {"check_same_thread": False}}
        else:
            poolclass = QueuePool
            pool_kwargs = {
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "pool_timeout": self.pool_timeout,
                "pool_recycle": self.pool_recycle,
                "echo_pool": self.echo_pool,
                "pool_pre_ping": True,  # Verify connections before using
            }

        self.engine = create_engine(
            self.database_url, poolclass=poolclass, **pool_kwargs
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # Create scoped session for thread safety
        self.Session = scoped_session(self.SessionLocal)

    def _setup_async_engine(self):
        """Setup asynchronous SQLAlchemy engine"""
        # Async pool configuration
        if "sqlite" in self.database_url:
            # SQLite async configuration
            connect_args = {"check_same_thread": False}
            poolclass = StaticPool if ":memory:" in self.database_url else NullPool
        else:
            connect_args = {}
            poolclass = QueuePool

        pool_kwargs = {
            "echo_pool": self.echo_pool,
            "pool_pre_ping": True,
            "connect_args": connect_args,
        }

        if poolclass == QueuePool:
            pool_kwargs.update(
                {
                    "pool_size": self.pool_size,
                    "max_overflow": self.max_overflow,
                    "pool_timeout": self.pool_timeout,
                    "pool_recycle": self.pool_recycle,
                }
            )

        self.async_engine = create_async_engine(
            self.database_url, poolclass=poolclass, **pool_kwargs
        )

        # Create async session factory
        self.AsyncSessionLocal = async_sessionmaker(
            self.async_engine, class_=AsyncSession, expire_on_commit=False
        )

    def _setup_event_listeners(self):
        """Setup SQLAlchemy event listeners for monitoring"""
        engine = self.engine if hasattr(self, "engine") else self.async_engine

        @event.listens_for(engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Handle new connection creation"""
            self.stats["connections_created"] += 1
            self.active_connections += 1
            self.total_connections += 1

            # Set connection properties for better performance
            if "sqlite" in self.database_url:
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=10000")
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.close()

            logger.debug(f"New connection created. Active: {self.active_connections}")

        @event.listens_for(engine, "close")
        def receive_close(dbapi_conn, connection_record):
            """Handle connection close"""
            self.active_connections -= 1
            logger.debug(f"Connection closed. Active: {self.active_connections}")

        @event.listens_for(engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Handle connection checkout from pool"""
            checkout_time = datetime.now()
            connection_record.info["checkout_time"] = checkout_time

        @event.listens_for(engine, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            """Handle connection checkin to pool"""
            if "checkout_time" in connection_record.info:
                duration = (
                    datetime.now() - connection_record.info["checkout_time"]
                ).total_seconds()
                self.connection_wait_time.append(duration)

                # Keep only last 100 measurements
                if len(self.connection_wait_time) > 100:
                    self.connection_wait_time.pop(0)

    @contextmanager
    def get_db(self) -> Generator[Session, None, None]:
        """
        Get a database session (sync) with enhanced error handling

        Yields:
            Database session
        """
        if not hasattr(self, "SessionLocal"):
            raise RuntimeError("Sync engine not initialized")

        db = None
        try:
            db = self.SessionLocal()
            yield db
            db.commit()
        except Exception as e:
            if db:
                try:
                    db.rollback()
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")
                    
            logger.error(f"Database session error: {e}")
            self.failed_connections += 1
            raise
        finally:
            if db:
                try:
                    db.close()
                except Exception as close_error:
                    logger.error(f"Failed to close database session: {close_error}")

    @asynccontextmanager
    async def get_async_db(self):
        """
        Get an async database session with enhanced error handling

        Yields:
            Async database session
        """
        if not hasattr(self, "AsyncSessionLocal"):
            raise RuntimeError("Async engine not initialized")

        session = None
        try:
            session = self.AsyncSessionLocal()
            yield session
            await session.commit()
        except Exception as e:
            if session:
                try:
                    await session.rollback()
                except Exception as rollback_error:
                    logger.error(f"Async rollback failed: {rollback_error}")
                    
            logger.error(f"Async database session error: {e}")
            self.failed_connections += 1
            raise
        finally:
            if session:
                try:
                    await session.close()
                except Exception as close_error:
                    logger.error(f"Failed to close async database session: {close_error}")
    
    @retry_async(
        config=DATABASE_RETRY_CONFIG,
        operation_name="get_resilient_session"
    )
    async def get_resilient_async_session(self):
        """
        Get a resilient async session that automatically retries on connection failures
        
        Yields:
            Async database session with retry logic
        """
        async with self.get_async_db() as session:
            yield session

    def execute_query(self, query: str, params: Optional[Dict] = None) -> Any:
        """
        Execute a raw SQL query (sync)

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query result
        """
        with self.get_db() as db:
            result = db.execute(text(query), params or {})
            return result.fetchall()

    async def execute_async_query(
        self, query: str, params: Optional[Dict] = None
    ) -> Any:
        """
        Execute a raw SQL query (async)

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query result
        """
        async with self.get_async_db() as db:
            result = await db.execute(text(query), params or {})
            return result.fetchall()

    @retry_async(
        config=DATABASE_RETRY_CONFIG,
        operation_name="database_health_check"
    )
    async def enhanced_health_check(self) -> Dict[str, Any]:
        """
        Perform enhanced health check with recovery capabilities
        
        Returns:
            Health status dictionary with detailed metrics
        """
        self.stats["health_checks_performed"] += 1
        check_start_time = time.time()
        
        try:
            # Test async connection if available
            if hasattr(self, "async_engine"):
                async with self.async_engine.connect() as conn:
                    result = await conn.execute(text("SELECT 1"))
                    await result.fetchone()
            elif hasattr(self, "engine"):
                # Fallback to sync connection test
                with self.engine.connect() as conn:
                    result = conn.execute(text("SELECT 1"))
                    result.fetchone()
            else:
                raise RuntimeError("No database engine available")

            # Get pool statistics
            pool_impl = getattr(self, "async_engine", getattr(self, "engine", None)).pool
            check_duration = time.time() - check_start_time

            status = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "check_duration_ms": round(check_duration * 1000, 2),
                "active_connections": self.active_connections,
                "total_connections": self.total_connections,
                "failed_connections": self.failed_connections,
                "consecutive_failures": self.consecutive_failures,
                "pool_metrics": {
                    "pool_size": getattr(pool_impl, "size", lambda: 0)() if callable(getattr(pool_impl, "size", 0)) else getattr(pool_impl, "size", 0),
                    "overflow": getattr(pool_impl, "overflow", lambda: 0)() if callable(getattr(pool_impl, "overflow", 0)) else getattr(pool_impl, "overflow", 0),
                    "checked_in": getattr(pool_impl, "checkedin", lambda: 0)() if callable(getattr(pool_impl, "checkedin", 0)) else getattr(pool_impl, "checkedin", 0),
                    "checked_out": getattr(pool_impl, "checkedout", lambda: 0)() if callable(getattr(pool_impl, "checkedout", 0)) else getattr(pool_impl, "checkedout", 0),
                },
                "performance_metrics": self._get_performance_metrics(),
                "stats": self.stats.copy(),
            }

            # Reset failure counter on successful health check
            self.consecutive_failures = 0
            self.is_healthy = True
            self.last_health_check = datetime.now()
            
            return status

        except Exception as e:
            self.stats["health_checks_failed"] += 1
            self.consecutive_failures += 1
            check_duration = time.time() - check_start_time
            
            # Mark as unhealthy if too many consecutive failures
            if self.consecutive_failures >= self.max_consecutive_failures:
                self.is_healthy = False
                logger.error(f"Database marked as unhealthy after {self.consecutive_failures} consecutive failures")
                
                # Attempt connection recovery
                await self._attempt_recovery()

            logger.error(f"Health check failed after {check_duration:.2f}s: {e}")
            
            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "check_duration_ms": round(check_duration * 1000, 2),
                "error": str(e),
                "consecutive_failures": self.consecutive_failures,
                "active_connections": self.active_connections,
                "failed_connections": self.failed_connections,
                "is_healthy": self.is_healthy,
                "stats": self.stats.copy(),
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Synchronous health check for compatibility
        
        Returns:
            Health status dictionary
        """
        try:
            # Test connection
            if hasattr(self, "engine"):
                with self.engine.connect() as conn:
                    result = conn.execute(text("SELECT 1"))
                    result.fetchone()
            else:
                raise RuntimeError("No sync engine available")

            # Get pool statistics
            pool_impl = self.engine.pool

            status = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "active_connections": self.active_connections,
                "total_connections": self.total_connections,
                "failed_connections": self.failed_connections,
                "pool_size": getattr(pool_impl, "size", 0),
                "overflow": getattr(pool_impl, "overflow", 0),
                "checked_in": getattr(pool_impl, "checkedin", 0),
                "stats": self.stats.copy(),
            }

            # Calculate average wait time
            if self.connection_wait_time:
                status["avg_wait_time_ms"] = (
                    sum(self.connection_wait_time)
                    / len(self.connection_wait_time)
                    * 1000
                )

            return status

        except Exception as e:
            self.consecutive_failures += 1
            logger.error(f"Sync health check failed: {e}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "consecutive_failures": self.consecutive_failures,
                "active_connections": self.active_connections,
                "failed_connections": self.failed_connections,
            }
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the connection pool"""
        metrics = {}
        
        # Connection wait times
        if self.connection_wait_time:
            wait_times = self.connection_wait_time
            metrics.update({
                "avg_wait_time_ms": sum(wait_times) / len(wait_times) * 1000,
                "min_wait_time_ms": min(wait_times) * 1000,
                "max_wait_time_ms": max(wait_times) * 1000,
                "wait_time_samples": len(wait_times),
            })
        
        # Connection utilization
        if hasattr(self, "engine"):
            pool_impl = self.engine.pool
            pool_size = getattr(pool_impl, "size", lambda: 0)()
            if pool_size > 0:
                utilization = (self.active_connections / pool_size) * 100
                metrics["pool_utilization_percent"] = round(utilization, 2)
        
        return metrics
    
    async def _attempt_recovery(self):
        """Attempt to recover from connection failures"""
        logger.info("Attempting database connection recovery...")
        
        try:
            # Close existing connections
            if hasattr(self, "engine"):
                self.engine.dispose()
                logger.info("Disposed of sync engine connections")
                
            if hasattr(self, "async_engine"):
                await self.async_engine.dispose()  
                logger.info("Disposed of async engine connections")
            
            # Recreate engines
            if self.use_async:
                self._setup_async_engine()
            else:
                self._setup_sync_engine()
                
            # Re-setup event listeners
            self._setup_event_listeners()
            
            self.stats["connections_recovered"] += 1
            logger.info("Database connection recovery completed successfully")
            
        except Exception as e:
            logger.error(f"Database connection recovery failed: {e}")
            raise

    async def async_health_check(self) -> Dict[str, Any]:
        """
        Perform async health check on connection pool

        Returns:
            Health status dictionary
        """
        try:
            # Test async connection
            async with self.async_engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.fetchone()

            return {
                "status": "healthy",
                "active_connections": self.active_connections,
                "total_connections": self.total_connections,
                "failed_connections": self.failed_connections,
                "stats": self.stats,
            }

        except Exception as e:
            logger.error(f"Async health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    def optimize_pool(self):
        """Optimize pool settings based on usage patterns"""
        if not self.connection_wait_time:
            return

        avg_wait = sum(self.connection_wait_time) / len(self.connection_wait_time)

        # If average wait time is high, consider increasing pool size
        if avg_wait > 1.0:  # More than 1 second average wait
            logger.warning(
                f"High connection wait time: {avg_wait:.2f}s. Consider increasing pool size."
            )

            # Auto-adjust if configured
            if hasattr(self.engine.pool, "size"):
                current_size = self.engine.pool.size()
                if current_size < 50:  # Max limit
                    new_size = min(current_size + 5, 50)
                    logger.info(
                        f"Adjusting pool size from {current_size} to {new_size}"
                    )
                    # Note: Pool size adjustment requires recreation in SQLAlchemy

        # Check for connection leaks
        if self.active_connections > self.pool_size * 1.5:
            logger.warning(
                f"Possible connection leak detected. Active: {self.active_connections}, Pool size: {self.pool_size}"
            )

    def close(self):
        """Close all connections and dispose of engine"""
        if hasattr(self, "engine"):
            self.engine.dispose()
            logger.info("Sync engine disposed")

        if hasattr(self, "Session"):
            self.Session.remove()

    async def async_close(self):
        """Close async connections and dispose of engine"""
        if hasattr(self, "async_engine"):
            await self.async_engine.dispose()
            logger.info("Async engine disposed")

    def get_statistics(self) -> Dict[str, Any]:
        """Get detailed pool statistics"""
        stats = {
            "pool_configuration": {
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "pool_timeout": self.pool_timeout,
                "pool_recycle": self.pool_recycle,
            },
            "runtime_stats": {
                "active_connections": self.active_connections,
                "total_connections": self.total_connections,
                "failed_connections": self.failed_connections,
                "connections_created": self.stats["connections_created"],
                "connections_recycled": self.stats["connections_recycled"],
                "pool_timeouts": self.stats["pool_timeouts"],
            },
            "performance_metrics": {},
        }

        # Add performance metrics
        if self.connection_wait_time:
            wait_times = self.connection_wait_time
            stats["performance_metrics"] = {
                "avg_wait_time_ms": sum(wait_times) / len(wait_times) * 1000,
                "min_wait_time_ms": min(wait_times) * 1000,
                "max_wait_time_ms": max(wait_times) * 1000,
                "samples": len(wait_times),
            }

        # Get pool implementation stats if available
        if hasattr(self, "engine"):
            pool_impl = self.engine.pool
            if hasattr(pool_impl, "size"):
                stats["pool_implementation"] = {
                    "type": pool_impl.__class__.__name__,
                    "size": getattr(pool_impl, "size", lambda: 0)(),
                    "checked_in": getattr(pool_impl, "checkedin", lambda: 0)(),
                    "overflow": getattr(pool_impl, "overflow", lambda: 0)(),
                    "total": getattr(pool_impl, "total", lambda: 0)(),
                }

        return stats


# Global pool instance
_pool_instance: Optional[DatabasePool] = None


def init_pool(**kwargs) -> DatabasePool:
    """
    Initialize global database pool

    Args:
        **kwargs: Pool configuration parameters

    Returns:
        DatabasePool instance
    """
    global _pool_instance
    _pool_instance = DatabasePool(**kwargs)
    return _pool_instance


def get_pool() -> DatabasePool:
    """
    Get global database pool instance

    Returns:
        DatabasePool instance
    """
    global _pool_instance
    if _pool_instance is None:
        _pool_instance = DatabasePool()
    return _pool_instance


# Dependency injection for FastAPI
async def get_async_session() -> AsyncSession:
    """FastAPI dependency for async database sessions"""
    pool = get_pool()
    async with pool.get_async_db() as session:
        yield session


def get_sync_session() -> Session:
    """FastAPI dependency for sync database sessions"""
    pool = get_pool()
    with pool.get_db() as session:
        yield session
