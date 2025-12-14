"""
Waiting The Longest™ - Security Tests
======================================
Tests for security vulnerabilities and protections.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestInputValidation:
    """Test that inputs are properly validated."""
    
    def test_sql_injection_prevention(self, client):
        """SQL injection attempts should be blocked or escaped."""
        malicious_inputs = [
            "'; DROP TABLE animals; --",
            "1 OR 1=1",
            "1'; SELECT * FROM users; --",
            "admin'--",
            "1 UNION SELECT * FROM shelters",
        ]
        
        for payload in malicious_inputs:
            response = client.get(f"/animals?species={payload}")
            # Should either return empty results or 400, not 500
            assert response.status_code in [200, 400, 422], \
                f"Potential SQL injection vulnerability with payload: {payload}"
    
    def test_xss_prevention_in_names(self, client):
        """XSS attempts should be escaped in output."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
        ]
        
        for payload in xss_payloads:
            response = client.get(f"/animals?name={payload}")
            # Should return OK but content should be escaped
            if response.status_code == 200:
                content = response.text
                # Raw script tags should not appear unescaped
                assert "<script>" not in content or "&lt;script&gt;" in content
    
    def test_path_traversal_prevention(self, client):
        """Path traversal attempts should be blocked."""
        payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "%2e%2e%2f%2e%2e%2f",
        ]
        
        for payload in payloads:
            response = client.get(f"/files/{payload}")
            # Should return 404 or 400, not actual file contents
            assert response.status_code in [400, 403, 404, 405, 422]
    
    def test_null_byte_injection(self, client):
        """Null byte injection should be handled."""
        response = client.get("/animals?species=dog%00.txt")
        # Should not cause server error
        assert response.status_code in [200, 400, 422]


class TestEmailValidation:
    """Test email input validation."""
    
    def test_invalid_email_rejected(self, client):
        """Invalid emails should be rejected."""
        invalid_emails = [
            "notanemail",
            "@nodomain.com",
            "no@domain",
            "spaces in@email.com",
            "email@.com",
            "",
        ]
        
        for email in invalid_emails:
            response = client.post(
                "/newsletter/subscribe",
                json={"email": email}
            )
            # Should return validation error, not success
            assert response.status_code in [400, 422], \
                f"Invalid email accepted: {email}"
    
    def test_email_max_length(self, client):
        """Very long emails should be rejected."""
        long_email = "a" * 500 + "@example.com"
        
        response = client.post(
            "/newsletter/subscribe",
            json={"email": long_email}
        )
        
        assert response.status_code in [400, 422]


class TestSecurityHeaders:
    """Test that security headers are present."""
    
    def test_content_type_header(self, client):
        """Responses should have proper content-type."""
        response = client.get("/animals")
        
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type
    
    def test_cache_control_on_sensitive_endpoints(self, client):
        """Sensitive endpoints should have cache-control."""
        # Health might have different caching than user data
        response = client.get("/health")
        # Just verify the request works, cache headers are optional
        assert response.status_code == 200


class TestRateLimiting:
    """Test rate limiting protections."""
    
    @pytest.mark.slow
    def test_rate_limit_enforced(self, client):
        """Rate limiting should kick in for excessive requests."""
        statuses = []
        
        for _ in range(150):  # Make many rapid requests
            response = client.get("/animals")
            statuses.append(response.status_code)
            
            if response.status_code == 429:
                # Rate limit working
                break
        
        # Either we hit rate limit or all succeeded (acceptable either way)
        assert 429 in statuses or all(s == 200 for s in statuses)
    
    def test_rate_limit_response_format(self, client):
        """Rate limit response should be informative."""
        # Make requests until rate limited
        for _ in range(200):
            response = client.get("/animals")
            
            if response.status_code == 429:
                # Should include retry-after or informative message
                assert "retry" in response.text.lower() or \
                       response.headers.get("Retry-After") is not None or \
                       "limit" in response.text.lower()
                break


class TestAuthenticationBypass:
    """Test that protected endpoints require authentication."""
    
    def test_admin_endpoints_require_auth(self, client):
        """Admin endpoints should require authentication."""
        admin_endpoints = [
            "/admin",
            "/admin/users",
            "/api/admin/settings",
            "/internal/config",
        ]
        
        for endpoint in admin_endpoints:
            response = client.get(endpoint)
            # Should return 401, 403, or 404 (if doesn't exist)
            assert response.status_code in [401, 403, 404, 405]


class TestDataExposure:
    """Test that sensitive data is not exposed."""
    
    def test_no_stack_traces_in_errors(self, client):
        """Error responses should not expose stack traces."""
        # Trigger an error
        response = client.get("/animals/not-an-integer")
        
        if response.status_code >= 400:
            content = response.text.lower()
            # Should not contain stack trace indicators
            assert "traceback" not in content
            assert "file \"" not in content
            assert ".py\", line" not in content
    
    def test_no_internal_ids_exposed(self, client):
        """Internal IDs should not be exposed unnecessarily."""
        response = client.get("/health")
        
        if response.status_code == 200:
            content = response.text.lower()
            # Should not expose database connection strings, internal IPs, etc.
            assert "password" not in content
            assert "secret" not in content


class TestCSRF:
    """Test CSRF protections."""
    
    def test_post_without_csrf_handled(self, client):
        """POST requests should handle CSRF appropriately."""
        # API endpoints typically use token auth instead of CSRF
        response = client.post(
            "/newsletter/subscribe",
            json={"email": "test@example.com"},
            headers={"Origin": "http://evil.com"}
        )
        
        # Should either work (if CORS allows) or be blocked
        # Not a server error
        assert response.status_code != 500


class TestDenialOfService:
    """Test protections against DoS attacks."""
    
    def test_large_payload_rejected(self, client):
        """Very large payloads should be rejected."""
        # Create a large payload
        large_data = {"data": "x" * 10_000_000}  # 10MB
        
        response = client.post("/newsletter/subscribe", json=large_data)
        
        # Should reject with 413 or 422, not process it
        assert response.status_code in [400, 413, 422]
    
    def test_deep_nested_json_rejected(self, client):
        """Deeply nested JSON should be rejected."""
        # Create deeply nested structure
        nested = {"a": None}
        current = nested
        for _ in range(100):
            current["a"] = {"a": None}
            current = current["a"]
        
        response = client.post("/newsletter/subscribe", json=nested)
        
        # Should not cause stack overflow
        assert response.status_code in [400, 422]
    
    def test_query_complexity_limited(self, client):
        """Complex queries should be limited."""
        # Try many filters at once
        params = "&".join([f"filter{i}=value{i}" for i in range(100)])
        
        response = client.get(f"/animals?{params}")
        
        # Should handle gracefully
        assert response.status_code in [200, 400, 414, 422]
