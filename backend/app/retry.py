"""
===============================================================================
Waiting The Longest™ - Retry Decorator with Exponential Backoff
===============================================================================
Purpose: Retry failed operations with exponential backoff.
         Essential for resilient API calls and database operations.

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import asyncio
import functools
import logging
import random
import time
from typing import (
    Any, Callable, Optional, Sequence, Tuple, Type, TypeVar, Union
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryError(Exception):
    """Exception raised when all retries are exhausted."""
    
    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        super().__init__(message)
        self.last_exception = last_exception


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts (default: 3)
        delay: Initial delay in seconds (default: 1.0)
        backoff: Backoff multiplier (default: 2.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        jitter: Add random jitter to delay (default: True)
        exceptions: Tuple of exceptions to catch
        on_retry: Optional callback called on each retry with (attempt, exception)
    
    Usage:
        @retry(max_attempts=3, exceptions=(httpx.HTTPError,))
        def fetch_data():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"Failed after {max_attempts} attempts: {func.__name__}",
                            extra={"exception": str(e)}
                        )
                        raise RetryError(
                            f"Failed after {max_attempts} attempts",
                            last_exception
                        ) from e
                    
                    # Calculate delay with jitter
                    wait_time = min(current_delay, max_delay)
                    if jitter:
                        wait_time = wait_time * (0.5 + random.random())
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {wait_time:.2f}s..."
                    )
                    
                    if on_retry:
                        on_retry(attempt, e)
                    
                    time.sleep(wait_time)
                    current_delay *= backoff
            
            # Should never reach here, but for type safety
            raise RetryError(f"Failed after {max_attempts} attempts", last_exception)
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"Failed after {max_attempts} attempts: {func.__name__}",
                            extra={"exception": str(e)}
                        )
                        raise RetryError(
                            f"Failed after {max_attempts} attempts",
                            last_exception
                        ) from e
                    
                    wait_time = min(current_delay, max_delay)
                    if jitter:
                        wait_time = wait_time * (0.5 + random.random())
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {wait_time:.2f}s..."
                    )
                    
                    if on_retry:
                        on_retry(attempt, e)
                    
                    await asyncio.sleep(wait_time)
                    current_delay *= backoff
            
            raise RetryError(f"Failed after {max_attempts} attempts", last_exception)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper
    
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service recovered
    
    Usage:
        breaker = CircuitBreaker(failure_threshold=5, reset_timeout=60)
        
        @breaker
        async def call_external_service():
            ...
    """
    
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            reset_timeout: Seconds before trying to close circuit
            exceptions: Exceptions that count as failures
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.exceptions = exceptions
        
        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
    
    @property
    def state(self) -> str:
        """Get current circuit state."""
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time >= self.reset_timeout:
                self._state = self.HALF_OPEN
        return self._state
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorate a function with circuit breaker."""
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            if self.state == self.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is open for {func.__name__}"
                )
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.exceptions as e:
                self._on_failure()
                raise
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            if self.state == self.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is open for {func.__name__}"
                )
            
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.exceptions as e:
                self._on_failure()
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper
    
    def _on_success(self) -> None:
        """Handle successful call."""
        self._failure_count = 0
        self._state = self.CLOSED
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._failure_count >= self.failure_threshold:
            self._state = self.OPEN
            logger.warning(
                f"Circuit breaker opened after {self._failure_count} failures"
            )
    
    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self._state = self.CLOSED
        self._failure_count = 0


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


# Convenience functions for common patterns
def retry_on_network_error(max_attempts: int = 3):
    """Retry decorator for network errors."""
    import httpx
    return retry(
        max_attempts=max_attempts,
        exceptions=(
            httpx.HTTPError,
            httpx.TimeoutException,
            httpx.ConnectError,
            ConnectionError,
            TimeoutError,
        )
    )


def retry_on_db_error(max_attempts: int = 3):
    """Retry decorator for database errors."""
    try:
        from sqlalchemy.exc import OperationalError, InterfaceError
        return retry(
            max_attempts=max_attempts,
            delay=0.5,
            exceptions=(OperationalError, InterfaceError)
        )
    except ImportError:
        return retry(max_attempts=max_attempts, delay=0.5)
