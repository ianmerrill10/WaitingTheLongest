#!/usr/bin/env python3
"""
===============================================================================
Waiting The Longest™ - End-to-End Test Suite
===============================================================================
Purpose: Run end-to-end tests against a running instance of the application.
         Tests the full user journey from browsing to adoption stories.

Usage:
    python tests/e2e_tests.py                    # Run against localhost:8000
    python tests/e2e_tests.py --url http://...   # Run against custom URL
    python tests/e2e_tests.py --verbose          # Show detailed output

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from typing import Tuple, Optional


class E2ETestRunner:
    """End-to-end test runner for Waiting The Longest API."""
    
    def __init__(self, base_url: str, verbose: bool = False):
        self.base_url = base_url.rstrip("/")
        self.verbose = verbose
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def log(self, message: str):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"    {message}")
    
    def request(self, path: str, method: str = "GET", data: dict = None) -> Tuple[int, Optional[dict]]:
        """Make an HTTP request and return (status_code, response_body)."""
        url = f"{self.base_url}{path}"
        self.log(f"{method} {url}")
        
        try:
            req = urllib.request.Request(url, method=method)
            req.add_header("Content-Type", "application/json")
            req.add_header("Accept", "application/json")
            
            if data:
                req.data = json.dumps(data).encode("utf-8")
            
            with urllib.request.urlopen(req, timeout=10) as response:
                body = json.loads(response.read().decode())
                return response.status, body
                
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read().decode())
            except:
                body = None
            return e.code, body
        except urllib.error.URLError as e:
            return 0, {"error": str(e.reason)}
        except Exception as e:
            return 0, {"error": str(e)}
    
    def test(self, name: str, condition: bool, message: str = ""):
        """Record a test result."""
        if condition:
            self.passed += 1
            print(f"  ✅ {name}")
        else:
            self.failed += 1
            self.errors.append(f"{name}: {message}")
            print(f"  ❌ {name}")
            if message:
                print(f"      {message}")
    
    def run_all_tests(self):
        """Run all E2E tests."""
        print("\n" + "=" * 60)
        print("🧪 Waiting The Longest™ - E2E Test Suite")
        print("=" * 60)
        print(f"Target: {self.base_url}\n")
        
        self.test_health_check()
        self.test_root_endpoint()
        self.test_animals_list()
        self.test_animals_filtering()
        self.test_animals_pagination()
        self.test_animals_sorting()
        self.test_longest_waiting()
        self.test_stats_endpoint()
        self.test_success_stories()
        self.test_request_id_header()
        self.test_cors_headers()
        self.test_error_handling()
        
        self.print_summary()
        return self.failed == 0
    
    def test_health_check(self):
        """Test health check endpoint."""
        print("\n📋 Health Check Tests")
        print("-" * 40)
        
        status, body = self.request("/health")
        
        self.test(
            "Health endpoint returns 200",
            status == 200,
            f"Got status {status}"
        )
        
        self.test(
            "Health shows database status",
            body and "database" in body,
            "Missing 'database' field"
        )
        
        self.test(
            "Database is healthy",
            body and body.get("database") == "healthy",
            f"Database status: {body.get('database') if body else 'unknown'}"
        )
    
    def test_root_endpoint(self):
        """Test root API endpoint."""
        print("\n🏠 Root Endpoint Tests")
        print("-" * 40)
        
        status, body = self.request("/")
        
        self.test(
            "Root endpoint returns 200",
            status == 200,
            f"Got status {status}"
        )
        
        self.test(
            "Response includes API name",
            body and "name" in body,
            "Missing 'name' field"
        )
        
        self.test(
            "Response includes version",
            body and "version" in body,
            "Missing 'version' field"
        )
    
    def test_animals_list(self):
        """Test animals list endpoint."""
        print("\n🐕 Animals List Tests")
        print("-" * 40)
        
        status, body = self.request("/api/animals")
        
        self.test(
            "Animals endpoint returns 200",
            status == 200,
            f"Got status {status}"
        )
        
        self.test(
            "Response includes animals array",
            body and "animals" in body,
            "Missing 'animals' field"
        )
        
        self.test(
            "Response includes pagination info",
            body and all(k in body for k in ["page", "page_size", "total"]),
            "Missing pagination fields"
        )
    
    def test_animals_filtering(self):
        """Test animals filtering."""
        print("\n🔍 Animals Filtering Tests")
        print("-" * 40)
        
        # Test species filter
        status, body = self.request("/api/animals?species=dog")
        
        self.test(
            "Species filter works",
            status == 200,
            f"Got status {status}"
        )
        
        if body and body.get("animals"):
            all_dogs = all(
                a.get("species", "").lower() == "dog" 
                for a in body["animals"]
            )
            self.test(
                "All results match species filter",
                all_dogs,
                "Found non-dog animals in results"
            )
        
        # Test combined filters
        status, body = self.request("/api/animals?species=dog&gender=Male")
        self.test(
            "Combined filters work",
            status == 200,
            f"Got status {status}"
        )
    
    def test_animals_pagination(self):
        """Test animals pagination."""
        print("\n📄 Pagination Tests")
        print("-" * 40)
        
        # Get first page
        status, page1 = self.request("/api/animals?page=1&page_size=5")
        
        self.test(
            "First page returns 200",
            status == 200,
            f"Got status {status}"
        )
        
        self.test(
            "Page size is respected",
            page1 and len(page1.get("animals", [])) <= 5,
            f"Got {len(page1.get('animals', []))} animals"
        )
        
        # Get second page
        status, page2 = self.request("/api/animals?page=2&page_size=5")
        
        self.test(
            "Second page returns 200",
            status == 200,
            f"Got status {status}"
        )
        
        # Check pages are different (if there's enough data)
        if page1 and page2:
            ids1 = set(a.get("id") for a in page1.get("animals", []))
            ids2 = set(a.get("id") for a in page2.get("animals", []))
            self.test(
                "Pages contain different animals",
                not ids1.intersection(ids2) or not ids1 or not ids2,
                "Same animals on different pages"
            )
    
    def test_animals_sorting(self):
        """Test animals sorting."""
        print("\n🔢 Sorting Tests")
        print("-" * 40)
        
        # Sort by days waiting descending
        status, body = self.request("/api/animals?sort_by=days_waiting&sort_order=desc")
        
        self.test(
            "Sorting endpoint returns 200",
            status == 200,
            f"Got status {status}"
        )
        
        if body and body.get("animals") and len(body["animals"]) > 1:
            animals = body["animals"]
            days = [a.get("days_waiting", 0) for a in animals]
            is_sorted = all(days[i] >= days[i+1] for i in range(len(days)-1))
            self.test(
                "Animals sorted by days waiting (desc)",
                is_sorted,
                f"Days waiting: {days[:5]}..."
            )
    
    def test_longest_waiting(self):
        """Test longest waiting endpoint."""
        print("\n⏰ Longest Waiting Tests")
        print("-" * 40)
        
        status, body = self.request("/api/longest-waiting?limit=5")
        
        self.test(
            "Longest waiting returns 200",
            status == 200,
            f"Got status {status}"
        )
        
        self.test(
            "Response is a list",
            isinstance(body, list),
            f"Got type {type(body)}"
        )
        
        self.test(
            "Limit is respected",
            body is None or len(body) <= 5,
            f"Got {len(body) if body else 0} animals"
        )
    
    def test_stats_endpoint(self):
        """Test stats endpoint."""
        print("\n📊 Stats Tests")
        print("-" * 40)
        
        status, body = self.request("/api/stats")
        
        self.test(
            "Stats endpoint returns 200",
            status == 200,
            f"Got status {status}"
        )
        
        expected_fields = ["total_animals", "available_animals", "total_shelters"]
        has_fields = body and all(k in body for k in expected_fields)
        self.test(
            "Stats includes required fields",
            has_fields,
            f"Missing some of {expected_fields}"
        )
    
    def test_success_stories(self):
        """Test success stories endpoint."""
        print("\n📖 Success Stories Tests")
        print("-" * 40)
        
        status, body = self.request("/api/success-stories")
        
        self.test(
            "Success stories returns 200",
            status == 200,
            f"Got status {status}"
        )
        
        self.test(
            "Response is a list",
            isinstance(body, list),
            f"Got type {type(body)}"
        )
    
    def test_request_id_header(self):
        """Test request ID header is present."""
        print("\n🏷️ Request ID Tests")
        print("-" * 40)
        
        url = f"{self.base_url}/health"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                request_id = response.headers.get("X-Request-ID")
                self.test(
                    "X-Request-ID header present",
                    request_id is not None,
                    "Missing X-Request-ID header"
                )
        except Exception as e:
            self.test("X-Request-ID header present", False, str(e))
    
    def test_cors_headers(self):
        """Test CORS headers."""
        print("\n🌐 CORS Tests")
        print("-" * 40)
        
        url = f"{self.base_url}/health"
        try:
            req = urllib.request.Request(url)
            req.add_header("Origin", "http://localhost:3000")
            with urllib.request.urlopen(req, timeout=5) as response:
                cors_header = response.headers.get("Access-Control-Allow-Origin")
                self.test(
                    "CORS headers present",
                    cors_header is not None,
                    "Missing CORS headers"
                )
        except Exception as e:
            self.test("CORS headers present", False, str(e))
    
    def test_error_handling(self):
        """Test error handling."""
        print("\n⚠️ Error Handling Tests")
        print("-" * 40)
        
        # Test 404
        status, body = self.request("/api/animals/99999999")
        self.test(
            "Non-existent animal returns 404",
            status == 404,
            f"Got status {status}"
        )
        
        # Test invalid page
        status, body = self.request("/api/animals?page=-1")
        self.test(
            "Invalid page parameter handled",
            status in [200, 400, 422],
            f"Got unexpected status {status}"
        )
    
    def print_summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        print(f"  Total:  {total}")
        print(f"  Passed: {self.passed} ✅")
        print(f"  Failed: {self.failed} ❌")
        
        if self.errors:
            print("\n  Failures:")
            for error in self.errors:
                print(f"    • {error}")
        
        print("=" * 60)
        
        if self.failed == 0:
            print("🎉 All tests passed!")
        else:
            print(f"⚠️ {self.failed} test(s) failed")


def main():
    parser = argparse.ArgumentParser(
        description="Run E2E tests for Waiting The Longest"
    )
    parser.add_argument(
        "--url", "-u",
        default="http://localhost:8000",
        help="Base URL to test against"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output"
    )
    
    args = parser.parse_args()
    
    runner = E2ETestRunner(args.url, args.verbose)
    success = runner.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
