#!/usr/bin/env bash
# Core-Test-9: verify skill dir can run standalone via bash wrapper.
# Fast Track S/Low — clean-checkout emulation without API calls.
#
# Copies the skill dir to a tmp location (simulating "user acquired the skill
# folder alone") and runs read-only commands (models / presets / --help) via
# the bash wrapper. Detects "repo で動く / 配布形態で動かない" drift.
# intent: DEC-003 (Core/cli-unification) — zero-install UX の継続監視。
set -euo pipefail

SKILL_SRC="skills/cheap-second-opinion"

if [ ! -d "$SKILL_SRC" ]; then
  echo "ERROR: skill dir not found at $SKILL_SRC" >&2
  exit 2
fi

WORK=$(mktemp -d)
# Do not attempt to clean up (template may block rm -rf); tmp dir OS-cleaned periodically.
cp -r "$SKILL_SRC" "$WORK/"
cd "$WORK/$(basename "$SKILL_SRC")"

status=0
for cmd in models presets "--help"; do
  if ./scripts/cheap-opinion "$cmd" > /dev/null 2>&1; then
    echo "  skill wrapper $cmd: OK"
  else
    exit_code=$?
    echo "ERROR: skill wrapper '$cmd' failed (exit $exit_code)" >&2
    status=1
  fi
done

if [ $status -eq 0 ]; then
  echo "Skill wrapper smoke test: OK (tmp dir at $WORK, OS-cleaned)"
fi
exit $status
