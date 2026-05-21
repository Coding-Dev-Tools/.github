# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the latest version.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via GitHub's private vulnerability reporting feature:

1. Go to the repository's Security tab
2. Click "Report a vulnerability"
3. Fill in the details

We aim to respond within 48 hours and will keep you updated on the fix.

## Automated Security Checks

All repos in the Coding-Dev-Tools org should use the reusable dependency review workflow:

```yaml
jobs:
  dependency-review:
    uses: Coding-Dev-Tools/.github/.github/workflows/dependency-review.yml@main
```

This scans PR dependency changes for known vulnerabilities before merging.

## Security Best Practices

- Keep your dependencies up to date
- Python projects: use `pip audit` to check for known vulnerabilities
- Node.js projects: use `npm audit` (or `pnpm audit`) to check for known vulnerabilities
- Add the `sentinel-review` label to security-sensitive PRs to prevent automatic stale closure
- Report any security concerns promptly

## Dependency Updates

Dependabot is configured at the org level for GitHub Actions dependencies.
Individual repos should add their own ecosystem entries (pip, npm, etc.)
to their local `.github/dependabot.yml`.