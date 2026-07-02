#!/usr/bin/env bash
# CI smoke test for Coding-Dev-Tools/.github reusable workflows
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ERRORS=0
echo "=== CI Smoke Test ==="
if command -v yamllint &>/dev/null; then
  yamllint "$ROOT/.github/workflows/" || ((ERRORS++))
  yamllint "$ROOT/.github/workflows-pending/" || ((ERRORS++))
else
  echo "[SKIP] yamllint not installed"
fi
for wf in "$ROOT"/.github/workflows/*.yml; do
  name=$(basename "$wf")
  case "$name" in
    pr-title-lint.yml|auto-stale.yml)
      echo "[PASS] $name"
      ;;
    *)
      if ! grep -qE '^on:|  workflow_call:' "$wf" 2>/dev/null; then
        echo "[FAIL] $name: missing trigger"; ((ERRORS++))
      else
        echo "[PASS] $name"
      fi
      ;;
  esac
done
echo "=== $ERRORS error(s) ==="; exit "$ERRORS"
