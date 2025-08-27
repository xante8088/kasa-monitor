# Commit Guidelines for Kasa Monitor

## When to Use [docker-build] Tag

### ✅ ALWAYS Include [docker-build] When Committing:

**Backend Changes:**
- Python files in `/backend/**`
- Requirements.txt updates
- Database schema changes
- API endpoint modifications
- Security fixes in backend code
- Authentication/authorization changes

**Frontend Changes:**
- React components in `/src/**`
- TypeScript/JavaScript files
- CSS/styling updates
- Package.json or package-lock.json changes
- Public assets updates
- Build configuration changes

**Docker/Deployment Changes:**
- Dockerfile modifications
- Docker-compose.yml updates
- Environment variable changes
- Port or networking changes

### ❌ DO NOT Include [docker-build] When Committing:

**Documentation Only:**
- README updates
- Wiki changes (*.md files)
- Comments or docstrings only
- LICENSE changes

**GitHub Workflows Only:**
- .github/workflows/* changes (unless they affect the build)
- GitHub Actions configuration
- CI/CD pipeline modifications

**Development Tools:**
- .gitignore updates
- ESLint/Prettier config
- IDE settings (.vscode, .idea)
- Development scripts that don't affect production

**Tests Only:**
- Test file updates without source changes
- Test configuration
- Mock data updates

## Commit Message Examples

### With [docker-build]:
```bash
# Backend changes
git commit -m "fix: correct authentication token validation [docker-build]"
git commit -m "feat: add new energy monitoring endpoint [docker-build]"
git commit -m "security: patch SQL injection vulnerability [docker-build]"

# Frontend changes  
git commit -m "fix: resolve chart rendering issue [docker-build]"
git commit -m "feat: add time period selectors to dashboard [docker-build]"
git commit -m "fix: correct TypeScript type errors [docker-build]"

# Critical fixes
git commit -m "fix: resolve memory leak in device polling [docker-build]"
git commit -m "perf: optimize database queries [docker-build]"
```

### Without [docker-build]:
```bash
# Documentation
git commit -m "docs: update installation instructions"
git commit -m "docs: add troubleshooting guide"

# Workflows
git commit -m "ci: fix GitHub Actions syntax error"
git commit -m "ci: add security scanning workflow"

# Development tools
git commit -m "chore: update .gitignore"
git commit -m "chore: configure prettier rules"

# Tests only
git commit -m "test: add unit tests for auth module"
git commit -m "test: update mock data"
```

## Quick Decision Tree

```
Is it a source code change?
├─ Yes → Does it affect the running application?
│   ├─ Yes → ✅ Add [docker-build]
│   └─ No → ❌ Don't add [docker-build]
└─ No → Is it a Dockerfile or dependency change?
    ├─ Yes → ✅ Add [docker-build]
    └─ No → ❌ Don't add [docker-build]
```

## Special Cases

### Hotfixes
For critical production fixes that need immediate deployment:
```bash
git commit -m "fix: critical security patch for XSS vulnerability [docker-build]"
```

### Multiple Changes
If commit includes both code and non-code changes, include tag:
```bash
git commit -m "fix: update API endpoint and documentation [docker-build]"
```

### Dependency Updates
Security updates or major dependency changes:
```bash
git commit -m "fix(deps): update vulnerable packages [docker-build]"
```

## Automation Note

The CI/CD pipeline will automatically build Docker images when:
1. Commit message contains `[docker-build]` tag
2. Semantic release creates a new version (feat/fix/perf commits)
3. Manual trigger via GitHub Actions UI

## Benefits

- **Efficiency**: Avoids unnecessary Docker builds for non-code changes
- **Cost Savings**: Reduces CI/CD minutes and Docker Hub storage
- **Clarity**: Makes it clear which commits result in new deployable versions
- **Control**: Gives developers explicit control over when builds occur

---

**Remember**: When in doubt about whether a change needs a Docker build, it's better to include `[docker-build]` to ensure the latest code is deployed.