#!/usr/bin/env python3
"""
===============================================================================
Waiting The Longest™ - Monitoring Dashboard Script
===============================================================================
Purpose: Display real-time monitoring information for the application.
         Shows health status, performance metrics, and recent activity.

Usage:
    python scripts/monitor.py              # Show dashboard once
    python scripts/monitor.py --watch      # Continuous monitoring
    python scripts/monitor.py --json       # Output as JSON

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error


def get_health(base_url: str) -> dict:
    """Get health status from the API."""
    try:
        url = f"{base_url}/health"
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}


def get_stats(base_url: str) -> dict:
    """Get platform statistics from the API."""
    try:
        url = f"{base_url}/api/stats"
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        return {"error": str(e)}


def get_root_info(base_url: str) -> dict:
    """Get API root information."""
    try:
        with urllib.request.urlopen(base_url, timeout=5) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        return {"error": str(e)}


def format_number(n) -> str:
    """Format a number with commas."""
    if n is None:
        return "N/A"
    return f"{n:,}"


def format_uptime(seconds: int) -> str:
    """Format uptime in human-readable format."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h"


def get_docker_status() -> dict:
    """Get Docker container status if available."""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=wtl-", "--format", "{{.Names}}: {{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            containers = {}
            for line in result.stdout.strip().split("\n"):
                if ": " in line:
                    name, status = line.split(": ", 1)
                    containers[name] = status
            return containers
    except:
        pass
    return {}


def display_dashboard(base_url: str, as_json: bool = False):
    """Display the monitoring dashboard."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Gather data
    health = get_health(base_url)
    stats = get_stats(base_url)
    root_info = get_root_info(base_url)
    docker = get_docker_status()
    
    if as_json:
        output = {
            "timestamp": timestamp,
            "base_url": base_url,
            "health": health,
            "stats": stats,
            "root_info": root_info,
            "docker": docker
        }
        print(json.dumps(output, indent=2))
        return
    
    # Clear screen for watch mode
    if os.name == 'nt':
        os.system('cls')
    else:
        print("\033[H\033[J", end="")
    
    # Header
    print("=" * 60)
    print("🐾 Waiting The Longest™ - Monitoring Dashboard")
    print("=" * 60)
    print(f"  Time: {timestamp}")
    print(f"  URL:  {base_url}")
    print()
    
    # Health Status
    print("📊 Health Status")
    print("-" * 40)
    
    status = health.get("status", health.get("database", "unknown"))
    status_icon = "🟢" if status == "healthy" else "🔴"
    print(f"  {status_icon} API Status: {status}")
    
    db_status = health.get("database", "unknown")
    db_icon = "🟢" if db_status == "healthy" else "🔴"
    print(f"  {db_icon} Database:   {db_status}")
    
    api_version = root_info.get("version", "unknown")
    print(f"  📦 Version:    {api_version}")
    print()
    
    # Platform Statistics
    print("📈 Platform Statistics")
    print("-" * 40)
    
    if "error" not in stats:
        print(f"  🐕 Total Animals:     {format_number(stats.get('total_animals'))}")
        print(f"  ✅ Available:         {format_number(stats.get('available_animals'))}")
        print(f"  🏠 Adopted:           {format_number(stats.get('adopted_animals'))}")
        print(f"  🏢 Shelters:          {format_number(stats.get('total_shelters'))}")
        print(f"  📖 Success Stories:   {format_number(stats.get('success_stories'))}")
        
        if stats.get("data_updated_at"):
            print(f"  🕐 Last Update:       {stats.get('data_updated_at')}")
    else:
        print(f"  ⚠️  Stats unavailable: {stats.get('error')}")
    print()
    
    # Docker Status
    if docker:
        print("🐳 Docker Containers")
        print("-" * 40)
        for name, status in docker.items():
            status_icon = "🟢" if "Up" in status else "🔴"
            print(f"  {status_icon} {name}: {status}")
        print()
    
    # Quick Actions
    print("🔧 Quick Actions")
    print("-" * 40)
    print(f"  API Docs:    {base_url}/api/docs")
    print(f"  Health:      {base_url}/health")
    print(f"  Animals:     {base_url}/api/animals")
    print()


def watch_mode(base_url: str, interval: int = 5):
    """Continuously display the dashboard."""
    print(f"Starting watch mode (refresh every {interval}s). Press Ctrl+C to stop.\n")
    
    try:
        while True:
            display_dashboard(base_url)
            print(f"\n[Refreshing in {interval}s... Press Ctrl+C to stop]")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped.")


def main():
    parser = argparse.ArgumentParser(
        description="Monitor Waiting The Longest application"
    )
    parser.add_argument(
        "--url", "-u",
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Continuous monitoring mode"
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=5,
        help="Refresh interval in seconds for watch mode (default: 5)"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output as JSON"
    )
    
    args = parser.parse_args()
    
    if args.watch:
        watch_mode(args.url, args.interval)
    else:
        display_dashboard(args.url, args.json)


if __name__ == "__main__":
    main()
