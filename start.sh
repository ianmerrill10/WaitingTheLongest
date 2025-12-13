#!/bin/bash
# ============================================================================
# Waiting The Longest - Quick Start Script (Mac/Linux)
# ============================================================================
# Usage: ./start.sh
# ============================================================================

set -e

echo ""
echo "============================================"
echo " Waiting The Longest - Quick Start"
echo "============================================"
echo ""

# Navigate to project root
cd "$(dirname "$0")"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.10+ from https://python.org"
    exit 1
fi

# Check if venv exists
if [ ! -d "backend/.venv" ]; then
    echo "Setting up development environment..."
    python3 scripts/dev_setup.py
fi

# Start the server
echo ""
echo "Starting development server..."
echo "Press Ctrl+C to stop"
echo ""
python3 scripts/run.py --open
