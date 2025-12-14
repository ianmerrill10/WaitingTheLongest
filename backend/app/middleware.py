"""
===============================================================================
Waiting The Longest™ - FastAPI Middleware Collection
===============================================================================
Purpose: Custom middleware for security, performance, and observability.
         Includes compression, timing, CORS, and request ID.

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import gzip
import io
import logging
import time
import uuid
from typing import Callable, List, Optional
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

logger = logging.getLogger(__name__)

# Context variable for request ID
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


def get_request_id() -> Optional[str]:
    """Get current request ID from context."""
    return request_id_var.get()


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Add unique request ID to each request for tracing.
    
    Adds X-Request-ID header to responses.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check for existing request ID or generate new one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Set in context for logging
        request_id_var.set(request_id)
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Add request timing information to responses.
    
    Adds X-Response-Time header with request duration.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        
        response = await call_next(request)
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        
        # Log slow requests
        if duration_ms > 1000:  # Over 1 second
            logger.warning(
                f"Slow request: {request.method} {request.url.path} took {duration_ms:.2f}ms"
            )
        
        return response


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Compress responses with gzip when appropriate.
    
    Only compresses responses larger than min_size
    and when client accepts gzip encoding.
    """
    
    def __init__(
        self,
        app,
        min_size: int = 500,
        compression_level: int = 6,
        exclude_paths: Optional[List[str]] = None
    ):
        """
        Initialize compression middleware.
        
        Args:
            app: ASGI app
            min_size: Minimum response size to compress (bytes)
            compression_level: gzip compression level (1-9)
            exclude_paths: Paths to exclude from compression
        """
        super().__init__(app)
        self.min_size = min_size
        self.compression_level = compression_level
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if client accepts gzip
        accept_encoding = request.headers.get("Accept-Encoding", "")
        if "gzip" not in accept_encoding:
            return await call_next(request)
        
        # Check if path is excluded
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)
        
        response = await call_next(request)
        
        # Don't compress if already compressed or streaming
        if "gzip" in response.headers.get("Content-Encoding", ""):
            return response
        
        if isinstance(response, StreamingResponse):
            return response
        
        # Get response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        
        # Check minimum size
        if len(body) < self.min_size:
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
        
        # Compress body
        compressed = gzip.compress(body, compresslevel=self.compression_level)
        
        # Only use compression if it actually reduces size
        if len(compressed) < len(body):
            headers = dict(response.headers)
            headers["Content-Encoding"] = "gzip"
            headers["Content-Length"] = str(len(compressed))
            
            return Response(
                content=compressed,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type
            )
        
        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    
    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: various restrictions
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )
        
        # Cache control for API responses
        if request.url.path.startswith("/api/"):
            response.headers.setdefault(
                "Cache-Control",
                "private, no-cache, no-store, must-revalidate"
            )
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all requests and responses.
    
    Logs method, path, status, and duration.
    """
    
    def __init__(self, app, exclude_paths: Optional[List[str]] = None):
        """
        Initialize logging middleware.
        
        Args:
            app: ASGI app
            exclude_paths: Paths to exclude from logging (e.g., /health)
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/favicon.ico"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip excluded paths
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)
        
        start_time = time.perf_counter()
        request_id = get_request_id() or "unknown"
        
        # Log request
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else "unknown"
            }
        )
        
        try:
            response = await call_next(request)
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(e)
                }
            )
            raise
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        # Log response
        logger.info(
            f"Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 2)
            }
        )
        
        return response


class RateLimitBypassMiddleware(BaseHTTPMiddleware):
    """
    Allow rate limit bypass for internal services.
    
    Checks for internal service token in headers.
    """
    
    def __init__(self, app, internal_token: Optional[str] = None):
        """
        Initialize bypass middleware.
        
        Args:
            app: ASGI app
            internal_token: Token for internal services
        """
        super().__init__(app)
        self.internal_token = internal_token
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check for internal token
        token = request.headers.get("X-Internal-Token")
        if token and self.internal_token and token == self.internal_token:
            request.state.rate_limit_bypass = True
        else:
            request.state.rate_limit_bypass = False
        
        return await call_next(request)
