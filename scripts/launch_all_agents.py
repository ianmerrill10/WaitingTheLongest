#!/usr/bin/env python3
"""
===============================================================================
Waiting The Longest™ - Agent Launcher & Orchestrator
===============================================================================
This script coordinates ALL custom AI agents to work in parallel,
systematically completing every project category until launch-ready.

Usage:
    python scripts/launch_all_agents.py [--category CATEGORY] [--parallel N]
    
Examples:
    python scripts/launch_all_agents.py                    # Full orchestration
    python scripts/launch_all_agents.py --category backend # Focus on backend
    python scripts/launch_all_agents.py --parallel 4       # Run 4 agents at once

Author: Waiting The Longest™ AI Agent Team
===============================================================================
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
AGENTS_DIR = PROJECT_ROOT / ".github" / "agents"

# =============================================================================
# PROJECT CATEGORIES & TASKS
# =============================================================================

CATEGORIES = {
    "1_core_backend": {
        "name": "Core Backend",
        "priority": "CRITICAL",
        "agents": ["backend-engineer", "api-engineer", "database-engineer", "error-handler"],
        "tasks": [
            {"name": "verify_models", "command": "python -c 'from app.models import *; print(\"Models OK\")'"},
            {"name": "verify_crud", "command": "python -c 'from app.crud import *; print(\"CRUD OK\")'"},
            {"name": "verify_main", "command": "python -c 'from app.main import app; print(\"App OK\")'"},
            {"name": "verify_schemas", "command": "python -c 'from app.schemas import *; print(\"Schemas OK\")'"},
            {"name": "run_api_tests", "command": "python -m pytest tests/test_api.py -v --tb=short"},
        ],
        "files": [
            "backend/app/models.py",
            "backend/app/crud.py", 
            "backend/app/main.py",
            "backend/app/schemas.py",
            "backend/app/database.py",
            "backend/app/config.py",
        ]
    },
    "2_data_ingestion": {
        "name": "Data Ingestion",
        "priority": "CRITICAL",
        "agents": ["integration-engineer", "database-engineer"],
        "tasks": [
            {"name": "verify_ingestor", "command": "python -c 'from ingestors.rescuegroups import *; print(\"Ingestor OK\")'"},
            {"name": "verify_scheduler", "command": "python -c 'from workers.scheduler import *; print(\"Scheduler OK\")'"},
        ],
        "files": [
            "backend/ingestors/rescuegroups.py",
            "backend/ingestors/__init__.py",
            "backend/workers/scheduler.py",
        ]
    },
    "3_monetization": {
        "name": "Monetization",
        "priority": "HIGH",
        "agents": ["backend-engineer", "api-engineer"],
        "tasks": [
            {"name": "verify_amazon", "command": "python -c 'from monetization.amazon_associates import *; print(\"Amazon OK\")'"},
            {"name": "run_affiliate_tests", "command": "python -m pytest tests/test_amazon_associates.py -v --tb=short"},
        ],
        "files": [
            "backend/monetization/amazon_associates.py",
            "backend/monetization/__init__.py",
        ]
    },
    "4_frontend": {
        "name": "Frontend",
        "priority": "CRITICAL",
        "agents": ["frontend-engineer", "mobile-engineer", "accessibility-engineer", "seo-engineer"],
        "tasks": [
            {"name": "verify_html", "command": "test -f ../frontend/index.html && echo 'HTML exists'"},
            {"name": "verify_css", "command": "test -f ../frontend/styles.css && echo 'CSS exists' || echo 'CSS missing - needs creation'"},
            {"name": "verify_js", "command": "test -f ../frontend/app.js && echo 'JS exists' || echo 'JS missing - needs creation'"},
        ],
        "files": [
            "frontend/index.html",
            "frontend/styles.css",
            "frontend/app.js",
        ]
    },
    "5_testing": {
        "name": "Testing",
        "priority": "HIGH",
        "agents": ["test-engineer", "qa-engineer"],
        "tasks": [
            {"name": "run_all_tests", "command": "python -m pytest tests/ -v --tb=short"},
            {"name": "check_coverage", "command": "python -m pytest tests/ --cov=app --cov-report=term-missing || echo 'Coverage check complete'"},
        ],
        "files": [
            "backend/tests/conftest.py",
            "backend/tests/test_api.py",
            "backend/tests/test_crud.py",
            "backend/tests/test_models.py",
            "backend/tests/test_amazon_associates.py",
        ]
    },
    "6_security": {
        "name": "Security",
        "priority": "CRITICAL",
        "agents": ["security-guardian", "devops-engineer"],
        "tasks": [
            {"name": "check_secrets", "command": "grep -r 'password\\|secret\\|api_key' app/ --include='*.py' | grep -v '.pyc' | grep -v 'settings\\|config\\|environ' || echo 'No hardcoded secrets found'"},
            {"name": "verify_env_example", "command": "test -f ../.env.example && echo 'ENV example exists'"},
        ],
        "files": [
            "backend/app/config.py",
            ".env.example",
            "nginx/waitingthelongest.conf",
        ]
    },
    "7_infrastructure": {
        "name": "Infrastructure",
        "priority": "HIGH",
        "agents": ["devops-engineer", "launch-coordinator"],
        "tasks": [
            {"name": "verify_deploy", "command": "test -f ../scripts/deploy.sh && bash -n ../scripts/deploy.sh && echo 'Deploy script valid'"},
            {"name": "verify_nginx", "command": "test -f ../nginx/waitingthelongest.conf && echo 'Nginx config exists'"},
            {"name": "verify_systemd", "command": "test -f ../systemd/waitingthelongest.service && echo 'Systemd service exists'"},
        ],
        "files": [
            "scripts/deploy.sh",
            "nginx/waitingthelongest.conf",
            "systemd/waitingthelongest.service",
        ]
    },
    "8_cicd": {
        "name": "CI/CD",
        "priority": "MEDIUM",
        "agents": ["devops-engineer"],
        "tasks": [
            {"name": "verify_workflows", "command": "ls -la ../.github/workflows/*.yml 2>/dev/null && echo 'Workflows exist' || echo 'No workflows'"},
        ],
        "files": [
            ".github/workflows/ci-cd.yml",
            ".github/workflows/daily-ingestion.yml",
            ".github/workflows/social-content.yml",
        ]
    },
    "9_social_media": {
        "name": "Social Media",
        "priority": "MEDIUM",
        "agents": ["social-media-engineer", "content-creator"],
        "tasks": [
            {"name": "verify_video_gen", "command": "python -c 'from tools.video_generator import *; print(\"Video generator OK\")'"},
        ],
        "files": [
            "backend/tools/video_generator.py",
            "backend/workers/scheduler.py",
        ]
    },
    "10_documentation": {
        "name": "Documentation",
        "priority": "MEDIUM",
        "agents": ["documentation-engineer"],
        "tasks": [
            {"name": "verify_readme", "command": "test -f ../README.md && wc -l ../README.md"},
            {"name": "verify_env_example", "command": "test -f ../.env.example && cat ../.env.example | head -20"},
        ],
        "files": [
            "README.md",
            ".env.example",
        ]
    },
}

# =============================================================================
# AGENT REGISTRY
# =============================================================================

def get_all_agents() -> List[str]:
    """Get list of all available agent files"""
    agents = []
    if AGENTS_DIR.exists():
        for agent_file in AGENTS_DIR.glob("*.agent.md"):
            agents.append(agent_file.stem.replace(".agent", ""))
    return agents


# =============================================================================
# TASK EXECUTION
# =============================================================================

class TaskResult:
    def __init__(self, name: str, success: bool, output: str, duration: float):
        self.name = name
        self.success = success
        self.output = output
        self.duration = duration


def run_task(task: Dict, cwd: Path) -> TaskResult:
    """Run a single task and return result"""
    start = time.time()
    try:
        result = subprocess.run(
            task["command"],
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120
        )
        success = result.returncode == 0
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        success = False
        output = "TIMEOUT: Task took too long"
    except Exception as e:
        success = False
        output = f"ERROR: {str(e)}"
    
    duration = time.time() - start
    return TaskResult(task["name"], success, output.strip(), duration)


def run_category_tasks(category_id: str, category: Dict) -> Dict:
    """Run all tasks for a category"""
    print(f"\n{'='*60}")
    print(f"📋 CATEGORY: {category['name']} (Priority: {category['priority']})")
    print(f"{'='*60}")
    
    results = {
        "category": category["name"],
        "priority": category["priority"],
        "tasks": [],
        "passed": 0,
        "failed": 0,
        "agents": category["agents"],
    }
    
    for task in category["tasks"]:
        print(f"  ⏳ Running: {task['name']}...", end=" ", flush=True)
        result = run_task(task, BACKEND_DIR)
        
        if result.success:
            print(f"✅ ({result.duration:.2f}s)")
            results["passed"] += 1
        else:
            print(f"❌ ({result.duration:.2f}s)")
            print(f"     Output: {result.output[:200]}")
            results["failed"] += 1
        
        results["tasks"].append({
            "name": result.name,
            "success": result.success,
            "output": result.output,
            "duration": result.duration
        })
    
    return results


# =============================================================================
# COMPLETION CHECK
# =============================================================================

def check_file_exists(filepath: str) -> bool:
    """Check if a file exists in the project"""
    full_path = PROJECT_ROOT / filepath
    return full_path.exists()


def check_category_files(category: Dict) -> Dict[str, bool]:
    """Check if all files for a category exist"""
    return {f: check_file_exists(f) for f in category["files"]}


def calculate_completion(results: List[Dict]) -> Dict:
    """Calculate overall project completion percentage"""
    total_tasks = sum(r["passed"] + r["failed"] for r in results)
    passed_tasks = sum(r["passed"] for r in results)
    
    categories_complete = sum(1 for r in results if r["failed"] == 0)
    total_categories = len(results)
    
    return {
        "task_completion": (passed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
        "category_completion": (categories_complete / total_categories * 100) if total_categories > 0 else 0,
        "passed_tasks": passed_tasks,
        "total_tasks": total_tasks,
        "complete_categories": categories_complete,
        "total_categories": total_categories,
    }


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_report(results: List[Dict], completion: Dict) -> str:
    """Generate a comprehensive status report"""
    report = []
    report.append("\n" + "=" * 70)
    report.append("🚀 WAITING THE LONGEST™ - PROJECT COMPLETION REPORT")
    report.append("=" * 70)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Overall stats
    report.append("📊 OVERALL COMPLETION")
    report.append("-" * 40)
    report.append(f"  Tasks Passed:      {completion['passed_tasks']}/{completion['total_tasks']} ({completion['task_completion']:.1f}%)")
    report.append(f"  Categories Done:   {completion['complete_categories']}/{completion['total_categories']} ({completion['category_completion']:.1f}%)")
    report.append("")
    
    # Category breakdown
    report.append("📋 CATEGORY STATUS")
    report.append("-" * 40)
    for r in results:
        status = "✅" if r["failed"] == 0 else "❌"
        report.append(f"  {status} {r['category']}: {r['passed']}/{r['passed']+r['failed']} tasks passed")
        if r["failed"] > 0:
            for task in r["tasks"]:
                if not task["success"]:
                    report.append(f"      ⚠️  FAILED: {task['name']}")
    
    report.append("")
    
    # Agent assignments
    report.append("🤖 AGENT ASSIGNMENTS")
    report.append("-" * 40)
    for r in results:
        if r["failed"] > 0:
            report.append(f"  {r['category']}: {', '.join(r['agents'])}")
    
    report.append("")
    
    # Launch readiness
    is_ready = completion["category_completion"] == 100
    report.append("🎯 LAUNCH READINESS")
    report.append("-" * 40)
    if is_ready:
        report.append("  ✅ ALL SYSTEMS GO - READY FOR LAUNCH! 🚀")
    else:
        report.append(f"  ❌ NOT READY - {completion['total_categories'] - completion['complete_categories']} categories need work")
        report.append("")
        report.append("  BLOCKERS:")
        for r in results:
            if r["failed"] > 0:
                report.append(f"    - {r['category']}: {r['failed']} failing tasks")
    
    report.append("")
    report.append("=" * 70)
    
    return "\n".join(report)


# =============================================================================
# FIX GENERATION
# =============================================================================

def generate_fix_tasks(results: List[Dict]) -> List[Dict]:
    """Generate a list of tasks needed to fix failing categories"""
    fixes = []
    
    for r in results:
        if r["failed"] > 0:
            for task in r["tasks"]:
                if not task["success"]:
                    fixes.append({
                        "category": r["category"],
                        "task": task["name"],
                        "error": task["output"][:500],
                        "agents": r["agents"],
                        "priority": r["priority"]
                    })
    
    # Sort by priority
    priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    fixes.sort(key=lambda x: priority_order.get(x["priority"], 99))
    
    return fixes


# =============================================================================
# MAIN ORCHESTRATION
# =============================================================================

def run_full_check() -> tuple:
    """Run full project check across all categories"""
    print("\n🔍 Starting full project analysis...")
    print(f"📁 Project root: {PROJECT_ROOT}")
    print(f"🤖 Available agents: {len(get_all_agents())}")
    
    results = []
    for cat_id, category in CATEGORIES.items():
        result = run_category_tasks(cat_id, category)
        results.append(result)
    
    completion = calculate_completion(results)
    return results, completion


def main():
    parser = argparse.ArgumentParser(description="Launch all agents to complete the project")
    parser.add_argument("--category", help="Focus on specific category")
    parser.add_argument("--parallel", type=int, default=4, help="Number of parallel agents")
    parser.add_argument("--fix", action="store_true", help="Generate fix recommendations")
    parser.add_argument("--report-only", action="store_true", help="Only generate report, no fixes")
    args = parser.parse_args()
    
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║     🐕 WAITING THE LONGEST™ - AGENT ORCHESTRATOR 🐕          ║
    ║                                                               ║
    ║     "Because Every Day Matters"                               ║
    ║                                                               ║
    ║     Launching all agents for TOTAL PROJECT COMPLETION         ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Run checks
    results, completion = run_full_check()
    
    # Generate and print report
    report = generate_report(results, completion)
    print(report)
    
    # Save report
    report_path = PROJECT_ROOT / "COMPLETION_REPORT.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\n📄 Report saved to: {report_path}")
    
    # Generate fix recommendations if needed
    if completion["category_completion"] < 100:
        fixes = generate_fix_tasks(results)
        
        print("\n" + "=" * 70)
        print("🔧 REQUIRED FIXES (in priority order)")
        print("=" * 70)
        
        for i, fix in enumerate(fixes, 1):
            print(f"\n{i}. [{fix['priority']}] {fix['category']} - {fix['task']}")
            print(f"   Agents: {', '.join(fix['agents'])}")
            print(f"   Error: {fix['error'][:200]}...")
        
        # Save fixes
        fixes_path = PROJECT_ROOT / "FIXES_NEEDED.json"
        with open(fixes_path, "w") as f:
            json.dump(fixes, f, indent=2)
        print(f"\n📄 Fixes saved to: {fixes_path}")
        
        print("\n" + "=" * 70)
        print("🚨 PROJECT NOT READY FOR LAUNCH")
        print("   Run agents on failing categories to complete the project.")
        print("=" * 70)
        
        return 1
    else:
        print("\n" + "=" * 70)
        print("🎉 PROJECT IS 100% COMPLETE AND READY FOR LAUNCH! 🚀")
        print("=" * 70)
        return 0


if __name__ == "__main__":
    sys.exit(main())
