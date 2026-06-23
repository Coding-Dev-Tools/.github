# Coding-Dev-Tools-dot-github

## Purpose
DevForge organization profile and reusable GitHub Actions workflows for 11 open-source CLI tools. Provides standardized CI (Python, Node), dependency review, and release workflows used across all Coding-Dev-Tools repositories.

## Build & Test Commands
- Install: N/A (workflow repository)
- Test: N/A (workflows are tested in consuming repos)
- Lint: `yamllint .github/workflows/` (if configured)
- Build: N/A

## Architecture
Key directories:
- `.github/workflows/` — Reusable workflows (python-ci.yml, dependency-review.yml, node-ci.yml, release.yml, etc.)
- `.github/actions/` — Composite actions
- `ISSUE_TEMPLATE/` — Standardized issue templates
- `profile/` — Organization profile README
- `templates/` — Project templates

## Conventions
- Language: YAML (GitHub Actions)
- Test framework: N/A (validated by consumer repos)
- CI: Self-hosted workflows consumed by 20+ repos
- Linting: yamllint (recommended)
- Reusable workflow pattern with inputs/outputs