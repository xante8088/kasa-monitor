# Code Quality Validation Scripts

This directory contains scripts to ensure code quality and prevent issues from being pushed to the repository.

## Scripts Overview

### 🔍 `validate-code.sh`
**Main validation script** - Comprehensive code quality checks for the backend Python code.

**What it checks:**
- ✅ **Import sorting** (using `isort` - auto-fixes issues)
- ❌ **Critical linting errors** (using `flake8` - blocks push)
- ⚠️ **Security issues** (hardcoded passwords, SQL injection patterns)
- 📝 **TODO/FIXME comments** (tracking technical debt)
- 🔐 **File permissions** (prevents world-writable files)

**Usage:**
```bash
./scripts/validate-code.sh
```

### 🛠️ `pre-commit-check.sh`
**Manual pre-commit validation** - Run before committing to catch issues early.

**Features:**
- Runs all validation checks
- Checks commit message length
- Detects large files that shouldn't be in git
- Provides detailed feedback

**Usage:**
```bash
./scripts/pre-commit-check.sh
```

## Automatic Validation

### Git Pre-Push Hook
A Git hook is automatically installed at `.git/hooks/pre-push` that:
- ⛔ **Blocks pushes** with critical linting errors
- ✅ **Allows pushes** with only warnings
- 🚀 **Auto-fixes** import sorting issues

**To bypass validation** (not recommended):
```bash
git push --no-verify
```

## Validation Rules

### Critical Errors (Block Push)
- `E9xx` - Runtime errors
- `F63x` - Invalid syntax
- `F7xx` - Logic errors  
- `F82x` - Undefined names

### Non-Critical Issues (Warnings Only)
- `F401` - Unused imports
- `F841` - Unused variables
- `E501` - Line too long
- `W503` - Line break before binary operator

### Security Checks
- 🔍 **Hardcoded passwords** - Patterns like `password =`
- 🔍 **SQL injection** - f-strings with SQL keywords
- 🔍 **File permissions** - World-writable Python files

## Configuration

### Flake8 Settings
```bash
--max-line-length=88
--extend-ignore=E203,W503,F401,F841,E501
```

### Import Sorting
Uses `isort` with default configuration for automatic import organization.

## Best Practices

1. **Run validation locally** before pushing:
   ```bash
   ./scripts/pre-commit-check.sh
   ```

2. **Fix critical errors immediately** - they will block pushes

3. **Address security warnings** - even if they don't block pushes

4. **Keep TODO comments manageable** - consider creating issues for large tasks

5. **Use proper file permissions** - avoid world-writable files

## Troubleshooting

### "Command not found" errors
Install required Python packages:
```bash
pip install flake8 isort
```

### Permission denied
Make scripts executable:
```bash
chmod +x scripts/*.sh
```

### Hook not working
Reinstall the pre-push hook:
```bash
cp scripts/validate-code.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

## Integration with CI/CD

These scripts can be integrated into CI/CD pipelines:
```yaml
# GitHub Actions example
- name: Validate Code Quality
  run: ./scripts/validate-code.sh
```

This ensures code quality is maintained across all development workflows.