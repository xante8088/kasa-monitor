## [1.1.0](https://github.com/xante8088/kasa-monitor/compare/v1.0.1...v1.1.0) (2025-08-22)

### 🚀 Features

* implement granular Docker cleanup with semantic versioning support ([a520b1c](https://github.com/xante8088/kasa-monitor/commit/a520b1ce8cbb2e0da7d28e5661a79b02b0e84dbc))

## [1.0.1](https://github.com/xante8088/kasa-monitor/compare/v1.0.0...v1.0.1) (2025-08-22)

### 🐛 Bug Fixes

* improve TruffleHog secret scanning to handle same BASE/HEAD commits ([8f71418](https://github.com/xante8088/kasa-monitor/commit/8f71418b0ba6e97a055816e7f550d3f3c0a03d2a))

## [1.0.0](https://github.com/xante8088/kasa-monitor/compare/v0.3.19...v1.0.0) (2025-08-22)

### ⚠ BREAKING CHANGES

* Remove redundant Docker build workflows

- Remove .github/workflows/docker-build.yml (redundant with CI/CD)
- Remove .github/workflows/docker-build-manual.yml (redundant with CI/CD)
- Update docker-build-pr.yml to use GitHub Container Registry consistently
- Consolidate all Docker builds into single CI/CD pipeline workflow

BENEFITS:
- Single registry: All images in GitHub Container Registry (ghcr.io)
- No duplicate builds: CI/CD pipeline handles all production builds
- Quality gates: Images only built after tests pass
- Resource efficiency: No redundant CI/CD minutes usage
- Simplified maintenance: One comprehensive workflow instead of multiple

REMAINING WORKFLOWS:
- ci-cd.yml: Complete CI/CD pipeline (build/test/deploy/release)
- docker-build-pr.yml: PR validation builds only (no push)
- cleanup workflows: Image management and storage optimization

Updated documentation to reflect single registry approach and simplified workflow structure.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
* Remove auto-tag workflow in favor of manual release process

- Remove .github/workflows/auto-tag.yml (conflicted with CI/CD releases)
- Remove auto-generated version.json file
- Enhance CI/CD pipeline release job with comprehensive release notes
- Add multi-platform Docker image information to releases
- Add quick start guide to release notes
- Improve Docker cleanup workflows with better package detection
- Improve Docker tagging strategy across all build workflows
- Add comprehensive release management documentation

NEW RELEASE PROCESS:
- Create git tags manually: git tag v1.0.0 && git push origin v1.0.0
- CI/CD pipeline handles: build → test → deploy → release
- Single source of truth for releases
- No duplicate release creation
- Better workflow ordering and control

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>

* Consolidate Docker workflows to eliminate redundancy ([d40a058](https://github.com/xante8088/kasa-monitor/commit/d40a05883542b8335dd8863a73eeb74d9e0bdc72))
* Consolidate release workflow and remove auto-tag duplication ([3ced73e](https://github.com/xante8088/kasa-monitor/commit/3ced73ed76a64a35ecd5fe5c127a980b9a7ae992))

### 🚀 Features

* complete comprehensive security vulnerability remediation ([be2f4e8](https://github.com/xante8088/kasa-monitor/commit/be2f4e82027c0c2b6f7c80356206e6a07d07b04b))
* comprehensive update of GitHub Actions to latest versions ([f3f858f](https://github.com/xante8088/kasa-monitor/commit/f3f858ff4ad27de9c8d273ff01b6c14bdffaf835))
* implement automatic version management with semantic-release ([e1c011a](https://github.com/xante8088/kasa-monitor/commit/e1c011a95c536180fd80bcbae4dc0d8d076fb489))
* implement comprehensive security fixes and infrastructure ([a3d2ded](https://github.com/xante8088/kasa-monitor/commit/a3d2ded35ee5cb701599f756b86e141a728ebdae))

### 🐛 Bug Fixes

* add required permissions for PR documentation checks ([d60c3d3](https://github.com/xante8088/kasa-monitor/commit/d60c3d3070417cae22e8534248c3dcc33c6f8acd))
* apply automatic code formatting to security fixes ([9b54c46](https://github.com/xante8088/kasa-monitor/commit/9b54c461223473994af845235de98913afbf8ead))
* backend/requirements.txt to reduce vulnerabilities ([e006731](https://github.com/xante8088/kasa-monitor/commit/e00673109933bdc6d8a159a5f9457539fbd40335))
* correct Python version path in Dockerfile for cache key computation ([7a8864a](https://github.com/xante8088/kasa-monitor/commit/7a8864a4cc8b18cc79dfa0cea10af88abef764ff))
* make Bandit security scan non-blocking ([9db009b](https://github.com/xante8088/kasa-monitor/commit/9db009b76b8b3236944a157c02bdec5a099c0c44))
* make Docker Scout scan non-blocking due to entitlement issues ([bfc1b39](https://github.com/xante8088/kasa-monitor/commit/bfc1b3995efb2b88dbd770c93289c2dc83813ceb))
* remove duplicate --fail flag from TruffleHog secret scanning ([17d5886](https://github.com/xante8088/kasa-monitor/commit/17d58867dba42f886652a6a6a9ae143eed0b5033))
* update semantic-release workflow to use Node.js 20 ([cbad5bf](https://github.com/xante8088/kasa-monitor/commit/cbad5bfe3b96b07070fd018b7b972502df1a8f10))
* update Tailwind CSS 4.x configuration and documentation port references ([5cb71a5](https://github.com/xante8088/kasa-monitor/commit/5cb71a566337c0199848140cd5788e0f1244f683))

### 🔒 Security

* fix critical backend vulnerabilities - reduced from 959 to 1 alert ([313df47](https://github.com/xante8088/kasa-monitor/commit/313df47a40a4a5132d4addcc683539140b48cebb))
* implement initial critical security vulnerability fixes ([8ddf952](https://github.com/xante8088/kasa-monitor/commit/8ddf9527f7d7899f3478bd313748d17190e58956))
* reorganize documentation and remove sensitive internal files ([b2fe947](https://github.com/xante8088/kasa-monitor/commit/b2fe947cdf96765778d94f712ef64762a29a3eac))

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Features
- Complete comprehensive security vulnerability remediation
- Implement comprehensive security fixes and infrastructure

### Bug Fixes
- Correct Python version path in Dockerfile for cache key computation
- Update Tailwind CSS 4.x configuration and documentation port references
- Apply automatic code formatting to security fixes
- Make Docker Scout scan non-blocking due to entitlement issues

### Security
- Reorganize documentation and remove sensitive internal files
- Fix critical backend vulnerabilities - reduced from 959 to 1 alert
- Implement initial critical security vulnerability fixes

## [0.3.19] - 2024-08-14

### Added
- Initial tagged release with core monitoring functionality
- Web interface for device management
- Power consumption tracking
- Cost analysis features
- Docker support with multi-architecture builds
- Plugin system foundation
- Audit logging system
- User management with role-based access control

### Security
- JWT authentication implementation
- SSL/TLS support
- Rate limiting
- Input validation

---

*Note: This changelog will be automatically maintained by semantic-release starting from the next release.*
