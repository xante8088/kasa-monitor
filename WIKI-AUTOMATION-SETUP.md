# GitHub Wiki Automation Setup Guide

## Overview

This guide provides complete instructions for setting up and using the GitHub Wiki automation system for Kasa Monitor. The automation ensures your `/wiki/` folder stays synchronized with your GitHub repository wiki.

## Implementation Status

✅ **Completed Components:**
- Core wiki sync workflow (`wiki-sync.yml`)
- Documentation quality workflow (`wiki-quality.yml`)
- PR documentation checks (`pr-doc-checks.yml`)
- Weekly maintenance workflow (`wiki-maintenance.yml`)
- Test workflow (`test-wiki-sync.yml`)
- Markdown linting configuration (`.markdownlint.json`)
- Git attributes configuration (`.gitattributes`)

## Prerequisites

### 1. Enable GitHub Wiki

Before using the automation, you must manually enable the wiki in your repository:

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Features**
3. Check the **Wiki** checkbox
4. Click **Save**
5. Create an initial wiki page (GitHub requirement):
   - Click on the **Wiki** tab
   - Click **Create the first page**
   - Enter any content (it will be replaced by automation)
   - Save the page

### 2. Repository Permissions

Ensure your repository has the correct permissions:
- The workflows use `GITHUB_TOKEN` which has write access by default
- No additional secrets or tokens are required

## Quick Start

### Step 1: Test the Setup

Run the test workflow to verify everything is configured correctly:

1. Go to **Actions** tab in your repository
2. Select **Test Wiki Sync** workflow
3. Click **Run workflow**
4. Choose test mode:
   - `dry-run`: Safe test without any changes
   - `validate-only`: Only validates structure
   - `full-test`: Complete test including linting

### Step 2: Initial Wiki Sync

After successful testing:

1. Go to **Actions** → **Sync Wiki Documentation**
2. Click **Run workflow**
3. Set `dry_run` to `false` for actual sync
4. Click **Run workflow**

The workflow will:
- Validate all wiki files
- Check for broken links
- Sync your `/wiki/` folder to GitHub Wiki
- Create a status check

### Step 3: Verify the Sync

1. Navigate to your repository's Wiki tab
2. Verify all documentation files are present
3. Check that links work correctly
4. Review the formatting

## Workflows Overview

### 1. **Wiki Sync Workflow** (`wiki-sync.yml`)

**Purpose:** Automatically syncs `/wiki/` folder to GitHub Wiki

**Triggers:**
- Push to `main` branch with changes to `wiki/**`
- Pull requests affecting wiki files
- Manual trigger with dry-run option

**Features:**
- Validates documentation structure
- Checks for required files (Home.md)
- Detects broken internal links
- Identifies placeholder content
- Supports dry-run mode for testing

### 2. **Wiki Quality Workflow** (`wiki-quality.yml`)

**Purpose:** Ensures documentation quality standards

**Triggers:**
- Pull requests with wiki changes
- Manual trigger with report generation

**Features:**
- Markdown linting
- Link validation
- Completeness checks
- Placeholder detection
- Generates quality reports
- Comments on PRs with results

### 3. **PR Documentation Checks** (`pr-doc-checks.yml`)

**Purpose:** Ensures code changes have appropriate documentation

**Triggers:**
- All pull requests to main branch

**Features:**
- Analyzes code changes for documentation impact
- Detects new API endpoints
- Identifies feature additions
- Checks for breaking changes
- Creates documentation checklist
- Comments on PR with requirements

### 4. **Wiki Maintenance** (`wiki-maintenance.yml`)

**Purpose:** Weekly documentation health checks

**Schedule:**
- Every Monday at 2 AM UTC
- Manual trigger available

**Features:**
- Identifies outdated documentation (>90 and >180 days)
- Validates cross-references between pages
- Checks external links
- Analyzes documentation coverage
- Generates statistics report
- Creates GitHub issues for problems

### 5. **Test Wiki Sync** (`test-wiki-sync.yml`)

**Purpose:** Test the wiki automation setup

**Triggers:**
- Manual only

**Test Modes:**
- `dry-run`: Full test without changes
- `validate-only`: Structure validation only
- `full-test`: Complete test with linting

## Manual Triggers

### Sync Wiki Manually

```bash
# Using GitHub CLI
gh workflow run wiki-sync.yml -f dry_run=false

# Using GitHub UI
1. Go to Actions tab
2. Select "Sync Wiki Documentation"
3. Click "Run workflow"
4. Choose options and run
```

### Run Quality Check

