"""
===============================================================================
Waiting The Longest™ - Structured Logging Configuration
===============================================================================
Purpose: Configure structured logging with structlog for better observability.
         Provides consistent JSON logging in production and human-readable
         output in development.

Usage:
    from app.logging_config import get_logger, setup_logging
    
    # Call once at startup
    setup_logging()
    
    # Get a logger for your module
    logger = get_logger(__name__)
    logger.info("request_processed", user_id=123, duration_ms=45)

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from .config import settings


def setup_logging(json_logs: bool = None, log_level: str = None) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        json_logs: If True, output JSON. If False, output colored console.
                   If None, auto-detect based on DEBUG setting.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR). 
                   Defaults to DEBUG if DEBUG=True, else INFO.
    """
    # Determine output format
    if json_logs is None:
        json_logs = not getattr(settings, 'DEBUG', False)
    
    # Determine log level
    if log_level is None:
        log_level = "DEBUG" if getattr(settings, 'DEBUG', False) else "INFO"
    
    # Shared processors for all log entries
    shared_processors: list[Processor] = [
        # Add log level
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Add call site info in debug mode
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.MODULE,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ) if log_level == "DEBUG" else structlog.processors.StackInfoRenderer(),
        # Format exception info
        structlog.processors.format_exc_info,
        # Handle unicode properly
        structlog.processors.UnicodeDecoder(),
    ]
    
    if json_logs:
        # Production: JSON output
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: Colored console output
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    
    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            # Prepare for final rendering
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging to work with structlog
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    
    # Set up root handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger for the given module name.
    
    Args:
        name: Logger name, typically __name__ of the calling module.
        
    Returns:
        A bound logger with structured logging capabilities.
        
    Example:
        logger = get_logger(__name__)
        logger.info("user_login", user_id=123, ip="1.2.3.4")
        logger.error("database_error", error=str(e), query="SELECT...")
    """
    return structlog.get_logger(name)


def log_request_context(request_id: str = None, **kwargs: Any) -> dict:
    """
    Create a context dict for request logging.
    
    Args:
        request_id: Unique request identifier
        **kwargs: Additional context fields
        
    Returns:
        Context dictionary for structured logging
    """
    context = {"request_id": request_id} if request_id else {}
    context.update(kwargs)
    return context


# Convenience function for logging API requests
def log_api_request(
    logger: structlog.stdlib.BoundLogger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    request_id: str = None,
    **extra: Any
) -> None:
    """
    Log an API request with standard fields.
    
    Args:
        logger: The logger to use
        method: HTTP method (GET, POST, etc.)
        path: Request path
        status_code: HTTP response status code
        duration_ms: Request duration in milliseconds
        request_id: Unique request identifier
        **extra: Additional fields to include
    """
    logger.info(
        "api_request",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=round(duration_ms, 2),
        request_id=request_id,
        **extra
    )
