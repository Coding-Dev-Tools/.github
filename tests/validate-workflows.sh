#!/usr/bin/env bash
# Validate reusable workflows in Coding-Dev-Tools/.github
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
P=0; F=0
check() { local d="$1"; shift; if "$@" &>/dev/null; then echo "[PASS] $d"; P=$((P+1)); else echo "[FAIL] $d"; F=$((F+1)); fi; }
echo "=== Workflow Validation ==="
for wf in python-ci auto-code-review code-review dependency-review stale pr-title-lint; do
  check "Workflow $wf.yml" test -f "$ROOT/.github/workflows/$wf.yml"
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
