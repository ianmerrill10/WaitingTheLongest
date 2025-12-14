"""
===============================================================================
Waiting The Longest™ - Prometheus Metrics Endpoint
===============================================================================
Purpose: Expose application metrics for Prometheus monitoring.
         Tracks API usage, response times, and business metrics.

Author: Waiting The Longest™ Development Team
Dependencies: prometheus_client
===============================================================================
"""

import time
from functools import wraps
from typing import Callable, Dict, Any, Optional
import logging

# Try to import prometheus_client, provide fallbacks if not installed
try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Info,
        generate_latest, CONTENT_TYPE_LATEST,
        CollectorRegistry, REGISTRY
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = None
    Histogram = None
    Gauge = None
    Info = None

logger = logging.getLogger(__name__)


class PrometheusMetrics:
    """Application metrics for Prometheus monitoring."""
    
    def __init__(self, registry=None):
        """Initialize metrics collectors."""
        if not PROMETHEUS_AVAILABLE:
            logger.warning("prometheus_client not installed. Metrics disabled.")
            self.enabled = False
            return
            
        self.enabled = True
        self.registry = registry or REGISTRY
        
        # HTTP Request metrics
        self.http_requests_total = Counter(
            'wtl_http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.http_request_duration_seconds = Histogram(
            'wtl_http_request_duration_seconds',
            'HTTP request latency',
            ['method', 'endpoint'],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry
        )
        
        # Business metrics
        self.animals_total = Gauge(
            'wtl_animals_total',
            'Total animals in database',
            ['species', 'status'],
            registry=self.registry
        )
        
        self.longest_wait_days = Gauge(
            'wtl_longest_wait_days',
            'Longest waiting animal in days',
            ['species'],
            registry=self.registry
        )
        
        self.shelters_total = Gauge(
            'wtl_shelters_total',
            'Total shelters in database',
            registry=self.registry
        )
        
        self.adoptions_total = Counter(
            'wtl_adoptions_total',
            'Total adoptions processed',
            registry=self.registry
        )
        
        # API-specific metrics
        self.api_errors_total = Counter(
            'wtl_api_errors_total',
            'Total API errors',
            ['endpoint', 'error_type'],
            registry=self.registry
        )
        
        self.ingestor_runs_total = Counter(
            'wtl_ingestor_runs_total',
            'Total ingestor runs',
            ['source', 'status'],
            registry=self.registry
        )
        
        self.ingestor_animals_processed = Counter(
            'wtl_ingestor_animals_processed_total',
            'Animals processed by ingestor',
            ['source', 'action'],
            registry=self.registry
        )
        
        # Email/Newsletter metrics
        self.newsletter_subscribers = Gauge(
            'wtl_newsletter_subscribers_total',
            'Total active newsletter subscribers',
            registry=self.registry
        )
        
        self.emails_sent_total = Counter(
            'wtl_emails_sent_total',
            'Total emails sent',
            ['type'],
            registry=self.registry
        )
        
        # Application info
        self.app_info = Info(
            'wtl_app',
            'Application information',
            registry=self.registry
        )
        self.app_info.info({
            'version': '1.0.0',
            'python_version': '3.12',
            'framework': 'FastAPI'
        })
    
    def track_request(
        self,
        method: str,
        endpoint: str,
        status: int,
        duration: float
    ) -> None:
        """Track an HTTP request."""
        if not self.enabled:
            return
        
        # Normalize endpoint (remove IDs)
        endpoint = self._normalize_endpoint(endpoint)
        
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status)
        ).inc()
        
        self.http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def track_error(self, endpoint: str, error_type: str) -> None:
        """Track an API error."""
        if not self.enabled:
            return
        
        endpoint = self._normalize_endpoint(endpoint)
        self.api_errors_total.labels(
            endpoint=endpoint,
            error_type=error_type
        ).inc()
    
    def update_animal_counts(self, counts: Dict[str, Dict[str, int]]) -> None:
        """Update animal count gauges.
        
        Args:
            counts: Dict like {'dog': {'available': 100, 'adopted': 50}, ...}
        """
        if not self.enabled:
            return
        
        for species, statuses in counts.items():
            for status, count in statuses.items():
                self.animals_total.labels(species=species, status=status).set(count)
    
    def update_longest_wait(self, waits: Dict[str, int]) -> None:
        """Update longest wait gauges.
        
        Args:
            waits: Dict like {'dog': 500, 'cat': 400, ...}
        """
        if not self.enabled:
            return
        
        for species, days in waits.items():
            self.longest_wait_days.labels(species=species).set(days)
    
    def track_adoption(self) -> None:
        """Track an adoption."""
        if not self.enabled:
            return
        self.adoptions_total.inc()
    
    def track_ingestor_run(self, source: str, status: str) -> None:
        """Track an ingestor run."""
        if not self.enabled:
            return
        self.ingestor_runs_total.labels(source=source, status=status).inc()
    
    def track_animals_processed(self, source: str, created: int, updated: int, skipped: int) -> None:
        """Track animals processed by ingestor."""
        if not self.enabled:
            return
        if created > 0:
            self.ingestor_animals_processed.labels(source=source, action='created').inc(created)
        if updated > 0:
            self.ingestor_animals_processed.labels(source=source, action='updated').inc(updated)
        if skipped > 0:
            self.ingestor_animals_processed.labels(source=source, action='skipped').inc(skipped)
    
    def track_email_sent(self, email_type: str) -> None:
        """Track an email sent."""
        if not self.enabled:
            return
        self.emails_sent_total.labels(type=email_type).inc()
    
    def set_subscriber_count(self, count: int) -> None:
        """Set newsletter subscriber count."""
        if not self.enabled:
            return
        self.newsletter_subscribers.set(count)
    
    def set_shelter_count(self, count: int) -> None:
        """Set shelter count."""
        if not self.enabled:
            return
        self.shelters_total.set(count)
    
    def generate_metrics(self) -> bytes:
        """Generate Prometheus metrics output."""
        if not self.enabled:
            return b"# Metrics disabled - prometheus_client not installed\n"
        return generate_latest(self.registry)
    
    def get_content_type(self) -> str:
        """Get Prometheus content type."""
        if not self.enabled:
            return "text/plain"
        return CONTENT_TYPE_LATEST
    
    def _normalize_endpoint(self, endpoint: str) -> str:
        """Normalize endpoint path by replacing IDs with placeholders."""
        import re
        # Replace numeric IDs
        endpoint = re.sub(r'/\d+', '/{id}', endpoint)
        # Replace UUIDs
        endpoint = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{id}',
            endpoint,
            flags=re.IGNORECASE
        )
        return endpoint


def metrics_middleware(metrics: PrometheusMetrics):
    """Create FastAPI middleware for request tracking."""
    
    async def middleware(request, call_next):
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            metrics.track_request(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code,
                duration=duration
            )
            
            return response
        except Exception as e:
            duration = time.time() - start_time
            metrics.track_error(request.url.path, type(e).__name__)
            raise
    
    return middleware


# Singleton instance
_metrics: Optional[PrometheusMetrics] = None


def get_metrics() -> PrometheusMetrics:
    """Get or create the metrics singleton."""
    global _metrics
    if _metrics is None:
        _metrics = PrometheusMetrics()
    return _metrics
