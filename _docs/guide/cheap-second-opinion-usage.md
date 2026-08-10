---
title: Cheap Second Opinion Usage Guide
status: active
draft_status: n/a
created_at: "2026-05-23"
updated_at: "2026-08-10"
references:
  - "README.md"
  - "_docs/intent/Core/preset-model-selection/decision.md"
  - "_docs/intent/Core/preset-schema/decision.md"
  - "_docs/intent/Core/cli-unification/decision.md"
related_issues: []
related_prs: []
---

## Purpose

`cheap-second-opinion` provides a read-only consultation path for Claude Code / Codex.
It asks OpenRouter-hosted models for review notes, risk checks, or design
feedback, then leaves the final judgment to the primary agent.

The external model must not edit files, run commands, or make final decisions.
Treat every answer as a candidate signal that still needs local verification.

## Default Skill Flow

Skill 本体は `skills/cheap-second-opinion/SKILL.md` に配置され、primary agent 向け使い分けガイドが含まれています。以下は補助ガイド。

Set `SKILL_DIR` to the loaded skill folder.

```bash
SKILL_DIR="$(pwd)/skills/cheap-second-opinion"
```

Confirm the bundled aliases / presets before calling a model.

```bash
"$SKILL_DIR/scripts/cheap-opinion" models
"$SKILL_DIR/scripts/cheap-opinion" presets
```

### Multi run with preset (推奨)

```bash
"$SKILL_DIR/scripts/cheap-opinion" multi review --preset master --format json
"$SKILL_DIR/scripts/cheap-opinion" multi ask --preset design --template design "この UI 設計の tradeoff は？"
"$SKILL_DIR/scripts/cheap-opinion" multi review                                # bare → [defaults].preset (master) 暗黙適用
```

### 単発 (デバッグ・比較検証用)

```bash
"$SKILL_DIR/scripts/cheap-opinion" review \
  --model v4-flash-0731 \
  --format json

"$SKILL_DIR/scripts/cheap-opinion" ask \
  --model kimi-k3 \
  --template risk \
  "この変更で見落としやすいリスクは？"
```

Use `multi` to collect several independent perspectives. Do not treat matching answers as a vote.

### Reasoning effort override

```bash
"$SKILL_DIR/scripts/cheap-opinion" --reasoning-effort max multi review --preset master
```

未知値は pass-through + stderr warning、`CHEAP_OPINION_STRICT_CONFIG=1` で startup error 昇格。

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

The skill-local `models.toml` (`skills/cheap-second-opinion/scripts/cheap_opinion/models.toml`) is the default alias / preset source. Override it with `--models-file` or `CHEAP_OPINION_MODELS_TOML` when testing another model set. 探索順は `CHEAP_OPINION_MODELS_TOML` → project root `./models.toml` → package default (詳細は [_docs/intent/Core/cli-unification/decision.md](../intent/Core/cli-unification/decision.md) DEC-002 参照)。

The CLI requires `OPENROUTER_API_KEY` for real model calls. Dry runs do not
require a key and are useful for checking prompt shape before network access.

## Minimum Verification

Before publishing or changing the skill, run these checks:

```bash
NEW_PP="skills/cheap-second-opinion/scripts"
"$NEW_PP/cheap-opinion" models
"$NEW_PP/cheap-opinion" presets
"$NEW_PP/cheap-opinion" multi review \
  --diff-file examples/sample.diff \
  --dry-run \
  --format json
PYTHONPATH=$NEW_PP python -m cheap_opinion models
PYTHONPATH=$NEW_PP python -m compileall -q $NEW_PP
deno run --allow-read --allow-env --allow-run=git scripts/validate-frontmatter.mjs
./scripts/check-docs.sh
```
