# Code Review Pipeline — Deployment Note

This PR adds the automated code review reusable workflow.

## ⚠️ Post-Merge Step

The file is at `.github/workflows-pending/code-review.yml` because
our OAuth token lacks the `workflow` scope required to push to
`.github/workflows/` directly.

After merging, move the file:
```bash
mv .github/workflows-pending/code-review.yml .github/workflows/code-review.yml
git add . && git commit -m "ci: move code-review workflow to workflows dir"
git push
```

Or: authorize the token with `workflow` scope, then re-push.

## What It Does

| Job | Tools | Purpose |
|-----|-------|---------|
| Lint & Format | ruff, mypy | Code quality & type checking |
| Security Scan | bandit, semgrep, pip-audit | Vulnerability detection |
| Test Coverage | pytest-cov | Coverage gate + reporting |
| Review Summary | gh CLI | PR comment with status table |

## Usage (from any repo)

```yaml
jobs:
  code-review:
    uses: Coding-Dev-Tools/.github/.github/workflows/code-review.yml@main
    secrets:
      CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}
```
