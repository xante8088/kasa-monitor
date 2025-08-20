# Documentation Standards Guide

## Version Control Standards

All documentation in Kasa Monitor follows semantic versioning and includes metadata to track changes and ensure currency.

## Document Version Format

Every documentation file must include a version footer with the following format:

```markdown
---

**Document Version:** 1.0.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current | Needs Review | Under Revision  
**Change Summary:** Initial documentation | Updated API endpoints | Added troubleshooting section
```

## Version Numbering System

Documentation follows semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR** (1.x.x): Complete rewrite or fundamental structure change
- **MINOR** (x.1.x): New sections added, significant content updates
- **PATCH** (x.x.1): Minor corrections, typo fixes, clarifications

### Version Increment Guidelines

| Change Type | Version Change | Examples |
|------------|---------------|----------|
| Complete rewrite | 2.0.0 | Architecture overhaul, new format |
| New major section | 1.1.0 | Added plugin development guide |
| New subsection | 1.0.1 | Added troubleshooting tips |
| Content updates | 1.0.1 | Updated configuration values |
| Typo/grammar fixes | 1.0.1 | Fixed spelling errors |
| Code example updates | 1.0.1 | Updated API response format |
| Broken link fixes | 1.0.1 | Corrected cross-references |

## Required Document Fields

### Header Section (Optional but Recommended)
```markdown
# Document Title

> **Document Type:** Guide | Reference | Tutorial | Troubleshooting  
> **Audience:** Developers | Administrators | End Users | All  
> **Prerequisites:** [List any required knowledge or setup]
```

### Footer Section (Required)
Every document must end with a version footer containing:

1. **Document Version** - Semantic version number
2. **Last Updated** - ISO 8601 date (YYYY-MM-DD)
3. **Review Status** - Current state of the document
4. **Change Summary** - Brief description of last change

### Review Status Definitions

- **Current**: Document is up-to-date and accurate
- **Needs Review**: Document may contain outdated information
- **Under Revision**: Active updates in progress
- **Deprecated**: Document is obsolete (include link to replacement)

## Documentation Categories

### API Documentation
- Version tied to API version
- Include request/response examples
- Document all error codes
- Show authentication requirements
- Update with each API change

### User Guides
- Task-focused documentation
- Include screenshots where helpful
- Step-by-step instructions
- Common use cases

### Technical References
- Architecture descriptions
- Database schemas
- Configuration options
- System requirements

### Troubleshooting Guides
- Problem-solution format
- Include error messages
- Diagnostic steps
- Resolution procedures

## Change Management Process

### When to Update Documentation

Documentation must be updated when:
- Code changes affect documented behavior
- New features are added
- Bugs are fixed that were documented workarounds
- User feedback indicates confusion
- Periodic review (quarterly minimum)

### Update Workflow

1. **Before Making Changes**
   - Check current version in footer
   - Review existing content thoroughly
   - Identify sections needing updates

2. **Making Updates**
   - Update content as needed
   - Increment version appropriately
   - Update "Last Updated" date
   - Add change summary
   - Update review status

3. **After Updates**
   - Verify all links work
   - Test code examples
   - Review formatting
   - Commit with descriptive message

### Commit Message Format
```
docs: Update [document name] to v[version]

- [Change description]
- [Additional changes]

Document: [filename]
Version: [old version] → [new version]
```

## Automated Version Tracking

### GitHub Actions Integration
The wiki sync workflow automatically:
- Validates document structure
- Checks for version footers
- Logs version changes
- Creates audit trail

### Version Validation Script
Documents are validated for:
- Presence of version footer
- Valid semantic version format
- ISO 8601 date format
- Non-empty change summary

## Documentation Templates

### New Document Template
```markdown
# [Document Title]

> **Document Type:** [Type]  
> **Audience:** [Target Audience]  
> **Prerequisites:** [Any requirements]

## Overview
[Brief introduction to the topic]

## [Main Sections]
[Document content organized in logical sections]

## Related Documentation
- [Link to related doc 1]
- [Link to related doc 2]

## Support
- [How to get help]
- [Where to report issues]

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Initial documentation
```

### Version Update Template
When updating an existing document:
```markdown
---

**Document Version:** [Increment version]  
**Last Updated:** [Today's date in YYYY-MM-DD]  
**Review Status:** Current  
**Change Summary:** [Describe what changed]
```

## Best Practices

### Writing Style
- Use clear, concise language
- Define technical terms on first use
- Include examples for complex concepts
- Use consistent terminology

### Code Examples
- Test all code examples
- Include complete, runnable examples
- Show expected output
- Explain important parts

### Cross-References
- Use relative links for internal docs
- Verify all links work
- Include section anchors for long documents
- Maintain link consistency

### Visual Content
- Include diagrams for architecture
- Add screenshots for UI elements
- Use tables for structured data
- Ensure images have alt text

## Review Schedule

### Quarterly Reviews
All documentation should be reviewed quarterly for:
- Technical accuracy
- Broken links
- Outdated information
- User feedback incorporation

### Major Release Reviews
Before each major release:
- Review all documentation
- Update version numbers
- Verify feature documentation
- Check deprecation notices

## Version History Tracking

### Changelog Format
For significant documentation updates, maintain a changelog:

```markdown
## Documentation Changelog

### Version 2.0.0 (2025-08-20)
- Complete rewrite for new architecture
- Added plugin development section
- Updated all API examples

### Version 1.2.0 (2025-07-15)
- Added troubleshooting guide
- Updated installation instructions
- Fixed broken links

### Version 1.1.0 (2025-06-01)
- Added Docker deployment guide
- Updated system requirements
- Clarified network configuration
```

## Automation Tools

### Version Check Script
A script is available to verify documentation standards:
```bash
# Check all documentation for version footers
npm run check-doc-versions

# Update all dates to today
npm run update-doc-dates

# Generate version report
npm run doc-version-report
```

## Quality Assurance

### Pre-Commit Checks
- Version footer present
- Date format valid
- No placeholder content
- Links validated

### Pull Request Reviews
Documentation changes require:
- Version increment
- Updated date
- Change summary
- Review approval

## Compliance

All documentation must comply with:
- Project code of conduct
- Accessibility guidelines
- Security best practices
- License requirements

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-08-20  
**Review Status:** Current  
**Change Summary:** Initial documentation standards guide