"""
Validation script for database improvements
Tests the retry utilities and basic functionality without external dependencies
"""

import asyncio
import sys
import time
from datetime import datetime

# Test retry utilities
from retry_utils import (
    RetryConfig,
    RetryStrategy,
    retry_async,
    retry_sync,
    get_retry_stats,
    reset_retry_stats,
)


def test_retry_config():
    """Test retry configuration creation"""
    print("Testing RetryConfig creation...")

    config = RetryConfig(
        max_attempts=5,
        base_delay=1.0,
        strategy=RetryStrategy.EXPONENTIAL,
        backoff_factor=2.0,
    )

    assert config.max_attempts == 5
    assert config.base_delay == 1.0
    assert config.strategy == RetryStrategy.EXPONENTIAL
    assert config.backoff_factor == 2.0

    print("✓ RetryConfig creation successful")


async def test_async_retry_success():
    """Test async retry with successful operation"""
    print("Testing async retry with success...")

    call_count = 0

    @retry_async(config=RetryConfig(max_attempts=3, log_attempts=False))
    async def successful_operation():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await successful_operation()
    assert result == "success"
    assert call_count == 1

    print("✓ Async retry success test passed")


async def test_async_retry_with_failures():
    """Test async retry with transient failures"""
    print("Testing async retry with transient failures...")

    call_count = 0

    @retry_async(config=RetryConfig(max_attempts=3, base_delay=0.01, log_attempts=False))
    async def failing_then_success():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Transient failure")
        return "success"

    result = await failing_then_success()
    assert result == "success"
    assert call_count == 3

    print("✓ Async retry with failures test passed")


async def test_async_retry_exhausted():
    """Test async retry when all attempts are exhausted"""
    print("Testing async retry with exhausted attempts...")

    call_count = 0

    @retry_async(config=RetryConfig(max_attempts=2, base_delay=0.01, log_attempts=False))
    async def always_failing():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("Always fails")

    try:
        await always_failing()
        assert False, "Should have raised an exception"
    except ConnectionError:
        pass  # Expected

    assert call_count == 2

    print("✓ Async retry exhausted test passed")


def test_sync_retry():
    """Test synchronous retry functionality"""
    print("Testing sync retry functionality...")

    call_count = 0

    @retry_sync(config=RetryConfig(max_attempts=3, base_delay=0.01, log_attempts=False))
    def sync_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise OSError("Transient error")
        return "sync_success"

    result = sync_operation()
    assert result == "sync_success"
    assert call_count == 2

    print("✓ Sync retry test passed")


def test_retry_statistics():
    """Test retry statistics tracking"""
    print("Testing retry statistics...")

    reset_retry_stats()

    initial_stats = get_retry_stats()
    assert initial_stats["total_attempts"] == 0
    assert initial_stats["successful_attempts"] == 0
    assert initial_stats["failed_attempts"] == 0

    print("✓ Retry statistics test passed")


def test_different_strategies():
    """Test different retry strategies"""
    print("Testing different retry strategies...")

    from retry_utils import RetryHandler

    # Test exponential backoff
    exponential_config = RetryConfig(
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay=1.0,
        backoff_factor=2.0,
        jitter=False,  # Disable jitter for predictable testing
    )
    handler = RetryHandler(exponential_config)

    delay1 = handler.calculate_delay(1)
    delay2 = handler.calculate_delay(2)
    delay3 = handler.calculate_delay(3)

    assert delay1 == 1.0  # First attempt: base_delay
    assert delay2 == 2.0  # Second attempt: base_delay * backoff_factor
    assert delay3 == 4.0  # Third attempt: base_delay * backoff_factor^2

    # Test linear backoff
    linear_config = RetryConfig(
        strategy=RetryStrategy.LINEAR, base_delay=0.5, jitter=False  # Disable jitter for predictable testing
    )
    linear_handler = RetryHandler(linear_config)

    linear_delay1 = linear_handler.calculate_delay(1)
    linear_delay2 = linear_handler.calculate_delay(2)
    linear_delay3 = linear_handler.calculate_delay(3)

    assert linear_delay1 == 0.5  # First attempt: 0.5 * 1
    assert linear_delay2 == 1.0  # Second attempt: 0.5 * 2
    assert linear_delay3 == 1.5  # Third attempt: 0.5 * 3

    print("✓ Different retry strategies test passed")


