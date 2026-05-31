## DevForge

11 developer CLI tools that catch problems before production. Open source, MIT licensed.

### Tools

| Tool | What It Does |
|------|-------------|
| [API Contract Guardian](https://github.com/Coding-Dev-Tools/api-contract-guardian) | Catch breaking OpenAPI changes in CI |
| [json2sql](https://github.com/Coding-Dev-Tools/json2sql) | Convert JSON to SQL INSERT statements |
| [DeployDiff](https://github.com/Coding-Dev-Tools/deploydiff) | Preview infrastructure costs before deploy |
| [ConfigDrift](https://github.com/Coding-Dev-Tools/configdrift) | Detect config drift across environments |
| [APIGhost](https://github.com/Coding-Dev-Tools/apighost) | Mock API server from OpenAPI specs |
| [Envault](https://github.com/Coding-Dev-Tools/envault) | Sync and rotate .env files |
| [SchemaForge](https://github.com/Coding-Dev-Tools/schemaforge) | Bidirectional ORM schema conversion (11 formats) |
| [click-to-mcp](https://github.com/Coding-Dev-Tools/click-to-mcp) | Wrap any Click/Typer CLI as MCP server |
| [DeadCode](https://github.com/Coding-Dev-Tools/deadcode) | Find and remove dead code in React/Next.js |
| [DataMorph](https://github.com/Coding-Dev-Tools/datamorph) | Convert between CSV, JSON, YAML, Parquet, Avro, Protobuf |
| [DevForge](https://github.com/Coding-Dev-Tools/devforge) | Unified CLI — install all tools at once |

### Install

```bash
pip install devforge
```

## Reusable Workflows

This repository provides reusable GitHub Actions workflows for use across the DevForge organization.

### Python CI

Standard reusable CI for Python repositories. Runs linting (ruff), tests (pytest via hatch) across a configurable Python version matrix, and validates the build.

```yaml
name: Python CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  test:
    uses: Coding-Dev-Tools/.github/.github/workflows/python-ci.yml@main
```

Supported inputs:

| Input | Default | Description |
|-------|---------|-------------|
| `python-versions` | `["3.10","3.11","3.12","3.13"]` | JSON array of Python versions |
| `runner-os` | `["ubuntu-latest"]` | JSON array of runner OS targets |
| `run-lint` | `true` | Run ruff linting |
| `lint-path` | `src` | Path(s) to lint (space-separated) |
| `run-build` | `true` | Run hatch build check |
| `test-command` | (auto) | Custom test command override |
| `extra-deps` | (empty) | Extra pip install deps |

### Dependency Review

Scans PR dependency changes for known vulnerabilities before merging.

```yaml
name: Dependency Review
on:
  pull_request:
    branches: [main]
jobs:
  dependency-review:
    uses: Coding-Dev-Tools/.github/.github/workflows/dependency-review.yml@main
    permissions:
      contents: read
      pull-requests: write
```

Supported inputs:

| Input | Default | Description |
|-------|---------|-------------|
| `fail-on-severity` | `high` | Severity threshold: low, medium, high, critical |
| `allow-licenses` | (empty) | Comma-separated allowed licenses |
| `deny-licenses` | (empty) | Comma-separated denied licenses |
| `fail-on-scopes` | `runtime,unknown` | Scopes to fail on: runtime, development, unknown |
---

### Auto Code Review

Automated code review for pull requests — runs lint, format, secret detection, TODO markers, and large-file checks, then posts a summary PR comment with a pass/warn/fail verdict.

```yaml
name: Auto Code Review
on:
  pull_request:
    branches: [main]
    types: [opened, synchronize, reopened]
jobs:
  code-review:
    uses: Coding-Dev-Tools/.github/.github/workflows/auto-code-review.yml@main
    permissions:
      contents: read
      pull-requests: write
      security-events: write
```

Supported inputs:

| Input | Default | Description |
|-------|---------|-------------|
| `python-version` | `'3.12'` | Python version for lint tools |
| `ruff-targets` | `'.'` | Paths ruff should scan (space-separated) |
| `detect-secrets` | `true` | Run detect-secrets credential scan |
| `check-todos` | `false` | Warn on leftover TODO/FIXME/HACK markers |
| `max-file-size` | `500` | Max allowed file size in KB (0 = skip) |
| `post-comment` | `true` | Post review summary as a PR comment |

**Checks performed:**

| Check | Tool | Severity |
|-------|------|----------|
| Lint | Ruff | Warning |
| Format | Ruff | Warning |
| Secret detection | detect-secrets | **Fail** |
| TODO/FIXME/HACK | grep | Warning |
| Large files | find | Warning |

> **Setup note:** The workflow file lives in `templates/workflows/auto-code-review.yml` in this repo. To activate it, copy or symlink it to `.github/workflows/auto-code-review.yml`. This is required because GitHub only recognizes workflow files under `.github/workflows/`.

### Code Review (Composite Action)

Lightweight code review using the `actions/code-review` composite action — runs ruff lint, bandit security scan, mypy type-check, and pytest. Posts a pass/fail PR comment.

```yaml
name: Code Review
on:
  pull_request:
    types: [opened, synchronize, reopened]
jobs:
  review:
    uses: Coding-Dev-Tools/.github/.github/workflows/code-review.yml@main
    with:
      python-version: '3.12'
      run-ruff: true
      run-bandit: true
      run-type-check: false
      run-pytest: true
      source-dir: src
      fail-on-security: true
    permissions:
      contents: read
      pull-requests: write
      checks: write
```

Supported inputs:

| Input | Default | Description |
|-------|---------|-------------|
| `python-version` | `'3.12'` | Python version for review tools |
| `run-ruff` | `true` | Run ruff lint check |
| `run-bandit` | `true` | Run bandit security scan |
| `run-type-check` | `false` | Run mypy type checking |
| `run-pytest` | `true` | Run pytest suite |
| `source-dir` | `src` | Source directory to lint/scan |
| `fail-on-security` | `true` | Fail on high-severity security issues |
| `post-comment` | `true` | Post review summary as a PR comment |

**Checks performed:**

| Check | Tool | Severity |
|-------|------|----------|
| Lint | Ruff | Warning |
| Security | Bandit | **Fail** |
| Types | Mypy | Warning |
| Tests | Pytest | **Fail** |

> **Setup note:** The workflow file lives in `templates/workflows/code-review.yml` in this repo. To activate it, copy or symlink it to `.github/workflows/code-review.yml`. This is required because GitHub only recognizes workflow files under `.github/workflows/`.

### Links

- [Website](https://coding-dev-tools.github.io/devforge.dev/)
- [Pricing](https://coding-dev-tools.github.io/devforge.dev/pricing.html)
- [Documentation](https://coding-dev-tools.github.io/devforge.dev/docs.html)
- [Blog](https://coding-dev-tools.github.io/devforge.dev/blog.html)
