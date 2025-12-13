#!/usr/bin/env python3
"""
===============================================================================
Waiting The Longest™ - One-Click Run Script
===============================================================================
Purpose: Start the entire development environment with a single command.
         Starts backend server and optionally opens frontend in browser.

Usage:
    python scripts/run.py              # Start backend server
    python scripts/run.py --open       # Start server and open browser
    python scripts/run.py --port 8080  # Use custom port

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import argparse
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).parent.parent


def get_backend_dir() -> Path:
    return get_project_root() / "backend"


def get_venv_python() -> str:
    backend_dir = get_backend_dir()
    if sys.platform == "win32":
        return str(backend_dir / ".venv" / "Scripts" / "python.exe")
    return str(backend_dir / ".venv" / "bin" / "python")


def check_venv_exists() -> bool:
    backend_dir = get_backend_dir()
    venv_path = backend_dir / ".venv"
    return venv_path.exists()


def run_setup():
    """Run the dev setup if venv doesn't exist."""
    print("Virtual environment not found. Running setup...")
    setup_script = get_project_root() / "scripts" / "dev_setup.py"
    subprocess.run([sys.executable, str(setup_script)], check=True)


def start_server(port: int = 8000, reload: bool = True):
    """Start the uvicorn server."""
    python_path = get_venv_python()
    backend_dir = get_backend_dir()
    
    cmd = [
        python_path, "-m", "uvicorn",
        "app.main:app",
        "--host", "127.0.0.1",
        "--port", str(port),
    ]
    
    if reload:
        cmd.append("--reload")
    
    print(f"\n🚀 Starting server on http://127.0.0.1:{port}")
    print("   API docs: http://127.0.0.1:{port}/api/docs")
    print("   Press Ctrl+C to stop\n")
    
    return subprocess.Popen(cmd, cwd=backend_dir)


def open_browser(port: int, delay: float = 2.0):
    """Open browser after a short delay."""
    time.sleep(delay)
    url = f"http://127.0.0.1:{port}"
    print(f"🌐 Opening {url} in browser...")
    webbrowser.open(url)


def main():
    parser = argparse.ArgumentParser(
        description="Start the Waiting The Longest development server"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000)"
    )
    parser.add_argument(
        "--open", "-o",
        action="store_true",
        help="Open browser after starting"
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable auto-reload (for production-like testing)"
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Force run setup before starting"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Waiting The Longest™ - Development Server")
    print("=" * 60)
    
    # Check/run setup
    if args.setup or not check_venv_exists():
        run_setup()
    
    # Start server
    server_process = start_server(
        port=args.port,
        reload=not args.no_reload
    )
    
    try:
        # Open browser if requested
        if args.open:
            import threading
            threading.Thread(
                target=open_browser,
                args=(args.port,),
                daemon=True
            ).start()
        
        # Wait for server
        server_process.wait()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Shutting down server...")
        server_process.terminate()
        server_process.wait()
        print("👋 Goodbye!")


if __name__ == "__main__":
    main()
