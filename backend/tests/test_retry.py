"""
===============================================================================
Waiting The Longest™ - Retry Utility Tests
===============================================================================
Purpose: Test retry decorator and circuit breaker
===============================================================================
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from backend.app.retry import (
    retry, RetryError, CircuitBreaker, CircuitBreakerOpenError
)


class TestRetryDecorator:
    """Tests for the retry decorator."""
    
    def test_retry_success_first_attempt(self):
        """Test function that succeeds on first attempt."""
        mock_fn = Mock(return_value="success")
        
        @retry(max_attempts=3)
        def success_fn():
            return mock_fn()
        
        result = success_fn()
        
        assert result == "success"
        assert mock_fn.call_count == 1
    
    def test_retry_success_after_failures(self):
        """Test function that succeeds after retries."""
        mock_fn = Mock(side_effect=[ValueError("fail"), ValueError("fail"), "success"])
        
        @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def retry_fn():
            return mock_fn()
        
        result = retry_fn()
        
        assert result == "success"
        assert mock_fn.call_count == 3
    
    def test_retry_max_attempts_exceeded(self):
        """Test function that exceeds max attempts."""
        mock_fn = Mock(side_effect=ValueError("always fail"))
        
        @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def fail_fn():
            return mock_fn()
        
        with pytest.raises(RetryError) as exc_info:
            fail_fn()
        
        assert mock_fn.call_count == 3
        assert "Failed after 3 attempts" in str(exc_info.value)
    
    def test_retry_only_catches_specified_exceptions(self):
        """Test that only specified exceptions trigger retry."""
        mock_fn = Mock(side_effect=TypeError("wrong type"))
        
        @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def fn():
            return mock_fn()
        
        with pytest.raises(TypeError):
            fn()
        
        # Should not retry for TypeError
        assert mock_fn.call_count == 1
    
    def test_retry_on_callback(self):
        """Test that on_retry callback is called."""
        callback = Mock()
        mock_fn = Mock(side_effect=[ValueError("fail"), "success"])
        
        @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,), on_retry=callback)
        def fn():
            return mock_fn()
        
        fn()
        
        assert callback.call_count == 1
        callback.assert_called_with(1, mock_fn.side_effect[0])
    
    @pytest.mark.asyncio
    async def test_retry_async_function(self):
        """Test retry with async function."""
        mock_fn = AsyncMock(side_effect=[ValueError("fail"), "success"])
        
        @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        async def async_fn():
            return await mock_fn()
        
        result = await async_fn()
        
        assert result == "success"
        assert mock_fn.call_count == 2


class TestCircuitBreaker:
    """Tests for the CircuitBreaker class."""
    
    def test_circuit_breaker_closed_on_success(self):
        """Test circuit stays closed on success."""
        breaker = CircuitBreaker(failure_threshold=3)
        mock_fn = Mock(return_value="success")
        
        @breaker
        def fn():
            return mock_fn()
        
        for _ in range(10):
            result = fn()
            assert result == "success"
        
        assert breaker.state == CircuitBreaker.CLOSED
    
    def test_circuit_breaker_opens_on_failures(self):
        """Test circuit opens after threshold failures."""
        breaker = CircuitBreaker(failure_threshold=3, exceptions=(ValueError,))
        mock_fn = Mock(side_effect=ValueError("fail"))
        
        @breaker
        def fn():
            return mock_fn()
        
        # Trigger failures up to threshold
        for _ in range(3):
            with pytest.raises(ValueError):
                fn()
        
        # Circuit should now be open
        assert breaker.state == CircuitBreaker.OPEN
        
        # Next call should fail immediately
        with pytest.raises(CircuitBreakerOpenError):
            fn()
        
        # Original function shouldn't be called
        assert mock_fn.call_count == 3
    
    def test_circuit_breaker_half_open_after_timeout(self):
        """Test circuit transitions to half-open after timeout."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            reset_timeout=0.01,
            exceptions=(ValueError,)
        )
        mock_fn = Mock(side_effect=ValueError("fail"))
        
        @breaker
        def fn():
            return mock_fn()
        
        # Trigger failures to open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                fn()
        
        assert breaker.state == CircuitBreaker.OPEN
        
        # Wait for timeout
        import time
        time.sleep(0.02)
        
        # Circuit should be half-open now
        assert breaker.state == CircuitBreaker.HALF_OPEN
    
    def test_circuit_breaker_closes_on_success_after_half_open(self):
        """Test circuit closes on success when half-open."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            reset_timeout=0.01,
            exceptions=(ValueError,)
        )
        
        call_count = [0]
        def varying_fn():
            call_count[0] += 1
            if call_count[0] <= 2:
                raise ValueError("fail")
            return "success"
        
        @breaker
        def fn():
            return varying_fn()
        
        # Trigger failures
        for _ in range(2):
            with pytest.raises(ValueError):
                fn()
        
        # Wait for timeout
        import time
        time.sleep(0.02)
        
        # Next call should succeed and close circuit
        result = fn()
        assert result == "success"
        assert breaker.state == CircuitBreaker.CLOSED
    
    def test_circuit_breaker_reset(self):
        """Test manual circuit reset."""
        breaker = CircuitBreaker(failure_threshold=2, exceptions=(ValueError,))
        mock_fn = Mock(side_effect=ValueError("fail"))
        
        @breaker
        def fn():
            return mock_fn()
        
        # Open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                fn()
        
        assert breaker.state == CircuitBreaker.OPEN
        
        # Manual reset
        breaker.reset()
        assert breaker.state == CircuitBreaker.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_async(self):
        """Test circuit breaker with async function."""
        breaker = CircuitBreaker(failure_threshold=2, exceptions=(ValueError,))
        mock_fn = AsyncMock(side_effect=ValueError("fail"))
        
        @breaker
        async def async_fn():
            return await mock_fn()
        
        for _ in range(2):
            with pytest.raises(ValueError):
                await async_fn()
        
        with pytest.raises(CircuitBreakerOpenError):
            await async_fn()
