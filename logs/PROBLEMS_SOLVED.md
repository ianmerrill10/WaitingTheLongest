# Problems Solved Log

This file documents issues encountered and how they were resolved.

---

## 2025-12-11

### Problem: Multiple Project Versions Causing Confusion

**Symptom**: Developer had multiple folders with different versions of the project:
- WaitingTheLongest/ (git repo)
- aistudiobuildDec5Restart/ (zip file)
- shelter finder mini app/RescueScout/ (empty)
- Various data folders

**Cause**: Multiple development attempts using different tools (GitHub Copilot, AI Studio, ChatGPT)

**Solution**:
1. Analyzed each version to understand completeness
2. Identified `WaitingTheLongest/shelter-registry-backup` as most complete
3. Merged valuable data from other sources
4. Created consolidated `main` branch
5. Set up logging system to track future work

**Resolution**: Project now has single authoritative `main` branch

---

### Problem: Git Merge Conflicts When Switching Branches

**Symptom**: Attempting to checkout GitHub default branch resulted in merge conflicts

**Cause**: Local `shelter-registry-backup` branch had diverged significantly from GitHub default branch

**Solution**:
1. Aborted the merge
2. Did fresh clone to separate folder
3. Copied needed files manually instead of merging
4. Kept local branch as base, added missing data

**Resolution**: No merge needed - manual file copy preserved both sets of work

---

## Previous Problems (Before 2025-12-11)

### CSS Inline Styles (Fixed 2025-12-07)
- Added utility classes to `styles.css` for all inline styles
- Classes: `.auth-section`, `.user-menu`, `.max-width-*`, `.text-*`, `.mt-*`, `.mb-*`, etc.

### CSS Browser Compatibility (Fixed 2025-12-07)
- Added `text-size-adjust: 100%;` to `styles.css`

See `PROJECT_CONTEXT.md` for additional historical issues.
