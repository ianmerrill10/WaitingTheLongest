#!/bin/bash
# ===============================================================================
# Waiting The Longest™ - Development Setup Script
# ===============================================================================
# Purpose: Set up local development environment
# Usage: ./scripts/dev-setup.sh
# ===============================================================================

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${BLUE}==>${NC} $1"
}

# Check for required commands
check_requirements() {
    log_step "Checking requirements..."
    
    local missing=()
    
    if ! command -v python3 &> /dev/null; then
        missing+=("python3")
    fi
    
    if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
        missing+=("pip")
    fi
    
    if ! command -v git &> /dev/null; then
        missing+=("git")
    fi
    
    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing[*]}"
        exit 1
    fi
    
    log_info "All requirements satisfied"
}

# Create virtual environment
setup_venv() {
    log_step "Setting up Python virtual environment..."
    
    if [ -d "venv" ]; then
        log_info "Virtual environment already exists"
    else
        python3 -m venv venv
        log_info "Virtual environment created"
    fi
    
    # Activate
    source venv/bin/activate
    log_info "Virtual environment activated"
}

# Install Python dependencies
install_python_deps() {
    log_step "Installing Python dependencies..."
    
    pip install --upgrade pip
    pip install -r backend/requirements.txt
    
    # Install dev dependencies
    pip install pytest pytest-asyncio pytest-cov httpx black isort flake8 pre-commit faker
    
    log_info "Python dependencies installed"
}

# Set up pre-commit hooks
setup_precommit() {
    log_step "Setting up pre-commit hooks..."
    
    if command -v pre-commit &> /dev/null; then
        pre-commit install
        log_info "Pre-commit hooks installed"
    else
        log_warn "pre-commit not found, skipping hooks setup"
    fi
}

# Create .env file from template
setup_env_file() {
    log_step "Setting up environment file..."
    
    if [ -f ".env" ]; then
        log_info ".env file already exists"
    elif [ -f ".env.example" ]; then
        cp .env.example .env
        log_info ".env file created from template"
        log_warn "Please edit .env and add your API keys"
    else
        log_warn "No .env.example found"
    fi
}

# Initialize database
init_database() {
    log_step "Initializing database..."
    
    cd backend
    
    # Run database initialization
    python -c "
from app.database import engine, Base
from app.models import Animal, Shelter, SuccessStory, NewsletterSubscriber
Base.metadata.create_all(bind=engine)
print('Database tables created')
"
    
    cd ..
    log_info "Database initialized"
}

# Run tests to verify setup
verify_setup() {
    log_step "Verifying setup..."
    
    cd backend
    python -m pytest tests/ -v --tb=short -q 2>/dev/null || log_warn "Some tests failed (this may be expected)"
    cd ..
    
    log_info "Setup verification complete"
}

# Print summary
print_summary() {
    echo ""
    echo "==============================================="
    echo -e "${GREEN}Development Setup Complete!${NC}"
    echo "==============================================="
    echo ""
    echo "Next steps:"
    echo "1. Activate the virtual environment:"
    echo "   source venv/bin/activate"
    echo ""
    echo "2. Edit .env with your API keys:"
    echo "   nano .env"
    echo ""
    echo "3. Start the development server:"
    echo "   cd backend && uvicorn app.main:app --reload"
    echo ""
    echo "4. Open in browser:"
    echo "   http://localhost:8000"
    echo ""
    echo "5. Run tests:"
    echo "   cd backend && pytest"
    echo ""
    echo "==============================================="
}

# Main
main() {
    echo "==============================================="
    echo "Waiting The Longest™ - Development Setup"
    echo "==============================================="
    
    check_requirements
    setup_venv
    install_python_deps
    setup_precommit
    setup_env_file
    init_database
    verify_setup
    print_summary
}

main "$@"
