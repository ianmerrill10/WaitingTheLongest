#!/usr/bin/env python3
"""
===============================================================================
Waiting The Longest™ - Developer Setup Script
===============================================================================
Purpose: One-command setup for new developers. Creates virtual environment,
         installs dependencies, initializes database, and seeds demo data.

Usage:
    python scripts/dev_setup.py           # Full setup
    python scripts/dev_setup.py --skip-demo  # Skip demo data seeding
    python scripts/dev_setup.py --help       # Show options

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import subprocess
import sys
import os
from pathlib import Path
import argparse


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_backend_dir() -> Path:
    """Get the backend directory."""
    return get_project_root() / "backend"


def run_command(cmd: list, cwd: Path = None, env: dict = None) -> bool:
    """Run a command and return success status."""
    print(f"\n>>> {' '.join(cmd)}")
    try:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        result = subprocess.run(cmd, cwd=cwd, env=merged_env, capture_output=False)
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False


def check_python_version():
    """Ensure Python 3.10+ is available."""
    print("\n=== Checking Python Version ===")
    version = sys.version_info
    print(f"Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("ERROR: Python 3.10 or higher is required")
        return False
    print("✓ Python version OK")
    return True


def create_virtualenv(backend_dir: Path):
    """Create virtual environment if not exists."""
    print("\n=== Setting Up Virtual Environment ===")
    venv_path = backend_dir / ".venv"
    
    if venv_path.exists():
        print(f"✓ Virtual environment already exists at {venv_path}")
        return True
    
    print(f"Creating virtual environment at {venv_path}...")
    return run_command([sys.executable, "-m", "venv", str(venv_path)], cwd=backend_dir)


def get_venv_python(backend_dir: Path) -> str:
    """Get the path to the venv Python executable."""
    if sys.platform == "win32":
        return str(backend_dir / ".venv" / "Scripts" / "python.exe")
    return str(backend_dir / ".venv" / "bin" / "python")


def install_dependencies(backend_dir: Path):
    """Install Python dependencies."""
    print("\n=== Installing Dependencies ===")
    python_path = get_venv_python(backend_dir)
    requirements = backend_dir / "requirements.txt"
    
    if not requirements.exists():
        print(f"ERROR: {requirements} not found")
        return False
    
    # Upgrade pip first
    run_command([python_path, "-m", "pip", "install", "--upgrade", "pip"], cwd=backend_dir)
    
    # Install requirements
    return run_command([python_path, "-m", "pip", "install", "-r", str(requirements)], cwd=backend_dir)


def setup_env_file(backend_dir: Path):
    """Create .env file from example if not exists."""
    print("\n=== Setting Up Environment File ===")
    env_file = backend_dir / ".env"
    env_example = backend_dir.parent / ".env.example"
    
    if env_file.exists():
        print("✓ .env file already exists")
        return True
    
    if env_example.exists():
        print(f"Copying {env_example} to {env_file}")
        import shutil
        shutil.copy(env_example, env_file)
        print("✓ Created .env file (please update with your settings)")
        return True
    
    # Create minimal .env
    print("Creating minimal .env file...")
    env_content = """# Waiting The Longest Environment Configuration
# Copy this file to .env and update values as needed

DATABASE_URL=sqlite:///./waitingthelongest.db
SECRET_KEY=dev-secret-key-change-in-production
DEBUG=true
TESTING=false
CORS_ORIGINS=["http://localhost:8000","http://127.0.0.1:8000","http://localhost:5500"]
"""
    env_file.write_text(env_content)
    print("✓ Created minimal .env file")
    return True


def initialize_database(backend_dir: Path):
    """Initialize the database."""
    print("\n=== Initializing Database ===")
    python_path = get_venv_python(backend_dir)
    
    # Run a quick import to trigger table creation
    init_script = """
import sys
sys.path.insert(0, '.')
from app.database import engine, Base
from app.models import Animal, Observation, Shelter, SuccessStory
Base.metadata.create_all(bind=engine)
print('✓ Database tables created')
"""
    return run_command([python_path, "-c", init_script], cwd=backend_dir)


def seed_demo_data(backend_dir: Path):
    """Seed demo data for development."""
    print("\n=== Seeding Demo Data ===")
    python_path = get_venv_python(backend_dir)
    
    # Check if add_demo_data.py exists
    demo_script = backend_dir / "add_demo_data.py"
    tools_demo = backend_dir / "tools" / "generate_demo_data.py"
    
    if demo_script.exists():
        return run_command([python_path, str(demo_script)], cwd=backend_dir)
    elif tools_demo.exists():
        return run_command([python_path, str(tools_demo)], cwd=backend_dir)
    else:
        print("No demo data script found, skipping...")
        return True


def verify_setup(backend_dir: Path):
    """Verify the setup by running health check."""
    print("\n=== Verifying Setup ===")
    python_path = get_venv_python(backend_dir)
    
    # Quick import test
    verify_script = """
import sys
sys.path.insert(0, '.')
try:
    from app.main import app
    from app.database import get_db
    from app.models import Animal
    print('✓ All imports successful')
    print('✓ Setup complete!')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
"""
    return run_command([python_path, "-c", verify_script], cwd=backend_dir)


def print_next_steps():
    """Print next steps for the developer."""
    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETE!")
    print("=" * 60)
    print("""
Next steps:

1. Start the development server:
   cd backend
   .venv\\Scripts\\activate  # Windows
   # source .venv/bin/activate  # Mac/Linux
   uvicorn app.main:app --reload

2. Open the API docs:
   http://localhost:8000/api/docs

3. Open the frontend:
   Open frontend/index.html in browser
   (or use Live Server extension in VS Code)

4. Run tests:
   cd backend
   pytest

For more info, see:
- README.md
- OWNERS_MANUAL.md
- RUNBOOK.md
""")


def main():
    parser = argparse.ArgumentParser(
        description="Set up development environment for Waiting The Longest"
    )
    parser.add_argument(
        "--skip-demo",
        action="store_true",
        help="Skip seeding demo data"
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip installing dependencies (use existing venv)"
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("Waiting The Longest™ - Developer Setup")
    print("=" * 60)
    
    backend_dir = get_backend_dir()
    print(f"Backend directory: {backend_dir}")
    
    # Step 1: Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Step 2: Create virtual environment
    if not create_virtualenv(backend_dir):
        print("ERROR: Failed to create virtual environment")
        sys.exit(1)
    
    # Step 3: Install dependencies
    if not args.skip_deps:
        if not install_dependencies(backend_dir):
            print("ERROR: Failed to install dependencies")
            sys.exit(1)
    else:
        print("\n=== Skipping Dependency Installation ===")
    
    # Step 4: Setup .env file
    setup_env_file(backend_dir)
    
    # Step 5: Initialize database
    if not initialize_database(backend_dir):
        print("WARNING: Database initialization had issues")
    
    # Step 6: Seed demo data
    if not args.skip_demo:
        seed_demo_data(backend_dir)
    else:
        print("\n=== Skipping Demo Data ===")
    
    # Step 7: Verify setup
    if not verify_setup(backend_dir):
        print("WARNING: Verification had issues, but setup may still work")
    
    # Print next steps
    print_next_steps()


if __name__ == "__main__":
    main()
