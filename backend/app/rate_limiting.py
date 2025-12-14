"""
Waiting The Longest™ - API Rate Limiting
=========================================
Enhanced rate limiting configuration.
"""

import time
from typing import Optional, Dict, Callable
from dataclasses import dataclass
from functools import wraps

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit."""
    requests: int
    window_seconds: int
    key_func: Optional[Callable[[Request], str]] = None
    
    @property
    def limit_string(self) -> str:
        """Get rate limit as string (e.g., '100/minute')."""
        if self.window_seconds == 60:
            return f"{self.requests}/minute"
        elif self.window_seconds == 3600:
            return f"{self.requests}/hour"
        elif self.window_seconds == 86400:
            return f"{self.requests}/day"
        else:
            return f"{self.requests}/{self.window_seconds}s"


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter.
    
    For production, consider Redis-based rate limiting for
    distributed systems.
    """
    
    def __init__(self):
        self.requests: Dict[str, list] = {}
        self.cleanup_interval = 60  # seconds
        self.last_cleanup = time.time()
    
    def _cleanup(self) -> None:
        """Remove expired entries."""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        # Remove old entries
        expired_keys = []
        for key, timestamps in self.requests.items():
            # Keep only timestamps from last hour
            self.requests[key] = [t for t in timestamps if now - t < 3600]
            if not self.requests[key]:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.requests[key]
        
        self.last_cleanup = now
    
    def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int, int]:
        """
        Check if request is allowed.
        
        Returns:
            (allowed, remaining, reset_after)
        """
        self._cleanup()
        
        now = time.time()
        window_start = now - window_seconds
        
        # Get timestamps for this key
        if key not in self.requests:
            self.requests[key] = []
        
        # Filter to current window
        self.requests[key] = [t for t in self.requests[key] if t > window_start]
        
        current_count = len(self.requests[key])
        remaining = max(0, max_requests - current_count - 1)
        
        if current_count >= max_requests:
            # Find when oldest request in window expires
            oldest = min(self.requests[key])
            reset_after = int(oldest + window_seconds - now)
            return False, 0, reset_after
        
        # Add current request
        self.requests[key].append(now)
        
        # Calculate reset time
        reset_after = window_seconds
        
        return True, remaining, reset_after


# Global rate limiter instance
_rate_limiter = InMemoryRateLimiter()


# =============================================================================
# Rate Limit Configurations
# =============================================================================

RATE_LIMITS = {
    "default": RateLimitConfig(
        requests=100,
        window_seconds=60,
    ),
    "strict": RateLimitConfig(
        requests=10,
        window_seconds=60,
    ),
    "api": RateLimitConfig(
        requests=60,
        window_seconds=60,
    ),
    "auth": RateLimitConfig(
        requests=5,
        window_seconds=60,
    ),
    "newsletter": RateLimitConfig(
        requests=3,
        window_seconds=60,
    ),
    "search": RateLimitConfig(
        requests=30,
        window_seconds=60,
    ),
}


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    # Check for forwarded headers (common in proxies/load balancers)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First IP in the chain is the client
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct connection
    if request.client:
        return request.client.host
    
    return "unknown"


def rate_limit(
    config_name: str = "default",
    key_func: Optional[Callable[[Request], str]] = None,
):
    """
    Decorator for rate limiting endpoints.
    
    Usage:
        @app.get("/items")
        @rate_limit("api")
        async def get_items(request: Request):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            config = RATE_LIMITS.get(config_name, RATE_LIMITS["default"])
            
            # Generate rate limit key
            if key_func:
                limit_key = key_func(request)
            elif config.key_func:
                limit_key = config.key_func(request)
            else:
                limit_key = f"{get_client_ip(request)}:{request.url.path}"
            
            # Check rate limit
            allowed, remaining, reset_after = _rate_limiter.is_allowed(
                limit_key,
                config.requests,
                config.window_seconds,
            )
            
            if not allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Too many requests",
                        "retry_after": reset_after,
                    },
                    headers={
                        "Retry-After": str(reset_after),
                        "X-RateLimit-Limit": str(config.requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_after),
                    },
                )
            
            # Execute the function
            response = await func(request, *args, **kwargs)
            
            # Add rate limit headers to response
            if hasattr(response, "headers"):
                response.headers["X-RateLimit-Limit"] = str(config.requests)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
            
            return response
        
        return wrapper
    return decorator


class RateLimitMiddleware:
    """
    Middleware for global rate limiting.
    
    Applies default rate limits to all requests.
    """
    
    def __init__(
        self,
        app,
        default_config: str = "default",
        exclude_paths: Optional[list] = None,
    ):
        self.app = app
        self.config = RATE_LIMITS.get(default_config, RATE_LIMITS["default"])
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/openapi.json"]
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        path = scope.get("path", "")
        
        # Skip excluded paths
        if any(path.startswith(p) for p in self.exclude_paths):
            await self.app(scope, receive, send)
            return
        
        # Get client IP from headers
        headers = dict(scope.get("headers", []))
        forwarded = headers.get(b"x-forwarded-for", b"").decode()
        client_ip = forwarded.split(",")[0].strip() if forwarded else "unknown"
        
        limit_key = f"{client_ip}:{path}"
        
        allowed, remaining, reset_after = _rate_limiter.is_allowed(
            limit_key,
            self.config.requests,
            self.config.window_seconds,
        )
        
        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": reset_after,
                },
                headers={
                    "Retry-After": str(reset_after),
                },
            )
            await response(scope, receive, send)
            return
        
        await self.app(scope, receive, send)
