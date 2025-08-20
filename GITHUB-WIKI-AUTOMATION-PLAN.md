# GitHub Wiki Automation Plan

## Overview

Implementation plan for automating Kasa Monitor wiki documentation using the GitHub Wiki Action to sync our `/wiki/` folder with the GitHub repository wiki.

## Current State

- **Local Wiki Folder**: `/wiki/` contains 28+ markdown files
- **Documentation Quality**: High-quality, recently updated documentation
- **Sync Status**: Manual sync required between local files and GitHub wiki
- **Recent Updates**: Major documentation fixes completed

## GitHub Wiki Action Benefits

### ✅ **Advantages**
- **Automatic Sync**: Push to `/wiki/` folder automatically updates GitHub wiki
- **Version Control**: Wiki content managed in main repository with full git history
- **Workflow Integration**: Fits into existing CI/CD pipeline
- **Multiple Formats**: Supports various markdown files and structures
- **Cross-Repository**: Can publish to different repository wikis if needed

### ⚠️ **Considerations**
- **Initial Setup**: Requires manual creation of initial wiki page
- **Preprocessing**: May modify markdown links during sync
- **Permissions**: Needs write access to repository

## Implementation Plan

### **Phase 1: Preparation (Week 1)**

#### **1.1 Repository Setup**
```bash
# Verify current wiki structure
ls -la wiki/
├── API-Documentation.md
├── Architecture-Overview.md
├── Audit-Logging.md
├── Backup-Recovery.md
├── Data-Export-System.md
├── Plugin-Development.md
├── Security-Guide.md
├── User-Management.md
└── ... (20+ more files)
```

#### **1.2 GitHub Wiki Initialization**
1. **Manual Step**: Create initial wiki page on GitHub
   - Navigate to repository Settings → Features → Wiki
   - Enable wiki and create initial "Home" page
   - This satisfies the action's requirement for existing wiki

#### **1.3 Documentation Cleanup**
```bash
# Ensure all files follow naming conventions
- Use kebab-case for filenames
- Ensure .md extensions
- Verify internal links work
- Check for special characters in filenames
```

### **Phase 2: Workflow Creation (Week 1)**

#### **2.1 Basic Wiki Sync Workflow**

Create `.github/workflows/wiki-sync.yml`:

```yaml
name: Sync Wiki Documentation

on:
  push:
    branches: [main]
    paths:
      - 'wiki/**'
      - 'DOCUMENTATION-ANALYSIS.md'
      - 'WIKI-CHANGES-SUMMARY.md'
  pull_request:
    branches: [main]
    paths:
      - 'wiki/**'
  workflow_dispatch:  # Manual trigger

permissions:
  contents: write

jobs:
  sync-wiki:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'  # Only sync from main branch
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for better wiki commits
      
      - name: Validate wiki files
        run: |
          echo "Validating wiki documentation..."
          # Check for required files
          if [[ ! -f "wiki/Home.md" ]]; then
            echo "Error: Home.md is required for wiki"
            exit 1
          fi
          
          # Check for broken internal links (basic check)
          find wiki/ -name "*.md" -exec grep -l "\[\[.*\]\]" {} \; | while read file; do
            echo "Warning: $file contains wiki-style links that may need conversion"
          done
          
          echo "Wiki validation complete"
      
      - name: Sync to GitHub Wiki
        uses: Andrew-Chen-Wang/github-wiki-action@v4
        with:
          repository: ${{ github.repository }}
          token: ${{ secrets.GITHUB_TOKEN }}
          path: wiki/
          strategy: clone  # Incremental commits
          preprocess: true  # Convert links and rename README
          dry-run: false
```

#### **2.2 Enhanced Workflow with Quality Checks**

Create `.github/workflows/wiki-quality.yml`:

