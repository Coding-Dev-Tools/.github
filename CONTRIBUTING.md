# Contributing to DevForge / Revenue Holdings

Thank you for your interest in contributing! All tools in the DevForge organization are open source (MIT) and built with contribution in mind.

## How to Contribute

### 1. Find or Open an Issue

- Check existing issues for something you'd like to work on.
- If you're fixing a bug or adding a feature, open an issue first to discuss.

### 2. Fork & Branch

- Fork the repository and create a branch named `yourname/short-description`.
- We recommend prefixing with your GitHub username, e.g. `alice/fix-readme-typo`.

### 3. Make Changes

- Follow the existing code style (we use `ruff` for Python formatting).
- Keep commits small and focused.
- Use [Conventional Commits](https://www.conventionalcommits.org/):
  `type(scope): description`
  Examples: `fix(cli): handle empty input gracefully`, `docs(readme): update install instructions`

### 4. Test

- Run the full test suite before submitting: `pytest` or `hatch run test`
- If adding new functionality, include tests.
- Ensure lint passes: `ruff check .` (or `hatch run lint`)

### 5. Open a Pull Request

- Open a PR against the `main` branch.
- Fill out the PR template (checklist, description, etc.).
- CI will run automatically. All checks must pass before merging.

### 6. Review

- A maintainer (AI or human) will review your PR.
- Address any feedback and update as needed.
- Once approved, your PR will be squashed and merged.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/Coding-Dev-Tools/<repo-name>.git
cd <repo-name>

# Install dev dependencies
pip install -e ".[dev]"
# or
hatch env create

# Run tests
pytest
```

## Code of Conduct

Be respectful and constructive. This is a community of developers helping developers.

## Questions?

Open a [Discussion](https://github.com/orgs/Coding-Dev-Tools/discussions) or reach out on [Twitter](https://x.com/DevForgeTools).
