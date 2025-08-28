"""
Retry utilities for handling transient failures in Kasa Monitor
Implements exponential backoff with configurable strategies
"""

import asyncio
import functools
import logging
import random
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Available retry strategies"""

    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    RANDOM = "random"


class RetryResult(Enum):
    """Retry decision result"""

    RETRY = "retry"
    FAIL = "fail"
    SUCCESS = "success"


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""

    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay between retries
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    backoff_factor: float = 2.0  # Multiplier for exponential backoff
    jitter: bool = True  # Add randomization to prevent thundering herd

    # Exception handling
    retryable_exceptions: tuple = (
        ConnectionError,
        TimeoutError,
        OSError,
    )
    non_retryable_exceptions: tuple = (
        ValueError,
        TypeError,
        KeyError,
    )

    # Logging
    log_attempts: bool = True
    log_level: int = logging.WARNING


class RetryStats:
    """Statistics tracking for retry operations"""

    def __init__(self):
        self.total_attempts = 0
        self.successful_attempts = 0
        self.failed_attempts = 0
        self.retry_counts: Dict[str, int] = {}
        self.total_delay = 0.0

    def record_attempt(self, operation: str, attempt: int, success: bool, delay: float = 0.0):
        """Record a retry attempt"""
        self.total_attempts += 1
        self.total_delay += delay

        if success:
            self.successful_attempts += 1
        else:
            self.failed_attempts += 1

        self.retry_counts[operation] = self.retry_counts.get(operation, 0) + attempt

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        return {
            "total_attempts": self.total_attempts,
            "successful_attempts": self.successful_attempts,
            "failed_attempts": self.failed_attempts,
            "success_rate": (self.successful_attempts / self.total_attempts if self.total_attempts > 0 else 0.0),
            "average_delay": (self.total_delay / self.total_attempts if self.total_attempts > 0 else 0.0),
            "retry_counts_by_operation": self.retry_counts.copy(),
        }


# Global retry statistics
_global_stats = RetryStats()


def get_retry_stats() -> Dict[str, Any]:
    """Get global retry statistics"""
    return _global_stats.get_stats()


def reset_retry_stats():
    """Reset global retry statistics"""
    global _global_stats
    _global_stats = RetryStats()


class RetryHandler:
    """Handles retry logic with different strategies"""

    def __init__(self, config: RetryConfig):
        self.config = config

    def should_retry(self, exception: Exception, attempt: int) -> RetryResult:
        """Determine if an operation should be retried"""

        # Check if we've exceeded max attempts
        if attempt >= self.config.max_attempts:
            return RetryResult.FAIL

        # Check for non-retryable exceptions
        if isinstance(exception, self.config.non_retryable_exceptions):
            return RetryResult.FAIL

        # Check for retryable exceptions
        if isinstance(exception, self.config.retryable_exceptions):
            return RetryResult.RETRY

        # Default: retry for most common transient errors
        retryable_error_messages = [
            "connection refused",
            "timeout",
            "temporary failure",
            "service unavailable",
            "database is locked",
            "no such host",
            "network unreachable",
        ]

        error_message = str(exception).lower()
        if any(msg in error_message for msg in retryable_error_messages):
            return RetryResult.RETRY

        # Don't retry by default for unknown exceptions
        return RetryResult.FAIL

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay before next retry attempt"""

        if self.config.strategy == RetryStrategy.FIXED:
            delay = self.config.base_delay

        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.base_delay * attempt

        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (self.config.backoff_factor ** (attempt - 1))

        elif self.config.strategy == RetryStrategy.RANDOM:
            delay = random.uniform(self.config.base_delay, self.config.max_delay)

        else:
            delay = self.config.base_delay

        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)

        # Add jitter to prevent thundering herd
        if self.config.jitter:
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0.1, delay)  # Ensure minimum delay

        return delay