```yaml
name: Wiki Quality Assurance

on:
  pull_request:
    paths:
      - 'wiki/**'
  workflow_dispatch:

jobs:
  quality-check:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
      
      - name: Install markdown linter
        run: |
          npm install -g markdownlint-cli
          npm install -g markdown-link-check
      
      - name: Lint markdown files
        run: |
          markdownlint wiki/**/*.md --config .markdownlint.json || true
      
      - name: Check internal links
        run: |
          find wiki/ -name "*.md" -exec markdown-link-check {} \; || true
      
      - name: Validate documentation completeness
        run: |
          echo "Checking for required documentation sections..."
          
          # Check API documentation exists
          if [[ ! -f "wiki/API-Documentation.md" ]]; then
            echo "Error: API-Documentation.md is required"
            exit 1
          fi
          
          # Check security guide exists
          if [[ ! -f "wiki/Security-Guide.md" ]]; then
            echo "Error: Security-Guide.md is required"
            exit 1
          fi
          
          echo "Documentation completeness check passed"
      
      - name: Generate documentation report
        run: |
          echo "# Documentation Report" > wiki-report.md
          echo "Generated: $(date)" >> wiki-report.md
          echo "" >> wiki-report.md
          echo "## Files in wiki/" >> wiki-report.md
          find wiki/ -name "*.md" | wc -l | xargs echo "Total markdown files:" >> wiki-report.md
          echo "" >> wiki-report.md
          echo "## File List" >> wiki-report.md
          find wiki/ -name "*.md" | sort >> wiki-report.md
      
      - name: Upload documentation report
        uses: actions/upload-artifact@v4
        with:
          name: documentation-report
          path: wiki-report.md
```

### **Phase 3: Advanced Features (Week 2)**

#### **3.1 Documentation Generation Integration**

Add to existing workflow or create `.github/workflows/doc-generation.yml`:

```yaml
name: Documentation Generation

on:
  push:
    branches: [main]
    paths:
      - 'backend/**/*.py'
      - 'src/**/*.tsx'
      - 'src/**/*.ts'

jobs:
  generate-docs:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Generate API documentation
        run: |
          pip install fastapi[all]
          cd backend
          python -c "
          from server import app
          import json
          
          # Generate OpenAPI spec
          openapi_spec = app.openapi()
          with open('../wiki/API-Specification.json', 'w') as f:
              json.dump(openapi_spec, f, indent=2)
          "
      
      - name: Update implementation status
        run: |
          echo "# Implementation Status" > wiki/Implementation-Status.md
          echo "Auto-generated: $(date)" >> wiki/Implementation-Status.md
          echo "" >> wiki/Implementation-Status.md
          
          # Count implemented endpoints
          grep -r "@.*\.(get\|post\|put\|delete)" backend/ | wc -l | xargs echo "Implemented API endpoints:" >> wiki/Implementation-Status.md
          
          # List recent features
          echo "" >> wiki/Implementation-Status.md
          echo "## Recent Features" >> wiki/Implementation-Status.md
          git log --oneline --since="1 month ago" --grep="feat\|add\|implement" >> wiki/Implementation-Status.md
      
      - name: Commit generated documentation
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add wiki/
          git diff --staged --quiet || git commit -m "Update auto-generated documentation"
          git push
```

#### **3.2 Scheduled Documentation Maintenance**

Create `.github/workflows/wiki-maintenance.yml`:

