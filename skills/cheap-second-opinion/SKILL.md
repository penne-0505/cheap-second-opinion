---
name: cheap-second-opinion
description: Get a read-only second opinion from an independent model for code, design, risk, or debugging questions. Use `review` for git diffs and `ask` for targeted consultation when the user asks for another angle, reconsideration, or multi-perspective review, and proactively before risky, hard-to-revert, or high-impact changes; verify findings before acting.
---

# Cheap Second Opinion

Use this as a read-only consultation tool. Do not let the external model edit files or make final decisions. The primary Codex agent must inspect and verify any finding before acting on it.

The bundled CLI is self-contained under this skill folder:

```bash
SKILL_DIR="<absolute path to this loaded skill folder>"
"$SKILL_DIR/scripts/cheap-opinion" models
```

Do not derive `SKILL_DIR` from the target repo's `pwd`; installed skills usually live outside the repo being reviewed.

## Review Current Diff

Use this when the user asks for a code review or asks for an independent external perspective on local changes.

```bash
SKILL_DIR="<absolute path to this loaded skill folder>"
"$SKILL_DIR/scripts/cheap-opinion" review --model qwen-coder --format json
```

Useful variants:

```bash
"$SKILL_DIR/scripts/cheap-opinion" review --model deepseek --format markdown
"$SKILL_DIR/scripts/cheap-opinion" review --model kimi --staged --format json
"$SKILL_DIR/scripts/cheap-opinion" review --repo /path/to/repo --model qwen-coder --format json
"$SKILL_DIR/scripts/cheap-opinion" multi review --models qwen-coder,deepseek,kimi --format markdown
```

## Ask For Opinion

Use `ask` for design, risk, debugging, or general second opinions. Keep the question specific and include only the files/context that matter.

```bash
"$SKILL_DIR/scripts/cheap-opinion" ask --model kimi --template risk --file src/foo.ts "この変更で見落としやすいリスクは？"
"$SKILL_DIR/scripts/cheap-opinion" multi ask --models qwen-coder,deepseek,kimi --template design "この設計方針を別視点から見て"
```

Templates are intentionally broad:

- `general`
- `risk`
- `design`
- `debug`

## Logging

Logging is opt-in and is controlled by the user. Enable it only when the user asks.

```bash
"$SKILL_DIR/scripts/cheap-opinion" logging status
"$SKILL_DIR/scripts/cheap-opinion" logging enable
"$SKILL_DIR/scripts/cheap-opinion" logging --repo /path/to/repo enable
"$SKILL_DIR/scripts/cheap-opinion" logging disable
```

When enabled, logs are written under the target repo's `.second-opinion-poc/logs/` directory. `review --repo /path/to/repo` uses that repo's git root for the default state/log directory. Use `--state-dir` only when the user explicitly wants a custom location.

## Model Config

Default model aliases live in `models.toml` inside this skill folder. Use `--models-file` or `CHEAP_OPINION_MODELS_TOML` only when the user explicitly wants to override the bundled config.

For `multi` runs, keep the same verification stance: treat model outputs as candidates for inspection, not as a vote or final answer.