def retry_sync(config: Optional[RetryConfig] = None, operation_name: Optional[str] = None):
    """Decorator for synchronous function retry logic"""

    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = RetryHandler(config)
            last_exception = None
            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            for attempt in range(1, config.max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    _global_stats.record_attempt(op_name, attempt, True)

                    if config.log_attempts and attempt > 1:
                        logger.info(f"Operation '{op_name}' succeeded on attempt {attempt}")

                    return result

                except Exception as e:
                    last_exception = e

                    if config.log_attempts:
                        logger.log(
                            config.log_level,
                            f"Operation '{op_name}' failed on attempt {attempt}/{config.max_attempts}: {str(e)}",
                        )

                    retry_decision = handler.should_retry(e, attempt)

                    if retry_decision == RetryResult.FAIL:
                        break

                    if attempt < config.max_attempts:
                        delay = handler.calculate_delay(attempt)
                        _global_stats.record_attempt(op_name, attempt, False, delay)

                        if config.log_attempts:
                            logger.info(f"Retrying '{op_name}' in {delay:.2f}s...")

                        time.sleep(delay)
                    else:
                        _global_stats.record_attempt(op_name, attempt, False)

            # All attempts failed
            _global_stats.record_attempt(op_name, config.max_attempts, False)

            if config.log_attempts:
                logger.error(f"Operation '{op_name}' failed after {config.max_attempts} attempts")

            raise last_exception

        return wrapper

    return decorator


def retry_async(config: Optional[RetryConfig] = None, operation_name: Optional[str] = None):
    """Decorator for asynchronous function retry logic"""

    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            handler = RetryHandler(config)
            last_exception = None
            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            for attempt in range(1, config.max_attempts + 1):
                try:
                    result = await func(*args, **kwargs)
                    _global_stats.record_attempt(op_name, attempt, True)

                    if config.log_attempts and attempt > 1:
                        logger.info(f"Operation '{op_name}' succeeded on attempt {attempt}")

                    return result

                except Exception as e:
                    last_exception = e

                    if config.log_attempts:
                        logger.log(
                            config.log_level,
                            f"Operation '{op_name}' failed on attempt {attempt}/{config.max_attempts}: {str(e)}",
                        )

                    retry_decision = handler.should_retry(e, attempt)

                    if retry_decision == RetryResult.FAIL:
                        break

                    if attempt < config.max_attempts:
                        delay = handler.calculate_delay(attempt)
                        _global_stats.record_attempt(op_name, attempt, False, delay)

                        if config.log_attempts:
                            logger.info(f"Retrying '{op_name}' in {delay:.2f}s...")

                        await asyncio.sleep(delay)
                    else:
                        _global_stats.record_attempt(op_name, attempt, False)

            # All attempts failed
            _global_stats.record_attempt(op_name, config.max_attempts, False)

            if config.log_attempts:
                logger.error(f"Operation '{op_name}' failed after {config.max_attempts} attempts")

            raise last_exception

        return wrapper

    return decorator


# Predefined configurations for common scenarios

DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.5,
    max_delay=5.0,
    strategy=RetryStrategy.EXPONENTIAL,
    backoff_factor=2.0,
    retryable_exceptions=(
        ConnectionError,
        TimeoutError,
        OSError,
        # Add database-specific exceptions
        Exception,  # Broad catch for database-specific exceptions
    ),
    non_retryable_exceptions=(
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
    ),
    log_attempts=True,
)

NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=1.0,
    max_delay=30.0,
    strategy=RetryStrategy.EXPONENTIAL,
    backoff_factor=1.5,
    retryable_exceptions=(
        ConnectionError,
        TimeoutError,
        OSError,
    ),
    log_attempts=True,
)

FILE_OPERATION_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.1,
    max_delay=1.0,
    strategy=RetryStrategy.LINEAR,
    retryable_exceptions=(
        OSError,
        PermissionError,
        FileNotFoundError,
    ),
    log_attempts=False,  # File operations are frequent, reduce noise
)


async def retry_async_operation(
    operation: Callable, config: Optional[RetryConfig] = None, operation_name: Optional[str] = None, *args, **kwargs
) -> Any:
    """
    Retry an async operation without using decorators

    Args:
        operation: The async function to retry
        config: Retry configuration
        operation_name: Name for logging and stats
        *args, **kwargs: Arguments to pass to the operation

    Returns:
        Result of the successful operation

    Raises:
        Last exception if all retry attempts fail
    """
    if config is None:
        config = RetryConfig()

    @retry_async(config=config, operation_name=operation_name)
    async def _wrapped():
        return await operation(*args, **kwargs)

    return await _wrapped()


def retry_sync_operation(
    operation: Callable, config: Optional[RetryConfig] = None, operation_name: Optional[str] = None, *args, **kwargs
) -> Any:
    """
    Retry a sync operation without using decorators

    Args:
        operation: The function to retry
        config: Retry configuration
        operation_name: Name for logging and stats
        *args, **kwargs: Arguments to pass to the operation

    Returns:
        Result of the successful operation

    Raises:
        Last exception if all retry attempts fail
    """
    if config is None:
        config = RetryConfig()

    @retry_sync(config=config, operation_name=operation_name)
    def _wrapped():
        return operation(*args, **kwargs)

    return _wrapped()


# Context manager for operations that need cleanup on retry
class RetryContext:
    """Context manager that provides retry functionality with cleanup"""

    def __init__(
        self,
        config: Optional[RetryConfig] = None,
        operation_name: Optional[str] = None,
        cleanup_func: Optional[Callable] = None,
    ):
        self.config = config or RetryConfig()
        self.operation_name = operation_name or "unknown_operation"
        self.cleanup_func = cleanup_func
        self.handler = RetryHandler(self.config)
        self.attempt = 0
        self.last_exception = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return False  # No exception, proceed normally

        self.last_exception = exc_val
        self.attempt += 1

        retry_decision = self.handler.should_retry(exc_val, self.attempt)

        if retry_decision == RetryResult.FAIL or self.attempt >= self.config.max_attempts:
            _global_stats.record_attempt(self.operation_name, self.attempt, False)
            return False  # Let the exception propagate

        # Clean up before retry
        if self.cleanup_func:
            try:
                if asyncio.iscoroutinefunction(self.cleanup_func):
                    await self.cleanup_func()
                else:
                    self.cleanup_func()
            except Exception as cleanup_error:
                logger.warning(f"Cleanup failed during retry: {cleanup_error}")

        # Calculate delay and wait
        delay = self.handler.calculate_delay(self.attempt)
        _global_stats.record_attempt(self.operation_name, self.attempt, False, delay)

        if self.config.log_attempts:
            logger.info(f"Retrying '{self.operation_name}' in {delay:.2f}s (attempt {self.attempt + 1})...")

        await asyncio.sleep(delay)

        return True  # Suppress the exception and retry
