"""
===============================================================================
Waiting The Longest™ - Health Check Module
===============================================================================
Purpose: Comprehensive health checks for all system components.
         Used by load balancers, monitoring, and deployment verification.

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health check status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status for a single component."""
    name: str
    status: HealthStatus
    message: Optional[str] = None
    latency_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealth:
    """Overall system health."""
    status: HealthStatus
    version: str
    uptime_seconds: float
    timestamp: str
    components: List[ComponentHealth] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status.value,
            "version": self.version,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "timestamp": self.timestamp,
            "components": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "latency_ms": c.latency_ms,
                    **c.metadata
                }
                for c in self.components
            ]
        }


class HealthChecker:
    """
    System health checker with pluggable component checks.
    
    Usage:
        checker = HealthChecker(version="1.0.0")
        checker.register("database", check_database)
        checker.register("cache", check_redis)
        
        health = await checker.check_all()
    """
    
    def __init__(self, version: str = "1.0.0"):
        """Initialize health checker."""
        self.version = version
        self.start_time = time.time()
        self._checks: Dict[str, Callable] = {}
        self._critical_components: set = set()
    
    def register(
        self,
        name: str,
        check_fn: Callable,
        critical: bool = False
    ) -> None:
        """
        Register a health check function.
        
        Args:
            name: Component name
            check_fn: Async function returning (bool, message)
            critical: If True, failure marks system as unhealthy
        """
        self._checks[name] = check_fn
        if critical:
            self._critical_components.add(name)
    
    async def check_component(self, name: str) -> ComponentHealth:
        """Run health check for a single component."""
        check_fn = self._checks.get(name)
        if not check_fn:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Unknown component: {name}"
            )
        
        start_time = time.time()
        try:
            if asyncio.iscoroutinefunction(check_fn):
                result = await check_fn()
            else:
                result = check_fn()
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Handle different return types
            if isinstance(result, tuple):
                is_healthy, message = result[0], result[1] if len(result) > 1 else None
                metadata = result[2] if len(result) > 2 else {}
            elif isinstance(result, bool):
                is_healthy = result
                message = None
                metadata = {}
            else:
                is_healthy = bool(result)
                message = str(result) if not is_healthy else None
                metadata = {}
            
            return ComponentHealth(
                name=name,
                status=HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY,
                message=message,
                latency_ms=round(latency_ms, 2),
                metadata=metadata
            )
        
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.exception(f"Health check failed for {name}")
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                latency_ms=round(latency_ms, 2)
            )
    
    async def check_all(self) -> SystemHealth:
        """Run all registered health checks."""
        if not self._checks:
            return SystemHealth(
                status=HealthStatus.HEALTHY,
                version=self.version,
                uptime_seconds=time.time() - self.start_time,
                timestamp=datetime.now(timezone.utc).isoformat(),
                components=[]
            )
        
        # Run all checks concurrently
        tasks = [
            self.check_component(name)
            for name in self._checks
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        components: List[ComponentHealth] = []
        has_critical_failure = False
        has_any_failure = False
        
        for result in results:
            if isinstance(result, Exception):
                # Handle unexpected exceptions
                components.append(ComponentHealth(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=str(result)
                ))
                has_any_failure = True
            else:
                components.append(result)
                if result.status != HealthStatus.HEALTHY:
                    has_any_failure = True
                    if result.name in self._critical_components:
                        has_critical_failure = True
        
        # Determine overall status
        if has_critical_failure:
            overall_status = HealthStatus.UNHEALTHY
        elif has_any_failure:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return SystemHealth(
            status=overall_status,
            version=self.version,
            uptime_seconds=time.time() - self.start_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
            components=components
        )


# Pre-built health check functions

async def check_database(db_session) -> tuple:
    """Check database connectivity."""
    try:
        result = await db_session.execute("SELECT 1")
        return True, "Connected"
    except Exception as e:
        return False, str(e)


def check_database_sync(db_session) -> tuple:
    """Check database connectivity (sync version)."""
    try:
        db_session.execute("SELECT 1")
        return True, "Connected"
    except Exception as e:
        return False, str(e)


async def check_external_api(url: str, timeout: float = 5.0) -> tuple:
    """Check external API availability."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            if response.status_code < 500:
                return True, f"Status {response.status_code}"
            return False, f"Status {response.status_code}"
    except Exception as e:
        return False, str(e)


def check_disk_space(min_gb: float = 1.0) -> tuple:
    """Check available disk space."""
    import shutil
    try:
        total, used, free = shutil.disk_usage("/")
        free_gb = free / (1024 ** 3)
        if free_gb >= min_gb:
            return True, f"{free_gb:.1f}GB free", {"free_gb": round(free_gb, 2)}
        return False, f"Low disk: {free_gb:.1f}GB", {"free_gb": round(free_gb, 2)}
    except Exception as e:
        return False, str(e)


def check_memory_usage(max_percent: float = 90.0) -> tuple:
    """Check memory usage."""
    try:
        import psutil
        memory = psutil.virtual_memory()
        if memory.percent <= max_percent:
            return True, f"{memory.percent}% used", {"percent": memory.percent}
        return False, f"High memory: {memory.percent}%", {"percent": memory.percent}
    except ImportError:
        return True, "psutil not installed"
    except Exception as e:
        return False, str(e)
