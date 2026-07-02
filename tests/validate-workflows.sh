#!/usr/bin/env bash
# Validate reusable workflows in Coding-Dev-Tools/.github
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
P=0; F=0
check() { local d="$1"; shift; if "$@" &>/dev/null; then echo "[PASS] $d"; P=$((P+1)); else echo "[FAIL] $d"; F=$((F+1)); fi; }
echo "=== Workflow Validation ==="
for wf in python-ci auto-code-review code-review dependency-review stale pr-title-lint auto-stale; do
  case "$wf" in
    python-ci) check_name="Workflow python-ci.yml" ;;
    auto-code-review) check_name="Workflow auto-code-review.yml" ;;
    code-review) check_name="Workflow code-review.yml" ;;
    dependency-review) check_name="Workflow dependency-review.yml" ;;
    stale) check_name="Workflow stale.yml" ;;
    pr-title-lint) check_name="Workflow pr-title-lint.yml" ;;
    auto-stale) check_name="Workflow auto-stale.yml" ;;
  esac
  check "$check_name" test -f "$ROOT/.github/workflows/$wf.yml"
done
for wf in "$ROOT"/.github/workflows/*.yml; do
  check "$(basename "$wf") has trigger" grep -qE '^on:|  workflow_call:' "$wf"
done
for tpl in auto-code-review caller-auto-code-review code-review; do
  check "Template $tpl.yml" test -f "$ROOT/templates/workflows/$tpl.yml"
done
check "AGENTS.md" test -f "$ROOT/AGENTS.md"
check "VERSION" test -f "$ROOT/VERSION"
echo "=== $P passed, $F failed ==="; exit "$F"
