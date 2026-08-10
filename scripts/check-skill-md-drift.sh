#!/usr/bin/env bash
# Docs-Doc-10: verify SKILL.md documented flags match CLI --help output.
# Fast Track XS/Low — minimum viable diff-check.
#
# Extracts CLI flag names (--foo) from SKILL.md code blocks and asserts each
# appears in some `cheap-opinion` subcommand --help output. Prevents SKILL.md
# from documenting removed/typo'd flags after CLI evolution.
set -euo pipefail

SKILL="skills/cheap-second-opinion/SKILL.md"
PP="skills/cheap-second-opinion/scripts"

if [ ! -f "$SKILL" ]; then
  echo "ERROR: SKILL.md not found at $SKILL" >&2
  exit 2
fi

help_all=$(mktemp)
trap 'rm -f "$help_all"' EXIT

PYTHONPATH="$PP" python -m cheap_opinion --help >> "$help_all" 2>&1
for sub in review ask logging models presets "multi review" "multi ask"; do
  # shellcheck disable=SC2086
  PYTHONPATH="$PP" python -m cheap_opinion $sub --help >> "$help_all" 2>&1 || true
done

# Extract flag names inside SKILL.md fenced code blocks only (avoid prose false positives).
flags=$(awk '/^```/{f=!f; next} f' "$SKILL" | grep -oE -- '--[a-z][a-z0-9-]+' | sort -u || true)

if [ -z "$flags" ]; then
  echo "WARN: no --flags found in SKILL.md code blocks (nothing to check)"
  exit 0
fi

status=0
count=0
for flag in $flags; do
  count=$((count + 1))
  if ! grep -q -- "$flag" "$help_all"; then
    echo "ERROR: SKILL.md documents flag not in CLI --help: $flag" >&2
    status=1
  fi
done

if [ $status -eq 0 ]; then
  echo "SKILL.md ↔ CLI --help drift check: OK ($count flags checked)"
fi
exit $status
