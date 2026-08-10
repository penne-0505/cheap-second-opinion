---
title: "Plan: Preset mechanism and output schema v1"
status: active
draft_status: n/a
created_at: 2026-08-10
updated_at: 2026-08-10
references:
  - "_docs/intent/Core/preset-model-selection/decision.md"
  - "_docs/intent/Core/preset-schema/decision.md"
  - "_docs/qa/Core/preset-mechanism/test-plan.md"
  - "TODO.md"
related_issues: []
related_prs: []
---

<!-- Canonical path: _docs/plan/Core/preset-mechanism/plan.md -->
<!-- 対応 TODO: Core-Enhance-8。実装は Core-Refactor-6 完了後に着手。 -->

## Overview

cheap-second-opinion CLI に用途タグ preset (master / cheap / design) を導入し、主導 agent (Claude Code / Codex) のモデル選定判断負荷を skill 側で吸収する。同時に `--reasoning-effort` CLI flag、`presets` subcommand、`schema_version: 1` 付き multi output、models.toml の schema 拡張 (default + override 意味論、strict parsing) を実装する。

判断根拠は [[preset-model-selection]] (含有モデル・除外モデル rationale) と [[preset-schema]] (schema / CLI / output 設計)。

## Scope

### schema slice (models.toml)

- `[defaults].preset = "master"` 追加
- `[defaults].reasoning_effort = "high"` 追加
- `[defaults].last_reviewed = "2026-08-10"` 追加、comment で trigger 意図明示
- 命名 rule comment (`<series>-<version>[-<variant>]`、deepseek は vendor prefix 抜き例外)
- 5 alias 整形: `v4-flash-0731`, `gpt-5.6-luna` (新規), `kimi-k3`, `glm-5.2`, `qwen3.8-max`
- `[presets.master]`, `[presets.cheap]`, `[presets.design]` 3 個追加 (models + description)
- `[archived_models]` 空セクション declared (comment 付き)
- 未知 field への default warning / opt-in strict 対応 (env var `CHEAP_OPINION_STRICT_CONFIG`)

### CLI slice (cli.py)

- `--preset <name>` flag (multi サブコマンド専用)
- `--reasoning-effort <val>` flag (全 command、pass-through + warning)
- `presets` subcommand (preset 一覧 + description + 含有 alias 表示、human-readable format)
- preset 解決ロジック: `--preset X` → models.toml `[presets.X].models` → alias list → ModelConfig 展開
- mutex validation: `--preset` と `--models` の同時指定は起動時 error
- 未定義 preset 名は起動時 error
- bare `multi review` / `multi ask` は `[defaults].preset` を暗黙適用
- 未知 config field: default warning、`CHEAP_OPINION_STRICT_CONFIG=1` で startup error

### output slice (JSON schema v1)

- multi output root に `schema_version: 1`
- `summary.preset` (nullable str)、`summary.preset_description` (nullable str)、`summary.total_cost_usd` (nullable float)
- `runs[].effective_effort` (nullable str)、`runs[].usage.{prompt_tokens, completion_tokens, cost_usd}` (nullable)
- 単発 `review` / `ask` output は現状踏襲 + `schema_version` + `usage` 追加

### doc slice

- SKILL.md 冒頭に primary agent 向け preset 使い分けガイド (3 preset 各 1 行) 追加
- README + `_docs/guide/cheap-second-opinion-usage.md` の実行例に preset 使用例追加 (Docs-Doc-4 と統合検討)

## Non-Goals

- Core-Refactor-6 (cli.py / models.toml 二重管理解消): 前提 TODO として独立実装
- escalate preset (max tier 想定): 実測で不要判断、後日別途起票
- grok 4.5 / muse-spark 1.2 の alias 登録: [[preset-model-selection]] DEC-005, DEC-007 で除外決着
- gpt-5.6-sol variant: 差別化点未共有のため保留
- consensus / unique 分類 layer (multi output): [[preset-schema]] DEC-009 で除外決着
- hidden preset-only モデル flag: 判断削減原理からシンプル化
- user home config (`~/.config/cheap-opinion/models.toml`) 探索: 単一 project 想定で over-engineering
- PyPI publish: 現時点で必要性なし
- primary agent への preset 選定 auto-hint (LLM 判定): item 2 原理 (判断削減) と衝突するため実装しない

## Requirements

### Functional

- [preset-schema] DEC-001〜013 の全 decision を実装する。
- [preset-model-selection] DEC-001〜010 に沿った alias / preset roster を models.toml に反映する。
- Core-Enhance-8 の AC-001〜013 を全て満たす。

### Non-Functional

- 既存挙動 (単発 `review` / `ask`、multi の per-model output 構造) は backward compatible。
- CLI 起動時間の regression は許容しない (現状 base line: `--help` 実行 ~200ms 以内)。
- OpenRouter provider 別 reasoning tier 挙動には skill が判断せず pass-through。
- output JSON size は現状の 1.2 倍以内 (usage / preset metadata 追加による膨張想定範囲)。

## Tasks

1. Refactor-6 完了確認 (前提)
2. schema slice: models.toml 拡張 + strict parsing 対応
3. CLI slice: 3 flag + 1 subcommand + preset 解決 + mutex validation
4. output slice: schema v1 化 + usage 抽出
5. doc slice: SKILL.md + README + guide 更新
6. QA test-plan の Test Matrix に沿った verification
7. verification.md 作成 → TODO 削除

## QA Plan

- QA document: `_docs/qa/Core/preset-mechanism/test-plan.md`
- Risk level: Medium
- Test strategy:
  - Unit: preset 解決ロジック、mutex validation、strict parsing、schema_version output field 生成
  - Integration: `cheap-opinion models` / `cheap-opinion presets` / `cheap-opinion multi review --preset master --dry-run`
  - E2E: OpenRouter mock で multi run 完全実行、schema v1 output 生成、`--reasoning-effort` override
  - Manual QA: SKILL.md ガイド追加内容の primary agent-friendliness 確認
  - Validator / static check: `PYTHONPATH=... python -m compileall`、`check-docs.sh`
- AC-001..013 を Test Matrix で unit / integration / E2E / manual に紐付ける。INV-001 (mutex) を unit + integration で確認。
- 影響する DEC: [[preset-model-selection]] DEC-001..010 と [[preset-schema]] DEC-001..013 全て。verification で Decision Conformance を確認。

## Deployment / Rollout

- リリース手順: PR で models.toml + cli.py + SKILL.md 一括変更、`AGENTS.md` 記載検証コマンド 4 種と `check-docs.sh` を PR CI で確認。
- rollback: git revert で 1 commit 前に戻せば preset 未実装状態に戻る (Refactor-6 完了状態は保持)。models.toml の schema 拡張は backward compat のため revert のみで復旧可能。
- 監視: 特になし (skill は local 実行、外部監視対象ではない)。
