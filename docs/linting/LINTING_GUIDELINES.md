# Linting Guidelines - FlexTraff Backend

## Overview

This project enforces basic linting on **all branches** to maintain code quality. We have multiple layers of linting checks to catch issues early.

## Automated Linting (GitHub Actions)

### 🔍 All Branches Linting
- **Workflow:** `lint-all-branches.yml`
- **Triggers:** Every push and PR to any branch
- **Checks:**
  - Flake8 code quality linting
  - Basic security scan with Bandit
- **Duration:** ~15-20 seconds

### 🚀 Main Branches CI/CD
- **Workflow:** `ci-cd.yml`
- **Triggers:** Push/PR to `main` and `develop` branches
- **Includes:** Full test suite + comprehensive linting

## Local Development Setup

### Option 1: Manual Pre-Push Script (Recommended)

Run before pushing to any branch:

```bash
# Make the script executable (one-time setup)
chmod +x scripts/pre-push-lint.sh

# Run before pushing
./scripts/pre-push-lint.sh
```

### Option 2: Pre-commit Hooks (Automatic)

Install pre-commit hooks to run checks automatically:

```bash
# Install pre-commit
pip install pre-commit

# Install the hooks
pre-commit install

# Now linting runs automatically on each commit
```

### Option 3: Manual Linting Commands

Run individual linting tools:

```bash
# Install linting tools
pip install flake8 bandit

# Run Flake8 linting
flake8 app/ tests/ main.py

# Run security scan
bandit -r app/
```

## Linting Rules

### Consistent Lenient Configuration

We use a **consistent lenient linting configuration** across all environments:

#### 🏠 Local Development & 🚀 GitHub Actions CI/CD
- **Configuration:** `.flake8` file 
- **Max line length:** 120 characters
- **Focus:** Developer-friendly while catching critical errors
- **Ignored rules:** Line length (E501), unused variables (F841), unused imports (F401), complexity (C901), documentation (D100-D105), naming conventions (N801-N806)
- **Purpose:** Reduce friction during development while maintaining essential code quality

### Security Scanning
- **Tool:** Bandit
- **Scope:** `app/` directory only
- **Level:** Medium and high severity issues

### Common Issues to Avoid
- ❌ Debug statements (`pdb.set_trace()`)
- ❌ Unused imports
- ❌ Undefined variables
- ❌ Security vulnerabilities
- ⚠️ Print statements in production code (use logging)

## Workflow Integration

### Branch Protection
1. **Feature branches:** Basic linting check runs on every push
2. **Main/Develop:** Full CI/CD pipeline with tests and comprehensive checks
3. **All branches:** Fast feedback with essential quality checks

### Developer Workflow
```
1. Create feature branch
2. Write code with lenient linting (.flake8)
3. Run ./scripts/pre-push-lint.sh (uses lenient rules)
4. Fix any critical linting issues
5. Push to branch
6. GitHub Actions runs same lenient linting (consistent experience)
7. Create PR (triggers full CI/CD if targeting main/develop)
```

### Why This Approach?
- **Developer Productivity:** Lenient rules reduce friction during development
- **Consistency:** Same linting rules across local and CI/CD environments
- **Early Feedback:** Local linting catches critical issues immediately
- **Focus on Essentials:** Emphasizes critical errors over strict formatting

## Bypassing Linting (Not Recommended)

In rare cases where you need to bypass linting:

```bash
# Skip pre-commit hooks (local only)
git commit --no-verify

# Note: GitHub Actions linting will still run
```

## Troubleshooting

### Common Linting Fixes

**Long lines:**
```python
# Bad
some_very_long_function_call_with_many_parameters(param1, param2, param3, param4, param5)

# Good
some_very_long_function_call_with_many_parameters(
    param1, param2, param3, param4, param5
)
```

**Unused imports:**
```python
# Bad
import os  # unused

# Good - remove unused imports
```

**Security issues:**
```python
# Bad
password = "hardcoded_password"

# Good
password = os.environ.get("PASSWORD")
```

## Benefits

✅ **Early Issue Detection:** Catch problems before they reach main branches  
✅ **Consistent Code Quality:** All code follows the same standards  
✅ **Security Awareness:** Basic security scanning on every push  
✅ **Fast Feedback:** Lightweight checks complete in ~15 seconds  
✅ **Developer Friendly:** Multiple options for local development  

## Support

- **Issues:** Report linting-related issues in GitHub Issues
- **Configuration:** Linting rules are defined in `.pre-commit-config.yaml`
- **Scripts:** Pre-push script located in `scripts/pre-push-lint.sh`