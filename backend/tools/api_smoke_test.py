#!/usr/bin/env python3
"""
API Smoke Test - Quick validation of core API endpoints.

Usage:
    python backend/tools/api_smoke_test.py [--base-url URL]

Checks:
    - GET /health
    - GET /api/animals
    - GET /api/longest-waiting
    - GET /api/stats
"""
from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from typing import Optional

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx")
    sys.exit(1)


@dataclass
class CheckResult:
    endpoint: str
    ok: bool
    status: int
    latency_ms: float
    error: Optional[str] = None


def check_endpoint(client: httpx.Client, endpoint: str) -> CheckResult:
    start = time.perf_counter()
    try:
        resp = client.get(endpoint, timeout=10.0)
        latency = (time.perf_counter() - start) * 1000
        return CheckResult(
            endpoint=endpoint,
            ok=resp.status_code < 400,
            status=resp.status_code,
            latency_ms=round(latency, 1),
        )
    except httpx.RequestError as e:
        latency = (time.perf_counter() - start) * 1000
        return CheckResult(
            endpoint=endpoint,
            ok=False,
            status=0,
            latency_ms=round(latency, 1),
            error=str(e),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="API smoke test")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="API base URL (default: http://127.0.0.1:8000)",
    )
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    endpoints = [
        "/health",
        "/api/animals",
        "/api/longest-waiting",
        "/api/stats",
    ]

    print(f"Smoke testing: {base}\n")

    results: list[CheckResult] = []
    with httpx.Client(base_url=base) as client:
        for ep in endpoints:
            result = check_endpoint(client, ep)
            results.append(result)
            status_icon = "✅" if result.ok else "❌"
            print(f"{status_icon} {ep} -> {result.status} ({result.latency_ms}ms)")
            if result.error:
                print(f"   Error: {result.error}")

    passed = sum(1 for r in results if r.ok)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
