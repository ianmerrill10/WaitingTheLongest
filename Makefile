# ============================================================================
# Waiting The Longest™ - Makefile
# ============================================================================
# Cross-platform command shortcuts for common development tasks.
# Note: On Windows, use `python scripts/run.py` directly or install make.
# ============================================================================

.PHONY: help install run test lint format clean docker ci setup seed

# Default target
help:
	@echo ""
	@echo "Waiting The Longest - Available Commands"
	@echo "========================================="
	@echo ""
	@echo "  make install     Install dependencies"
	@echo "  make setup       Full development setup"
	@echo "  make run         Start development server"
	@echo "  make test        Run all tests"
	@echo "  make lint        Run linting checks"
	@echo "  make format      Auto-format code"
	@echo "  make ci          Run all CI checks"
	@echo "  make seed        Seed demo data"
	@echo "  make clean       Clean generated files"
	@echo "  make docker      Build Docker image"
	@echo ""

# Python executable (adjust if needed)
PYTHON = python3
BACKEND = backend
VENV = $(BACKEND)/.venv
PIP = $(VENV)/bin/pip
PYTEST = $(VENV)/bin/pytest

# Windows compatibility
ifeq ($(OS),Windows_NT)
	PYTHON = python
	PIP = $(VENV)/Scripts/pip
	PYTEST = $(VENV)/Scripts/pytest
	VENV_PYTHON = $(VENV)/Scripts/python
else
	VENV_PYTHON = $(VENV)/bin/python
endif

# Install dependencies
install:
	cd $(BACKEND) && $(PYTHON) -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r $(BACKEND)/requirements.txt

# Full development setup
setup:
	$(PYTHON) scripts/dev_setup.py

# Start development server
run:
	$(PYTHON) scripts/run.py

# Run with browser
run-open:
	$(PYTHON) scripts/run.py --open

# Run all tests
test:
	cd $(BACKEND) && $(PYTEST) -v

# Quick test run
test-quick:
	cd $(BACKEND) && $(PYTEST) -q

# Run linting
lint:
	cd $(BACKEND) && $(VENV_PYTHON) -m flake8 app/ --max-line-length=100

# Format code
format:
	cd $(BACKEND) && $(VENV_PYTHON) -m black app/ tools/ tests/ --line-length=100
	cd $(BACKEND) && $(VENV_PYTHON) -m isort app/ tools/ tests/ --profile=black

# Run CI checks
ci:
	$(PYTHON) scripts/ci.py

# CI with auto-fix
ci-fix:
	$(PYTHON) scripts/ci.py --fix

# Seed demo data
seed:
	$(PYTHON) scripts/db_seed.py demo

# Clear database
db-clear:
	$(PYTHON) scripts/db_seed.py clear --force

# Reset database
db-reset:
	$(PYTHON) scripts/db_seed.py reset --force

# Database status
db-status:
	$(PYTHON) scripts/db_seed.py status

# Build Docker image
docker:
	docker build -t waitingthelongest:latest .

# Run Docker container
docker-run:
	docker run -p 8000:8000 waitingthelongest:latest

# Clean generated files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Full project validation
validate:
	$(PYTHON) scripts/full_project_check.py

# API smoke test
smoke-test:
	cd $(BACKEND) && $(VENV_PYTHON) tools/api_smoke_test.py

# Health check
health:
	$(PYTHON) scripts/health_check.py http://127.0.0.1:8000/health
