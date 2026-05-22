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

### Links

- [Website](https://coding-dev-tools.github.io/devforge.dev/)
- [Pricing](https://coding-dev-tools.github.io/devforge.dev/pricing.html)
- [Documentation](https://coding-dev-tools.github.io/devforge.dev/docs.html)
- [Blog](https://coding-dev-tools.github.io/devforge.dev/blog.html)
