---
title: Cheap Second Opinion Usage Guide
status: active
draft_status: n/a
created_at: "2026-05-23"
updated_at: "2026-05-23"
references:
  - README.md
  - skills/cheap-second-opinion/SKILL.md
related_issues: []
related_prs: []
---

## Purpose

`cheap-second-opinion` provides a read-only consultation path for Codex.
It asks OpenRouter-hosted models for review notes, risk checks, or design
feedback, then leaves the final judgment to the primary agent.

The external model must not edit files, run commands, or make final decisions.
Treat every answer as a candidate signal that still needs local verification.

## Default Skill Flow

Set `SKILL_DIR` to the loaded skill folder.

```bash
SKILL_DIR="$(pwd)/skills/cheap-second-opinion"
```

Confirm the bundled aliases before calling a model.

```bash
"$SKILL_DIR/scripts/cheap-opinion" models
```

Review the current repository diff.

```bash
"$SKILL_DIR/scripts/cheap-opinion" review \
  --model qwen-coder \
  --format json
```

Ask a targeted risk or design question.

```bash
"$SKILL_DIR/scripts/cheap-opinion" ask \
  --model kimi \
  --template risk \
  "この変更で見落としやすいリスクは？"
```

Use `multi` only to collect several independent perspectives. Do not treat
multiple matching answers as a vote.

## Logging

Logging is off by default. Enable it only when the user asks, because logs can
contain prompts, diffs, file contents, and model responses.

```bash
"$SKILL_DIR/scripts/cheap-opinion" logging enable
```

By default, logs are written under the target git root:

```text
.second-opinion-poc/logs/
```

Use `--state-dir` only when a custom storage location is intentional.

## Configuration

The skill-local `models.toml` is the default model alias source. Override it
with `--models-file` or `CHEAP_OPINION_MODELS_TOML` when testing another model
set.

The CLI requires `OPENROUTER_API_KEY` for real model calls. Dry runs do not
require a key and are useful for checking prompt shape before network access.

## Minimum Verification

Before publishing or changing the skill, run these checks:

```bash
skills/cheap-second-opinion/scripts/cheap-opinion models
skills/cheap-second-opinion/scripts/cheap-opinion review \
  --diff-file examples/sample.diff \
  --dry-run \
  --format json
PYTHONPATH=src python -m cheap_opinion models
python -m compileall \
  src/cheap_opinion \
  skills/cheap-second-opinion/scripts/cheap_opinion
VALIDATOR=/home/penne/.codex/skills/.system/skill-creator/scripts
python "$VALIDATOR/quick_validate.py" skills/cheap-second-opinion
deno run --allow-read scripts/validate-frontmatter.mjs
```
