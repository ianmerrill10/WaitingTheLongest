# Waiting The Longest™ - Documentation Requirements

> **Documentation is MANDATORY for all changes**

---

## Overview

This document establishes the documentation requirements for the Waiting The Longest™ project. All contributors must follow these guidelines to ensure the codebase remains well-documented and maintainable.

---

## Documentation Policy

### Rule 1: OWNERS_MANUAL.md Must Be Updated

Every pull request that modifies functionality MUST include updates to `OWNERS_MANUAL.md`.

**What requires documentation updates:**
- New API endpoints
- Modified API behavior or parameters
- New database models or schema changes
- New configuration options or environment variables
- New features or workflows
- Changes to deployment procedures
- Bug fixes that change documented behavior
- Security-related changes

**What does NOT require documentation updates:**
- Minor code refactoring (no behavior change)
- Test file changes only
- Dependency version bumps (unless they change behavior)
- Typo fixes in code comments

### Rule 2: Every Python File Must Have Header Documentation

All Python files must include a header comment block with:
- File purpose
- Author information
- Last updated date
- Dependencies list
- Related files
- IMPORTANT notice: "Any changes to this file MUST be documented in OWNERS_MANUAL.md"

**Template:**
```python
"""
===============================================================================
Waiting The Longest™ - [File Description]
===============================================================================
Purpose: [Describe what this file does]

Author: Waiting The Longest™ Development Team
Last Updated: YYYY-MM-DD
Dependencies: [List key dependencies]
Related Files: [List related files]

IMPORTANT: Any changes to this file MUST be documented in OWNERS_MANUAL.md
===============================================================================
"""
```

### Rule 3: Every Function Must Have a Docstring

All public functions must include:
- Description of purpose
- Args section with parameter descriptions and types
- Returns section with return value description
- Raises section if exceptions are thrown
- Example usage where appropriate

**Template:**
```python
def function_name(param1: str, param2: int) -> bool:
    """
    Brief description of what this function does.
    
    More detailed explanation if needed. Explain the business logic
    and any important considerations.
    
    Args:
        param1: Description of first parameter
        param2: Description of second parameter
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param1 is empty
        DatabaseError: When connection fails
        
    Example:
        >>> result = function_name("test", 42)
        >>> print(result)
        True
    """
```

### Rule 4: Inline Comments for Complex Logic

Any non-obvious code logic should include inline comments explaining:
- WHY the code exists (not just what it does)
- Business rules being implemented
- Edge cases being handled
- Performance considerations

---

## Documentation Checklist for Pull Requests

Before submitting a PR, verify:

- [ ] **OWNERS_MANUAL.md Updated**
  - [ ] Added new sections if needed
  - [ ] Updated existing sections if behavior changed
  - [ ] Updated Changelog section with changes

- [ ] **File Headers**
  - [ ] All new Python files have header documentation
  - [ ] Modified files have updated "Last Updated" date

- [ ] **Function Docstrings**
  - [ ] All new functions have complete docstrings
  - [ ] Modified functions have updated docstrings
  - [ ] Args, Returns, and Raises sections are complete

- [ ] **Inline Comments**
  - [ ] Complex logic is explained
  - [ ] Business rules are documented
  - [ ] Edge cases are noted

- [ ] **Configuration**
  - [ ] New environment variables added to `.env.example`
  - [ ] New config options documented in OWNERS_MANUAL.md

- [ ] **API Changes**
  - [ ] New endpoints documented in API Reference section
  - [ ] Changed endpoints updated in API Reference section
  - [ ] Request/response examples included

---

## Enforcement

### Automated Checks

The CI/CD pipeline includes a documentation validation workflow that:
1. Checks if OWNERS_MANUAL.md was modified when Python files change
2. Verifies all Python files have header documentation
3. Scans for functions missing docstrings

PRs that fail documentation checks will not be merged.

### Manual Review

All PRs must also pass manual review for documentation quality:
- Documentation is clear and accurate
- Examples are helpful and correct
- No outdated information remains

---

## Resources

- **Main Documentation**: [OWNERS_MANUAL.md](/OWNERS_MANUAL.md)
- **API Documentation**: [/api/docs](https://waitingthelongest.com/api/docs)
- **Environment Template**: [.env.example](/.env.example)

---

**"Because Every Day Matters"** - and so does documentation!

*© 2025 Waiting The Longest™*
