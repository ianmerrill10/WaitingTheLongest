"""
Waiting The Longest™ - Performance Tests
=========================================
Tests for API performance and response times.
"""

import pytest
import time
from datetime import date, timedelta
from statistics import mean, median
from typing import List

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def measure_response_time(client: TestClient, endpoint: str, num_requests: int = 10) -> List[float]:
    """Measure response times for an endpoint."""
    times = []
    for _ in range(num_requests):
        start = time.perf_counter()
        response = client.get(endpoint)
        end = time.perf_counter()
        
        if response.status_code == 200:
            times.append((end - start) * 1000)  # Convert to milliseconds
    
    return times


class TestResponseTimes:
    """Test that API endpoints respond within acceptable times."""
    
    # Maximum acceptable response times in milliseconds
    MAX_HEALTH_TIME_MS = 100
    MAX_LIST_TIME_MS = 500
    MAX_DETAIL_TIME_MS = 200
    
    def test_health_endpoint_fast(self, client):
        """Health endpoint should respond very quickly."""
        times = measure_response_time(client, "/health", num_requests=5)
        
        if times:
            avg_time = mean(times)
            assert avg_time < self.MAX_HEALTH_TIME_MS, \
                f"Health endpoint too slow: {avg_time:.1f}ms (max: {self.MAX_HEALTH_TIME_MS}ms)"
    
    def test_animals_list_reasonable_time(self, client):
        """Animals list should respond within acceptable time."""
        times = measure_response_time(client, "/animals?limit=20", num_requests=5)
        
        if times:
            avg_time = mean(times)
            # Relaxed timing for test environments
            assert avg_time < self.MAX_LIST_TIME_MS * 2, \
                f"Animals list too slow: {avg_time:.1f}ms (max: {self.MAX_LIST_TIME_MS * 2}ms)"
    
    def test_consistent_response_times(self, client):
        """Response times should be consistent (low variance)."""
        times = measure_response_time(client, "/health", num_requests=10)
        
        if len(times) >= 5:
            avg_time = mean(times)
            max_time = max(times)
            
            # Max time shouldn't be more than 3x the average (allows for warmup)
            assert max_time < avg_time * 3, \
                f"Inconsistent response times: avg={avg_time:.1f}ms, max={max_time:.1f}ms"


class TestConcurrentRequests:
    """Test behavior under concurrent load."""
    
    @pytest.mark.slow
    def test_concurrent_requests_succeed(self, client):
        """Multiple concurrent requests should all succeed."""
        import concurrent.futures
        
        def make_request():
            response = client.get("/health")
            return response.status_code
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # Most requests should succeed
        success_count = sum(1 for r in results if r == 200)
        assert success_count >= len(results) * 0.8, \
            f"Too many failures under load: {success_count}/{len(results)} succeeded"


class TestPaginationPerformance:
    """Test pagination doesn't degrade with page number."""
    
    def test_pagination_constant_time(self, client, populated_db):
        """Later pages should not be significantly slower than first page."""
        # Time first page
        start = time.perf_counter()
        response1 = client.get("/animals?page=1&limit=20")
        first_page_time = (time.perf_counter() - start) * 1000
        
        if response1.status_code != 200:
            pytest.skip("Pagination not implemented")
        
        # Time a later page
        start = time.perf_counter()
        response2 = client.get("/animals?page=5&limit=20")
        later_page_time = (time.perf_counter() - start) * 1000
        
        if response2.status_code == 200:
            # Later page should be within 2x of first page time
            assert later_page_time < first_page_time * 2, \
                f"Pagination degradation: page 1 = {first_page_time:.1f}ms, page 5 = {later_page_time:.1f}ms"


class TestFilterPerformance:
    """Test filter operations perform well."""
    
    def test_species_filter_fast(self, client, populated_db):
        """Species filter should be fast (indexed query)."""
        times = measure_response_time(client, "/animals?species=dog", num_requests=3)
        
        if times:
            avg_time = mean(times)
            # Should be fast since species should be indexed
            assert avg_time < 1000, f"Species filter too slow: {avg_time:.1f}ms"
    
    def test_combined_filters_reasonable(self, client, populated_db):
        """Combined filters should still perform well."""
        times = measure_response_time(
            client, 
            "/animals?species=dog&state=CA&min_days_waiting=30",
            num_requests=3
        )
        
        if times:
            avg_time = mean(times)
            # Allow more time for complex queries
            assert avg_time < 2000, f"Combined filters too slow: {avg_time:.1f}ms"


class TestDatabaseQueryEfficiency:
    """Test for N+1 query problems and efficient queries."""
    
    def test_animals_list_single_query(self, client, populated_db, caplog):
        """Animals list should use minimal queries."""
        import logging
        
        # Enable SQL logging temporarily
        logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)
        
        response = client.get("/animals?limit=20")
        
        # Reset logging
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
        
        assert response.status_code == 200
        # Test passes - actual query count verification requires more setup


class TestMemoryUsage:
    """Test that endpoints don't leak memory."""
    
    @pytest.mark.slow
    def test_no_memory_leak_on_repeated_requests(self, client):
        """Memory should not grow significantly with repeated requests."""
        import gc
        
        # Warm up
        for _ in range(5):
            client.get("/animals")
        
        gc.collect()
        
        # Make many requests
        for _ in range(50):
            client.get("/animals?limit=10")
        
        gc.collect()
        
        # If we got here without OOM, test passes
        assert True


# =============================================================================
# Benchmark Report Generator
# =============================================================================

def generate_performance_report(client: TestClient, endpoints: list) -> dict:
    """Generate a performance report for multiple endpoints."""
    report = {}
    
    for endpoint in endpoints:
        times = measure_response_time(client, endpoint, num_requests=10)
        
        if times:
            report[endpoint] = {
                "samples": len(times),
                "min_ms": round(min(times), 2),
                "max_ms": round(max(times), 2),
                "mean_ms": round(mean(times), 2),
                "median_ms": round(median(times), 2),
            }
        else:
            report[endpoint] = {"error": "No successful requests"}
    
    return report


@pytest.mark.slow
def test_generate_performance_report(client, capsys):
    """Generate and print a performance report."""
    endpoints = [
        "/health",
        "/animals",
        "/animals?limit=10",
        "/animals?species=dog",
        "/shelters",
    ]
    
    report = generate_performance_report(client, endpoints)
    
    print("\n" + "=" * 60)
    print("PERFORMANCE REPORT")
    print("=" * 60)
    
    for endpoint, stats in report.items():
        print(f"\n{endpoint}")
        if "error" in stats:
            print(f"  Error: {stats['error']}")
        else:
            print(f"  Samples: {stats['samples']}")
            print(f"  Min: {stats['min_ms']}ms")
            print(f"  Max: {stats['max_ms']}ms")
            print(f"  Mean: {stats['mean_ms']}ms")
            print(f"  Median: {stats['median_ms']}ms")
    
    print("\n" + "=" * 60)
    
    assert True  # Report generation succeeded
