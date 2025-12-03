#!/usr/bin/env python3
"""
===============================================================================
Waiting The Longest™ - Documentation Validator
===============================================================================
Purpose: Validates that documentation requirements are met for the codebase.

This script checks:
1. OWNERS_MANUAL.md exists
2. All Python files have header documentation
3. All functions have docstrings
4. Environment variables are documented

Author: Waiting The Longest™ Development Team
Last Updated: 2025-01-15

Usage:
    python documentation_validator.py [--strict] [--fix]
    
Options:
    --strict    Exit with error code on any warning
    --fix       Attempt to add missing header comments (stub only)

IMPORTANT: Any changes to this file MUST be documented in OWNERS_MANUAL.md
===============================================================================
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Tuple, Optional
import argparse


class DocumentationValidator:
    """
    Validates documentation requirements for the Waiting The Longest™ codebase.
    
    This validator checks:
    - OWNERS_MANUAL.md exists and has content
    - Python files have header documentation
    - Functions have docstrings
    - Classes have docstrings
    
    Attributes:
        root_dir: Root directory of the project
        errors: List of critical errors found
        warnings: List of non-critical warnings found
        
    Example:
        >>> validator = DocumentationValidator("/path/to/project")
        >>> success = validator.validate_all()
        >>> print(f"Validation {'passed' if success else 'failed'}")
    """
    
    def __init__(self, root_dir: str = "."):
        """
        Initialize the documentation validator.
        
        Args:
            root_dir: Root directory of the project to validate
        """
        self.root_dir = Path(root_dir).resolve()
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def validate_all(self) -> bool:
        """
        Run all validation checks.
        
        Returns:
            True if all critical checks pass, False otherwise
            
        Raises:
            FileNotFoundError: If root_dir doesn't exist
        """
        print("=" * 60)
        print("Waiting The Longest™ - Documentation Validator")
        print("=" * 60)
        print()
        
        # Check OWNERS_MANUAL.md
        self._check_owners_manual()
        
        # Check Python files
        self._check_python_files()
        
        # Check environment variables documentation
        self._check_env_documentation()
        
        # Report results
        self._report_results()
        
        return len(self.errors) == 0
    
    def _check_owners_manual(self) -> None:
        """
        Verify OWNERS_MANUAL.md exists and has content.
        
        Adds an error if the file is missing or empty.
        """
        manual_path = self.root_dir / "OWNERS_MANUAL.md"
        
        if not manual_path.exists():
            self.errors.append("OWNERS_MANUAL.md does not exist!")
            return
            
        content = manual_path.read_text()
        
        if len(content) < 100:
            self.errors.append("OWNERS_MANUAL.md appears to be empty or too short")
            return
            
        # Check for required sections
        required_sections = [
            "Project Overview",
            "API Endpoint",
            "Database",
            "Deployment",
            "Troubleshooting",
        ]
        
        for section in required_sections:
            if section.lower() not in content.lower():
                self.warnings.append(f"OWNERS_MANUAL.md may be missing section: {section}")
        
        print("✓ OWNERS_MANUAL.md exists and has content")
    
    def _check_python_files(self) -> None:
        """
        Check all Python files for proper documentation.
        
        Validates:
        - Header documentation (module docstring)
        - Function docstrings
        - Class docstrings
        """
        backend_dir = self.root_dir / "backend"
        
        if not backend_dir.exists():
            self.warnings.append("backend directory not found")
            return
            
        python_files = list(backend_dir.rglob("*.py"))
        
        # Exclude test files and __pycache__
        python_files = [
            f for f in python_files 
            if "__pycache__" not in str(f) 
            and not f.name.startswith("test_")
            and f.name != "__init__.py"
        ]
        
        print(f"\nChecking {len(python_files)} Python files...")
        
        for py_file in python_files:
            self._validate_python_file(py_file)
    
    def _validate_python_file(self, file_path: Path) -> None:
        """
        Validate a single Python file for documentation.
        
        Args:
            file_path: Path to the Python file to validate
        """
        relative_path = file_path.relative_to(self.root_dir)
        
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
        except SyntaxError as e:
            self.errors.append(f"{relative_path}: Syntax error - {e}")
            return
        except Exception as e:
            self.warnings.append(f"{relative_path}: Could not parse - {e}")
            return
        
        # Check for module docstring
        if not ast.get_docstring(tree):
            self.warnings.append(f"{relative_path}: Missing module docstring (header documentation)")
        
        # Check functions and classes
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Skip private functions (starting with _)
                if not node.name.startswith("_"):
                    if not ast.get_docstring(node):
                        self.warnings.append(
                            f"{relative_path}:{node.lineno}: Function '{node.name}' missing docstring"
                        )
                        
            elif isinstance(node, ast.ClassDef):
                if not ast.get_docstring(node):
                    self.warnings.append(
                        f"{relative_path}:{node.lineno}: Class '{node.name}' missing docstring"
                    )
    
    def _check_env_documentation(self) -> None:
        """
        Verify environment variables are documented.
        
        Checks that .env.example exists and has content.
        """
        env_example = self.root_dir / ".env.example"
        
        if not env_example.exists():
            self.warnings.append(".env.example does not exist")
            return
            
        content = env_example.read_text()
        
        if len(content) < 50:
            self.warnings.append(".env.example appears to be empty")
            return
            
        print("✓ .env.example exists and has content")
    
    def _report_results(self) -> None:
        """
        Print validation results summary.
        """
        print()
        print("=" * 60)
        print("VALIDATION RESULTS")
        print("=" * 60)
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"   • {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings[:20]:  # Limit to first 20
                print(f"   • {warning}")
            if len(self.warnings) > 20:
                print(f"   ... and {len(self.warnings) - 20} more warnings")
        
        print()
        
        if not self.errors and not self.warnings:
            print("✅ All documentation checks passed!")
        elif not self.errors:
            print("✅ No critical errors, but please address warnings.")
        else:
            print("❌ Documentation validation FAILED. Please fix errors above.")


def main():
    """
    Main entry point for the documentation validator.
    
    Parses command-line arguments and runs validation.
    
    Returns:
        Exit code: 0 for success, 1 for failure
    """
    parser = argparse.ArgumentParser(
        description="Validate documentation for Waiting The Longest™"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors"
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Project root directory"
    )
    
    args = parser.parse_args()
    
    # Find project root (look for OWNERS_MANUAL.md or .git)
    root_dir = Path(args.root).resolve()
    
    # Try to find project root by looking for key files
    if not (root_dir / "backend").exists():
        # Try parent directories
        for parent in root_dir.parents:
            if (parent / "backend").exists():
                root_dir = parent
                break
    
    validator = DocumentationValidator(str(root_dir))
    success = validator.validate_all()
    
    if args.strict and validator.warnings:
        print("\n--strict mode: Treating warnings as errors")
        success = False
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