```bash
# Using GitHub CLI
gh workflow run wiki-quality.yml -f generate_report=true

# Using GitHub UI
1. Go to Actions tab
2. Select "Wiki Quality Assurance"
3. Click "Run workflow"
4. Enable report generation
```

### Run Maintenance Check

```bash
# Using GitHub CLI
gh workflow run wiki-maintenance.yml -f create_issues=true

# Using GitHub UI
1. Go to Actions tab
2. Select "Wiki Maintenance"
3. Click "Run workflow"
4. Choose to create issues
```

## Configuration

### Markdown Linting Rules

The `.markdownlint.json` file configures linting rules:

- Line length: 120 characters (except tables and code)
- Allows HTML in markdown
- Requires consistent heading styles
- Enforces proper list formatting

To customize, edit `.markdownlint.json`

### Git Attributes

The `.gitattributes` file ensures:

- Consistent line endings (LF) for all text files
- Proper handling of binary files
- Markdown files always use LF endings

## Troubleshooting

### Issue: Wiki sync fails with "Wiki not found"

**Solution:** Ensure you've created an initial wiki page manually (see Prerequisites)

### Issue: "Permission denied" errors

**Solution:** Check repository settings:
1. Settings → Actions → General
2. Workflow permissions → Read and write permissions
3. Save changes

### Issue: Links broken after sync

**Solution:** The automation converts wiki-style links `[[Page]]` to markdown links. Update your documentation to use standard markdown link format: `[Page](Page.md)`

### Issue: Dry run succeeds but actual sync fails

**Solution:** 
1. Verify wiki is enabled in repository settings
2. Check that Home.md exists in wiki/ folder
3. Ensure no special characters in filenames

### Issue: Quality checks fail on valid markdown

**Solution:** Review `.markdownlint.json` configuration and adjust rules as needed for your documentation style

## Best Practices

### Documentation Structure

1. **Always include Home.md** - Required by GitHub Wiki
2. **Use descriptive filenames** - They become wiki page titles
3. **Avoid special characters** - Use hyphens instead of spaces
4. **Maintain consistent formatting** - Follow markdownlint rules

### Link Management

1. **Use relative links** for internal documentation
2. **Test links locally** before pushing
3. **Avoid hardcoding URLs** when possible
4. **Update links** when renaming files

### Workflow Usage

1. **Test changes** with dry-run before syncing
2. **Review quality reports** in pull requests
3. **Address maintenance issues** promptly
4. **Monitor weekly reports** for documentation health

### Documentation Updates

1. **Update documentation with code changes** - Especially API changes
2. **Remove outdated content** - Don't just add new content
3. **Fix placeholders** - Replace TODO/FIXME items
4. **Keep examples current** - Update code samples

## Integration with Documentation Review Process

As the Technical Documentation Specialist, you can integrate these workflows into your review process:

### After Documentation Review

1. **Run quality check** to validate your changes:
   ```bash
   gh workflow run wiki-quality.yml
   ```

2. **Sync to wiki** after approval:
   ```bash
   gh workflow run wiki-sync.yml -f dry_run=false
   ```

3. **Monitor maintenance** reports weekly

### During Pull Request Review

1. Check the automated PR comment for documentation requirements
2. Ensure all checklist items are addressed
3. Review quality check results
4. Verify wiki sync will succeed

### Periodic Maintenance

1. Review weekly maintenance reports
2. Address GitHub issues created by automation
3. Update outdated documentation identified
4. Fix broken links reported

## Monitoring and Metrics

### Success Metrics

- **Sync Success Rate:** Target >99%
- **Quality Check Pass Rate:** Target >95%
- **Broken Links:** Target 0
- **Outdated Files:** Target <10%
- **Placeholder Content:** Target 0

### Where to Monitor

1. **GitHub Actions Tab:** View workflow runs
2. **Pull Request Comments:** See automated checks
3. **GitHub Issues:** Review maintenance issues
4. **Artifact Downloads:** Access detailed reports

## Support and Maintenance

### Regular Tasks

- **Weekly:** Review maintenance report
- **Monthly:** Audit documentation completeness
- **Quarterly:** Review and update automation rules

### Getting Help

1. Check workflow logs in Actions tab
2. Review this setup guide
3. Consult GITHUB-WIKI-AUTOMATION-PLAN.md
4. Check GitHub Actions documentation

## Conclusion

The GitHub Wiki automation system is now fully implemented and ready for use. It will:

- ✅ Automatically sync documentation changes
- ✅ Maintain quality standards
- ✅ Alert you to issues
- ✅ Ensure documentation stays current
- ✅ Integrate with your review process

Start by running the test workflow, then proceed with your first wiki sync!

---

*Setup guide created: August 20, 2025*
*Automation system version: 1.0.0*