```yaml
name: Wiki Maintenance

on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday at 2 AM
  workflow_dispatch:

jobs:
  maintenance:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Check for outdated documentation
        run: |
          echo "Checking for outdated documentation..."
          
          # Find files not updated in 6 months
          find wiki/ -name "*.md" -not -newermt "6 months ago" > outdated-docs.txt
          
          if [[ -s outdated-docs.txt ]]; then
            echo "Warning: The following documentation may be outdated:"
            cat outdated-docs.txt
          fi
      
      - name: Validate cross-references
        run: |
          echo "Checking cross-references between wiki pages..."
          
          # Extract all markdown links
          grep -r "\[.*\](.*.md)" wiki/ | while IFS: read -r file link; do
            target=$(echo "$link" | sed -n 's/.*(\(.*\.md\)).*/\1/p')
            if [[ ! -f "wiki/$target" ]]; then
              echo "Warning: Broken link in $file -> $target"
            fi
          done
      
      - name: Generate wiki statistics
        run: |
          echo "# Wiki Statistics" > wiki-stats.md
          echo "Generated: $(date)" >> wiki-stats.md
          echo "" >> wiki-stats.md
          
          find wiki/ -name "*.md" | wc -l | xargs echo "Total pages:" >> wiki-stats.md
          find wiki/ -name "*.md" -exec wc -w {} + | tail -1 | awk '{print $1}' | xargs echo "Total words:" >> wiki-stats.md
          
          echo "" >> wiki-stats.md
          echo "## Recent Updates" >> wiki-stats.md
          git log --oneline --since="1 month ago" -- wiki/ >> wiki-stats.md
      
      - name: Create maintenance issue if needed
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            
            if (fs.existsSync('outdated-docs.txt') && fs.statSync('outdated-docs.txt').size > 0) {
              const outdatedFiles = fs.readFileSync('outdated-docs.txt', 'utf8');
              
              await github.rest.issues.create({
                owner: context.repo.owner,
                repo: context.repo.repo,
                title: 'Documentation Maintenance Required',
                body: `Automated check found potentially outdated documentation:
                
                ${outdatedFiles}
                
                Please review and update these files as needed.`,
                labels: ['documentation', 'maintenance']
              });
            }
```

### **Phase 4: Integration with Development Workflow**

#### **4.1 Documentation Review in PR Process**

