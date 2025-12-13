#!/usr/bin/env python3
"""
Health Check Script - Verify backend is running and healthy.

Usage:
    python scripts/health_check.py [URL]

Examples:
    python scripts/health_check.py                           # default localhost:8000
    python scripts/health_check.py http://localhost:8000
    python scripts/health_check.py https://your-app-runner-url.amazonaws.com
"""
from __future__ import annotations

import sys
import urllib.request
import urllib.error
import json
import time


def check_health(base_url: str) -> int:
    base = base_url.rstrip("/")
    health_url = f"{base}/health"

    print(f"Checking: {health_url}")
    start = time.perf_counter()

    try:
        req = urllib.request.Request(health_url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            latency = (time.perf_counter() - start) * 1000
            status = resp.status
            body = resp.read().decode("utf-8")

        print(f"Status: {status}")
        print(f"Latency: {latency:.1f}ms")

        try:
            data = json.loads(body)
            print(f"Response: {json.dumps(data, indent=2)}")
        except json.JSONDecodeError:
            print(f"Response (raw): {body[:500]}")

        if status == 200:
            print("\n✅ Backend is healthy!")
            return 0
        else:
            print(f"\n⚠️ Unexpected status: {status}")
            return 1

    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error: {e.code} {e.reason}")
        return 1
    except urllib.error.URLError as e:
        print(f"❌ Connection Error: {e.reason}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def main() -> int:
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "http://127.0.0.1:8000"

    return check_health(url)


if __name__ == "__main__":
    raise SystemExit(main())