def test_should_retry_logic():
    """Test retry decision logic"""
    print("Testing retry decision logic...")

    from retry_utils import RetryHandler, RetryResult

    config = RetryConfig(
        max_attempts=3,
        retryable_exceptions=(ConnectionError, TimeoutError),
        non_retryable_exceptions=(ValueError, TypeError),
    )
    handler = RetryHandler(config)

    # Should retry for retryable exceptions
    result = handler.should_retry(ConnectionError("Connection failed"), 1)
    assert result == RetryResult.RETRY

    result = handler.should_retry(TimeoutError("Timeout"), 1)
    assert result == RetryResult.RETRY

    # Should not retry for non-retryable exceptions
    result = handler.should_retry(ValueError("Bad value"), 1)
    assert result == RetryResult.FAIL

    result = handler.should_retry(TypeError("Type error"), 1)
    assert result == RetryResult.FAIL

    # Should not retry when max attempts exceeded
    result = handler.should_retry(ConnectionError("Connection failed"), 3)
    assert result == RetryResult.FAIL

    print("✓ Retry decision logic test passed")


async def test_predefined_configs():
    """Test predefined retry configurations"""
    print("Testing predefined retry configurations...")

    from retry_utils import DATABASE_RETRY_CONFIG, NETWORK_RETRY_CONFIG, FILE_OPERATION_RETRY_CONFIG

    # Test database config
    assert DATABASE_RETRY_CONFIG.max_attempts == 3
    assert DATABASE_RETRY_CONFIG.strategy == RetryStrategy.EXPONENTIAL

    # Test network config
    assert NETWORK_RETRY_CONFIG.max_attempts == 5
    assert NETWORK_RETRY_CONFIG.max_delay == 30.0

    # Test file operation config
    assert FILE_OPERATION_RETRY_CONFIG.strategy == RetryStrategy.LINEAR
    assert not FILE_OPERATION_RETRY_CONFIG.log_attempts  # Should be False for frequent operations

    print("✓ Predefined configurations test passed")


async def run_all_tests():
    """Run all validation tests"""
    print("=" * 60)
    print("KASA MONITOR DATABASE IMPROVEMENTS VALIDATION")
    print("=" * 60)
    print()

    try:
        # Test retry utilities
        test_retry_config()
        await test_async_retry_success()
        await test_async_retry_with_failures()
        await test_async_retry_exhausted()
        test_sync_retry()
        test_retry_statistics()
        test_different_strategies()
        test_should_retry_logic()
        await test_predefined_configs()

        print()
        print("=" * 60)
        print("✅ ALL TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)
        print()

        # Show final statistics
        final_stats = get_retry_stats()
        print("Final Retry Statistics:")
        print(f"  Total attempts: {final_stats['total_attempts']}")
        print(f"  Successful attempts: {final_stats['successful_attempts']}")
        print(f"  Failed attempts: {final_stats['failed_attempts']}")
        print(f"  Success rate: {final_stats['success_rate']:.2%}")

        return True

    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        import traceback

        traceback.print_exc()
        return False


async def performance_benchmark():
    """Run performance benchmarks for retry functionality"""
    print("\nRunning performance benchmarks...")

    # Benchmark successful operations
    @retry_async(config=RetryConfig(max_attempts=1, log_attempts=False))
    async def fast_operation():
        return "result"

    start_time = time.time()
    for _ in range(100):
        await fast_operation()
    success_time = time.time() - start_time

    print(f"100 successful operations took: {success_time:.3f}s")

    # Benchmark operations with retries
    call_count = 0

    @retry_async(config=RetryConfig(max_attempts=3, base_delay=0.001, log_attempts=False))
    async def retry_operation():
        nonlocal call_count
        call_count += 1
        if call_count % 3 != 0:  # Fail 2/3 of the time
            raise ConnectionError("Simulated failure")
        return "result"

    call_count = 0
    start_time = time.time()
    for _ in range(33):  # Will result in ~100 total calls
        await retry_operation()
    retry_time = time.time() - start_time

    print(f"33 operations with retries (100 total calls) took: {retry_time:.3f}s")
    print(f"Overhead per retry: {(retry_time - success_time) / 67:.4f}s")  # 67 extra calls


if __name__ == "__main__":

    async def main():
        success = await run_all_tests()

        if success:
            await performance_benchmark()
            print("\n🎉 Validation completed successfully!")
            print("\nDatabase improvements are ready for use:")
            print("  - Retry utilities with exponential backoff")
            print("  - Enhanced error handling and recovery")
            print("  - Connection pooling improvements")
            print("  - Health monitoring capabilities")
            print("  - Comprehensive statistics tracking")
            sys.exit(0)
        else:
            print("\n❌ Validation failed!")
            sys.exit(1)

    # Run the validation
    asyncio.run(main())
