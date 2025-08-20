# Documentation Versioning Examples

This guide shows how the versioning system applies to different types of documentation in Kasa Monitor.

## Version Format Examples

### API Documentation Example

```markdown
# Device Control API

[API content...]

---

**Document Version:** 2.1.3  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Added new power threshold endpoints, fixed response examples
```

**Version Reasoning:**
- Major version 2: Complete API restructure from v1
- Minor version 1: Added new endpoint group
- Patch version 3: Fixed examples and typos

### User Guide Example

```markdown
# Getting Started Guide

[Guide content...]

---

**Document Version:** 1.3.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Added Docker setup section, updated screenshots
```

**Version Reasoning:**
- Major version 1: Original complete guide
- Minor version 3: Added new major section
- Patch version 0: No patches since minor update

### Troubleshooting Guide Example

```markdown
# Network Troubleshooting

[Troubleshooting content...]

---

**Document Version:** 1.0.5  
**Last Updated:** 2025-08-20  
**Review Status:** Needs Review  
**Change Summary:** Added macvlan network issues, updated firewall rules
```

**Version Reasoning:**
- Major version 1: Complete troubleshooting guide
- Minor version 0: No new sections added
- Patch version 5: Multiple small fixes and clarifications

### Draft Documentation Example

```markdown
# Plugin Marketplace (DRAFT)

[Draft content with TODOs...]

---

**Document Version:** 0.1.0  
**Last Updated:** 2025-08-20  
**Review Status:** Under Revision  
**Change Summary:** Initial draft for plugin marketplace feature
```

**Version Reasoning:**
- Major version 0: Document not yet complete
- Minor version 1: First draft version
- Patch version 0: No patches yet

## Version Increment Guidelines by Change Type

### Major Version Changes (X.0.0)

**When to increment:**
- Complete rewrite of documentation
- Fundamental structure change
- Breaking changes in documented features

**Example commit:**
```bash
git commit -m "docs: Rewrite API documentation to v2.0.0

- Complete restructure for new API version
- New authentication system documentation
- Breaking changes from v1 API

Document: wiki/API-Documentation.md
Version: 1.5.2 → 2.0.0"
```

### Minor Version Changes (x.Y.0)

**When to increment:**
- New section added
- Significant content additions
- New features documented

**Example commit:**
```bash
git commit -m "docs: Update Installation guide to v1.1.0

- Added Kubernetes deployment section
- New environment variables documented
- Extended troubleshooting section

Document: wiki/Installation.md
Version: 1.0.8 → 1.1.0"
```

### Patch Version Changes (x.y.Z)

**When to increment:**
- Typo fixes
- Small clarifications
- Code example updates
- Link fixes

**Example commit:**
```bash
git commit -m "docs: Update Security guide to v1.2.1

- Fixed broken links to OWASP
- Corrected JWT example
- Updated rate limit values

Document: wiki/Security-Guide.md
Version: 1.2.0 → 1.2.1"
```

## Review Status Examples

### Current

```markdown
**Document Version:** 1.2.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Updated for latest release, all information verified
```

Use when:
- Documentation is up-to-date
- Recently reviewed or updated
- Matches current software version

### Needs Review

```markdown
**Document Version:** 1.0.3  
**Last Updated:** 2025-02-15  
**Review Status:** Needs Review  
**Change Summary:** May contain outdated information after v0.4.0 release
```

Use when:
- Documentation is older than 90 days
- Software has been updated since last doc update
- User feedback indicates issues

### Under Revision

```markdown
**Document Version:** 0.8.0  
**Last Updated:** 2025-08-19  
**Review Status:** Under Revision  
**Change Summary:** Actively updating for new authentication system
```

Use when:
- Actively working on updates
- Major changes in progress
- Temporary state during updates

### Deprecated

```markdown
**Document Version:** 1.5.0  
**Last Updated:** 2025-01-01  
**Review Status:** Deprecated  
**Change Summary:** Replaced by new Plugin Development Guide v2
```

Use when:
- Documentation is obsolete
- Feature has been removed
- Replaced by new documentation

## Change Summary Examples

### Good Change Summaries

✅ **Clear and specific:**
- "Added WebSocket event documentation, fixed authentication examples"
- "Updated for v0.4.0 release, new rate limiting section"
- "Complete rewrite for new plugin system architecture"
- "Fixed broken links, updated deprecated API endpoints"

### Poor Change Summaries

❌ **Too vague:**
- "Updated"
- "Fixed stuff"
- "Changes"
- "Minor updates"

## Automation Examples

### Check All Documentation Versions

```bash
# Run version compliance check
npm run check-doc-versions

# Example output:
# ✅ Compliant Documents (25)
# ⚠️  Documents with Issues (3)
# ❌ Documents Missing Footer (2)
```

### Update Documentation Versions

```bash
# Add version footers to all documents
npm run update-doc-versions

# Update only dates (preserve versions)
npm run update-doc-dates

# Dry run to see what would change
npm run update-doc-versions -- --dry-run
```

### Generate Version Report

```bash
# Generate detailed version report
npm run doc-version-report

# Output includes:
# - Version distribution
# - Age analysis
# - Review status breakdown
# - Compliance metrics
```

## GitHub Actions Integration

The versioning system integrates with CI/CD:

```yaml
# .github/workflows/wiki-maintenance.yml
- name: Check documentation version compliance
  run: |
    node scripts/check-doc-versions.js
    # Fails if documents lack version footers
```

## Version Footer Template

Copy this template for new documents:

```markdown
---

**Document Version:** 1.0.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Initial documentation
```

## Migration from Unversioned Documents

For existing documentation without versions:

1. **Assess completeness** to determine initial version:
   - Complete, production-ready: `1.0.0`
   - Mostly complete: `0.9.0`
   - Basic but functional: `0.5.0`
   - Early draft: `0.1.0`

2. **Add footer** using the update script:
   ```bash
   npm run update-doc-versions
   ```

3. **Review and adjust** versions as needed

4. **Commit with clear message**:
   ```bash
   git commit -m "docs: Add version tracking to all documentation

   - Added semantic versioning to 30 wiki documents
   - Set initial versions based on completeness
   - Established review status for all docs"
   ```

## Best Practices

1. **Always increment version** when making changes
2. **Update date** even for minor changes
3. **Use meaningful change summaries** to track evolution
4. **Review status accurately** reflects document state
5. **Major.Minor.Patch** follows semantic versioning
6. **Commit messages** reference version changes
7. **Regular reviews** keep documentation current

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Initial versioning examples guide