"""
===============================================================================
Waiting The Longest™ - Health Check Tests
===============================================================================
Purpose: Test health check module
===============================================================================
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from backend.app.health import (
    HealthChecker, HealthStatus, ComponentHealth, SystemHealth,
    check_disk_space, check_memory_usage
)


class TestHealthChecker:
    """Tests for HealthChecker class."""
    
    @pytest.mark.asyncio
    async def test_empty_checker_returns_healthy(self):
        """Test checker with no registered checks."""
        checker = HealthChecker(version="1.0.0")
        
        health = await checker.check_all()
        
        assert health.status == HealthStatus.HEALTHY
        assert health.version == "1.0.0"
        assert len(health.components) == 0
    
    @pytest.mark.asyncio
    async def test_single_healthy_component(self):
        """Test with single healthy component."""
        checker = HealthChecker()
        checker.register("test", lambda: (True, "OK"))
        
        health = await checker.check_all()
        
        assert health.status == HealthStatus.HEALTHY
        assert len(health.components) == 1
        assert health.components[0].name == "test"
        assert health.components[0].status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_single_unhealthy_component(self):
        """Test with single unhealthy non-critical component."""
        checker = HealthChecker()
        checker.register("test", lambda: (False, "Error"))
        
        health = await checker.check_all()
        
        assert health.status == HealthStatus.DEGRADED  # Not UNHEALTHY since not critical
        assert health.components[0].status == HealthStatus.UNHEALTHY
        assert health.components[0].message == "Error"
    
    @pytest.mark.asyncio
    async def test_critical_component_failure(self):
        """Test that critical component failure marks system unhealthy."""
        checker = HealthChecker()
        checker.register("database", lambda: (False, "DB Error"), critical=True)
        checker.register("cache", lambda: (True, "OK"))
        
        health = await checker.check_all()
        
        assert health.status == HealthStatus.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_async_check_function(self):
        """Test with async check function."""
        checker = HealthChecker()
        
        async def async_check():
            await asyncio.sleep(0.001)
            return True, "Async OK"
        
        checker.register("async_test", async_check)
        
        health = await checker.check_all()
        
        assert health.status == HealthStatus.HEALTHY
        assert health.components[0].status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_check_exception_handling(self):
        """Test that exceptions in checks are handled."""
        checker = HealthChecker()
        
        def bad_check():
            raise RuntimeError("Check failed")
        
        checker.register("bad", bad_check)
        
        health = await checker.check_all()
        
        assert health.status == HealthStatus.DEGRADED
        assert health.components[0].status == HealthStatus.UNHEALTHY
        assert "Check failed" in health.components[0].message
    
    @pytest.mark.asyncio
    async def test_latency_tracking(self):
        """Test that check latency is tracked."""
        checker = HealthChecker()
        
        async def slow_check():
            await asyncio.sleep(0.01)
            return True, "Slow OK"
        
        checker.register("slow", slow_check)
        
        health = await checker.check_all()
        
        assert health.components[0].latency_ms is not None
        assert health.components[0].latency_ms >= 10  # At least 10ms
    
    @pytest.mark.asyncio
    async def test_uptime_tracking(self):
        """Test that uptime is tracked."""
        checker = HealthChecker()
        await asyncio.sleep(0.01)
        
        health = await checker.check_all()
        
        assert health.uptime_seconds > 0
    
    @pytest.mark.asyncio
    async def test_to_dict_serialization(self):
        """Test SystemHealth.to_dict() serialization."""
        checker = HealthChecker(version="2.0.0")
        checker.register("test", lambda: (True, "OK", {"extra": "data"}))
        
        health = await checker.check_all()
        data = health.to_dict()
        
        assert data["status"] == "healthy"
        assert data["version"] == "2.0.0"
        assert isinstance(data["uptime_seconds"], float)
        assert isinstance(data["components"], list)
        assert data["components"][0]["extra"] == "data"
    
    @pytest.mark.asyncio
    async def test_mixed_health_status(self):
        """Test with mixed healthy/unhealthy non-critical components."""
        checker = HealthChecker()
        checker.register("healthy1", lambda: True)
        checker.register("healthy2", lambda: (True, "OK"))
        checker.register("unhealthy", lambda: False)
        
        health = await checker.check_all()
        
        assert health.status == HealthStatus.DEGRADED
        
        healthy_count = sum(
            1 for c in health.components 
            if c.status == HealthStatus.HEALTHY
        )
        assert healthy_count == 2


class TestBuiltInChecks:
    """Tests for built-in health check functions."""
    
    def test_check_disk_space_success(self):
        """Test disk space check when enough space."""
        # Should pass on most systems
        is_healthy, message, metadata = check_disk_space(min_gb=0.001)
        
        assert is_healthy is True
        assert "free" in message.lower()
        assert "free_gb" in metadata
    
    def test_check_disk_space_failure(self):
        """Test disk space check with impossible requirement."""
        is_healthy, message, metadata = check_disk_space(min_gb=1000000)  # 1 petabyte
        
        assert is_healthy is False
        assert "low disk" in message.lower()
    
    @patch('backend.app.health.psutil')
    def test_check_memory_usage_success(self, mock_psutil):
        """Test memory check when usage is low."""
        mock_memory = Mock()
        mock_memory.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_memory
        
        is_healthy, message, metadata = check_memory_usage(max_percent=90.0)
        
        assert is_healthy is True
        assert "50" in message
        assert metadata["percent"] == 50.0
    
    @patch('backend.app.health.psutil')
    def test_check_memory_usage_failure(self, mock_psutil):
        """Test memory check when usage is high."""
        mock_memory = Mock()
        mock_memory.percent = 95.0
        mock_psutil.virtual_memory.return_value = mock_memory
        
        is_healthy, message, metadata = check_memory_usage(max_percent=90.0)
        
        assert is_healthy is False
        assert "high memory" in message.lower()
