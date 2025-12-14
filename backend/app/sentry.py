"""
===============================================================================
Waiting The Longest™ - Sentry Error Tracking Integration
===============================================================================
Purpose: Error tracking and performance monitoring with Sentry.
         Captures exceptions, performance data, and user context.

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import logging
import os
from typing import Any, Callable, Dict, Optional
from functools import wraps

logger = logging.getLogger(__name__)

# Try to import sentry_sdk
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    sentry_sdk = None


def init_sentry(
    dsn: Optional[str] = None,
    environment: str = "development",
    release: Optional[str] = None,
    sample_rate: float = 1.0,
    traces_sample_rate: float = 0.1,
    profiles_sample_rate: float = 0.1,
    enable_performance: bool = True,
    debug: bool = False
) -> bool:
    """
    Initialize Sentry SDK.
    
    Args:
        dsn: Sentry DSN (defaults to SENTRY_DSN env var)
        environment: Environment name (production, staging, development)
        release: Release/version identifier
        sample_rate: Error event sample rate (0.0 to 1.0)
        traces_sample_rate: Performance traces sample rate
        profiles_sample_rate: Profiling sample rate
        enable_performance: Enable performance monitoring
        debug: Enable Sentry debug mode
        
    Returns:
        True if initialization successful
    """
    if not SENTRY_AVAILABLE:
        logger.warning("Sentry SDK not installed. Error tracking disabled.")
        return False
    
    dsn = dsn or os.environ.get("SENTRY_DSN")
    if not dsn:
        logger.info("No Sentry DSN provided. Error tracking disabled.")
        return False
    
    release = release or os.environ.get("GIT_SHA", "unknown")
    
    integrations = [
        FastApiIntegration(transaction_style="url"),
        SqlalchemyIntegration(),
        LoggingIntegration(
            level=logging.WARNING,
            event_level=logging.ERROR
        ),
    ]
    
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        integrations=integrations,
        sample_rate=sample_rate,
        traces_sample_rate=traces_sample_rate if enable_performance else 0.0,
        profiles_sample_rate=profiles_sample_rate if enable_performance else 0.0,
        debug=debug,
        send_default_pii=False,  # Don't send PII by default
        before_send=before_send,
        before_send_transaction=before_send_transaction,
    )
    
    logger.info(f"Sentry initialized for environment: {environment}")
    return True


def before_send(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Process event before sending to Sentry.
    
    Used to filter/modify events.
    """
    # Filter out certain exceptions
    if "exc_info" in hint:
        exc_type, exc_value, _ = hint["exc_info"]
        
        # Don't send 404 errors
        if exc_type.__name__ == "HTTPException":
            if hasattr(exc_value, "status_code") and exc_value.status_code == 404:
                return None
        
        # Don't send rate limit errors
        if exc_type.__name__ == "RateLimitExceeded":
            return None
    
    # Remove sensitive data
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        sensitive_headers = ["authorization", "cookie", "x-api-key"]
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "[Filtered]"
    
    return event


def before_send_transaction(
    event: Dict[str, Any],
    hint: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Process transaction before sending to Sentry.
    
    Used to filter performance data.
    """
    # Filter out health check transactions
    if event.get("transaction") in ["/health", "/api/health"]:
        return None
    
    return event


def capture_exception(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None,
    user: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Capture an exception to Sentry.
    
    Args:
        exception: Exception to capture
        context: Additional context data
        tags: Additional tags
        user: User information
        
    Returns:
        Sentry event ID or None
    """
    if not SENTRY_AVAILABLE or sentry_sdk is None:
        logger.exception("Exception (Sentry disabled)", exc_info=exception)
        return None
    
    with sentry_sdk.push_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_context(key, value)
        
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)
        
        if user:
            scope.set_user(user)
        
        return sentry_sdk.capture_exception(exception)


def capture_message(
    message: str,
    level: str = "info",
    context: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Capture a message to Sentry.
    
    Args:
        message: Message to capture
        level: Log level (debug, info, warning, error, fatal)
        context: Additional context data
        tags: Additional tags
        
    Returns:
        Sentry event ID or None
    """
    if not SENTRY_AVAILABLE or sentry_sdk is None:
        logger.log(logging.getLevelName(level.upper()), message)
        return None
    
    with sentry_sdk.push_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_context(key, value)
        
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)
        
        return sentry_sdk.capture_message(message, level=level)


def set_user(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    username: Optional[str] = None,
    ip_address: Optional[str] = None
) -> None:
    """Set user context for Sentry events."""
    if not SENTRY_AVAILABLE or sentry_sdk is None:
        return
    
    user_data = {}
    if user_id:
        user_data["id"] = user_id
    if email:
        user_data["email"] = email
    if username:
        user_data["username"] = username
    if ip_address:
        user_data["ip_address"] = ip_address
    
    if user_data:
        sentry_sdk.set_user(user_data)


def set_tag(key: str, value: str) -> None:
    """Set a tag for Sentry events."""
    if not SENTRY_AVAILABLE or sentry_sdk is None:
        return
    sentry_sdk.set_tag(key, value)


def set_context(name: str, data: Dict[str, Any]) -> None:
    """Set additional context for Sentry events."""
    if not SENTRY_AVAILABLE or sentry_sdk is None:
        return
    sentry_sdk.set_context(name, data)


def start_span(
    op: str,
    description: Optional[str] = None
) -> Any:
    """
    Start a performance span.
    
    Usage:
        with start_span("db.query", "Fetch animals") as span:
            # ... do work
            span.set_data("row_count", len(results))
    """
    if not SENTRY_AVAILABLE or sentry_sdk is None:
        return DummySpan()
    
    return sentry_sdk.start_span(op=op, description=description)


class DummySpan:
    """Dummy span when Sentry is not available."""
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def set_data(self, key: str, value: Any) -> None:
        pass
    
    def set_tag(self, key: str, value: str) -> None:
        pass
    
    def set_status(self, status: str) -> None:
        pass


def traced(
    op: Optional[str] = None,
    description: Optional[str] = None
) -> Callable:
    """
    Decorator to trace function execution.
    
    Args:
        op: Operation type (e.g., "http", "db", "task")
        description: Operation description
    
    Usage:
        @traced(op="db.query", description="Fetch animals")
        def get_animals():
            ...
    """
    def decorator(func: Callable) -> Callable:
        _op = op or f"function.{func.__name__}"
        _description = description or func.__name__
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with start_span(_op, _description):
                return func(*args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with start_span(_op, _description):
                return await func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
