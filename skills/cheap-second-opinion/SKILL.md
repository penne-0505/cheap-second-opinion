---
name: cheap-second-opinion
description: Get a read-only second opinion from an independent model for code, design, risk, or debugging questions. Use `review` for git diffs and `ask` for targeted consultation when the user asks for another angle, reconsideration, or multi-perspective review, and proactively before risky, hard-to-revert, or high-impact changes; verify findings before acting.
---

# Cheap Second Opinion

Use this as a read-only consultation tool. Do not let the external model edit files or make final decisions. The primary Codex agent must inspect and verify any finding before acting on it.

## Preset selection (primary agent guide)

`multi` サブコマンドは「どのモデルを組み合わせるか」の判断を preset で吸収する。主導 agent は用途タグを選ぶだけでよい:

- **master**: セカンドオピニオンが必要なとき、迷ったらこれ。
- **cheap**: 安く広く多発で意見が欲しいとき。探索や発想。
- **design**: web / UI デザインの taste 判断が必要なとき。

単発 `--model X` はデバッグ・比較検証など明確な用途がある場合に限る。実運用は preset を使う。preset を `--preset` も `--models` も指定せずに `multi` を叩けば `[defaults].preset` (= master) が暗黙適用される。

The bundled CLI is self-contained under this skill folder:

```bash
SKILL_DIR="<absolute path to this loaded skill folder>"
"$SKILL_DIR/scripts/cheap-opinion" presets   # 一覧
"$SKILL_DIR/scripts/cheap-opinion" models    # 一覧
```

Do not derive `SKILL_DIR` from the target repo's `pwd`; installed skills usually live outside the repo being reviewed.

## Review Current Diff

Use this when the user asks for a code review or asks for an independent external perspective on local changes.

```bash
SKILL_DIR="<absolute path to this loaded skill folder>"
"$SKILL_DIR/scripts/cheap-opinion" multi review --preset master --format json
```

Useful variants:

```bash
"$SKILL_DIR/scripts/cheap-opinion" multi review --preset cheap --format markdown
"$SKILL_DIR/scripts/cheap-opinion" multi review --staged --format json          # bare multi = default preset (master) を暗黙適用
"$SKILL_DIR/scripts/cheap-opinion" review --model kimi-k3 --format markdown     # 単発 (デバッグ用途)
"$SKILL_DIR/scripts/cheap-opinion" review --repo /path/to/repo --model v4-flash-0731 --format json
```

## Ask For Opinion

Use `ask` for design, risk, debugging, or general second opinions. Keep the question specific and include only the files/context that matter.

```bash
"$SKILL_DIR/scripts/cheap-opinion" multi ask --preset design --template design "この UI の design tradeoff を評価して"
"$SKILL_DIR/scripts/cheap-opinion" ask --model kimi-k3 --template risk --file src/foo.ts "この変更で見落としやすいリスクは？"
"$SKILL_DIR/scripts/cheap-opinion" multi ask --template general "この設計方針を別視点から見て"      # bare multi = master 暗黙適用
```

Templates are intentionally broad:

- `general`
- `risk`
- `design`
- `debug`

## Reasoning Effort Override

一時的に reasoning tier を上げたい (escalate) / 下げたい場合、top-level `--reasoning-effort` で override 可能:

```bash
"$SKILL_DIR/scripts/cheap-opinion" --reasoning-effort max multi review --preset master
"$SKILL_DIR/scripts/cheap-opinion" --reasoning-effort medium ask --model kimi-k3 "..."
```

既知値は `low`, `medium`, `high`, `xhigh`, `max`, `minimal`, `none`。未知値も pass-through (stderr に warning)、`CHEAP_OPINION_STRICT_CONFIG=1` で startup error に昇格。default は models.toml の `[defaults].reasoning_effort = "high"`。

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

Default model aliases と preset roster は skill folder 内 `scripts/cheap_opinion/models.toml` に集約されている。探索順は env var `CHEAP_OPINION_MODELS_TOML` → project root `./models.toml` → package default。project 単位で override したい場合は project root に `models.toml` を置く。

Full OpenRouter model ID (e.g. `openai/gpt-5.6-luna`) を `--model provider/name` として渡せば alias 未登録モデルも単発で使える。

For `multi` runs, keep the same verification stance: treat model outputs as candidates for inspection, not as a vote or final answer.