Update `.github/workflows/pr-checks.yml` (or create if doesn't exist):

```yaml
name: Pull Request Checks

on:
  pull_request:
    branches: [main]

jobs:
  documentation-check:
    runs-on: ubuntu-latest
    if: contains(github.event.pull_request.changed_files, 'wiki/') || contains(github.event.pull_request.changed_files, 'backend/') || contains(github.event.pull_request.changed_files, 'src/')
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Check if documentation needs updates
        run: |
          echo "Checking if code changes require documentation updates..."
          
          # Check for new API endpoints
          git diff origin/main..HEAD -- backend/ | grep -E "@.*\.(get|post|put|delete)" && {
            echo "Warning: New API endpoints detected. Please update API documentation."
            echo "::warning::Consider updating wiki/API-Documentation.md"
          } || true
          
          # Check for new features
          git diff origin/main..HEAD --name-only | grep -E "(feature|feat)" && {
            echo "Warning: New features detected. Please update relevant documentation."
            echo "::warning::Consider updating relevant wiki pages"
          } || true
      
      - name: Validate documentation changes
        if: contains(github.event.pull_request.changed_files, 'wiki/')
        run: |
          echo "Validating documentation changes..."
          
          # Run the technical documentation specialist check
          echo "Documentation changes detected - ensuring quality standards"
          
          # Check for common issues
          changed_files=$(git diff --name-only origin/main..HEAD -- wiki/)
          for file in $changed_files; do
            if [[ -f "$file" ]]; then
              # Check for TODO or FIXME comments
              grep -n "TODO\|FIXME" "$file" && {
                echo "::warning::$file contains TODO/FIXME comments"
              } || true
              
              # Check for placeholder text
              grep -n "INSERT\|PLACEHOLDER\|TBD" "$file" && {
                echo "::error::$file contains placeholder text"
                exit 1
              } || true
            fi
          done
```

#### **4.2 Post-Merge Documentation Sync**

Add to the main wiki sync workflow:

```yaml
  post-merge-sync:
    runs-on: ubuntu-latest
    needs: [sync-wiki]
    if: github.ref == 'refs/heads/main'
    
    steps:
      - name: Notify successful sync
        uses: actions/github-script@v7
        with:
          script: |
            const { owner, repo } = context.repo;
            const sha = context.sha;
            
            // Create a check run to indicate wiki sync completion
            await github.rest.checks.create({
              owner,
              repo,
              name: 'Wiki Documentation Sync',
              head_sha: sha,
              status: 'completed',
              conclusion: 'success',
              output: {
                title: 'Wiki Updated Successfully',
                summary: 'Documentation has been synced to GitHub Wiki'
              }
            });
      
      - name: Update documentation index
        run: |
          echo "Updating documentation index..."
          # This could trigger other downstream processes
          curl -X POST "${{ secrets.WEBHOOK_URL }}" \
            -H "Content-Type: application/json" \
            -d '{"event": "wiki_updated", "repository": "${{ github.repository }}", "commit": "${{ github.sha }}"}' || true
```

## Configuration Files

### **Markdown Linting Configuration**

Create `.markdownlint.json`:

```json
{
  "MD013": {
    "line_length": 120,
    "tables": false,
    "code_blocks": false
  },
  "MD033": false,
  "MD041": false,
  "MD024": {
    "allow_different_nesting": true
  }
}
```

### **Git Attributes**

Create `.gitattributes` (if not exists) and add:

```
wiki/*.md text eol=lf
*.md text eol=lf
```

## Testing Strategy

### **Phase 1: Testing**

1. **Create Test Branch**:
   ```bash
   git checkout -b test-wiki-automation
   ```

2. **Test Wiki Sync**:
   ```bash
   # Make small change to wiki
   echo "Test update $(date)" >> wiki/Home.md
   git add wiki/Home.md
   git commit -m "test: wiki automation"
   git push origin test-wiki-automation
   ```

3. **Verify Workflow**:
   - Check GitHub Actions tab
   - Verify wiki was updated
   - Test dry-run mode first

### **Phase 2: Production Deployment**

1. **Merge to Main**:
   ```bash
   git checkout main
   git merge test-wiki-automation
   git push origin main
   ```

2. **Monitor Initial Sync**:
   - Watch GitHub Actions execution
   - Verify all wiki pages sync correctly
   - Check for any link conversion issues

## Benefits and ROI

### **Immediate Benefits**
- ✅ **Automated Sync**: No more manual wiki updates
- ✅ **Version Control**: Full git history for documentation
- ✅ **Quality Assurance**: Automated checks and validation
- ✅ **Consistency**: Single source of truth in repository

### **Long-term Benefits**
- 📈 **Improved Documentation Quality**: Continuous validation
- 🔄 **Reduced Maintenance**: Automated outdated content detection
- 🚀 **Better Developer Experience**: Documentation in main workflow
- 📊 **Analytics**: Track documentation usage and updates

## Risk Mitigation

### **Potential Issues and Solutions**

1. **Link Conversion Problems**:
   - **Risk**: GitHub wiki links may break
   - **Solution**: Test thoroughly, use preprocess option carefully

2. **Large Files**:
   - **Risk**: Wiki sync may fail with large files
   - **Solution**: Use `.gitignore` for large assets, link to releases

3. **Permissions Issues**:
   - **Risk**: Action may fail due to insufficient permissions
   - **Solution**: Ensure `contents: write` permission is set

4. **Sync Conflicts**:
   - **Risk**: Manual wiki edits may conflict
   - **Solution**: Establish policy for repository-first editing

## Success Metrics

### **Quality Metrics**
- Documentation sync success rate: >99%
- Broken link detection: 100% coverage
- Outdated content alerts: Weekly reports

### **Developer Experience Metrics**
- Time to update documentation: 50% reduction
- Documentation consistency: 100% accuracy
- Developer satisfaction: Survey feedback

## Timeline

| Week | Phase | Activities |
|------|-------|------------|
| 1 | Setup | Repository preparation, workflow creation |
| 2 | Testing | Test branch validation, quality checks |
| 3 | Deployment | Production deployment, monitoring |
| 4 | Optimization | Performance tuning, feature enhancement |

## Conclusion

Implementing the GitHub Wiki Action will significantly improve our documentation workflow by:

1. **Automating** the sync between repository and GitHub wiki
2. **Ensuring** documentation quality through automated checks
3. **Maintaining** consistency between code and documentation
4. **Reducing** manual maintenance overhead

The implementation follows a phased approach with proper testing and risk mitigation, ensuring a smooth transition to automated documentation management.

---

*Implementation plan created: August 20, 2025*