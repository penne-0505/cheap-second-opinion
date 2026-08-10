---
title: "QA Verification: Preset mechanism and output schema v1"
status: active
draft_status: n/a
qa_status: partial
risk: Medium
qa_schema: 2
created_at: 2026-08-10
updated_at: 2026-08-10
references:
  - "_docs/intent/Core/preset-mechanism/decision.md"
  - "_docs/intent/Core/preset-model-selection/decision.md"
  - "_docs/intent/Core/preset-schema/decision.md"
  - "_docs/plan/Core/preset-mechanism/plan.md"
  - "_docs/qa/Core/preset-mechanism/test-plan.md"
related_issues: []
related_prs: []
---

# QA Verification: Preset mechanism and output schema v1

## Summary

Core-Enhance-8 の preset mechanism を実装した。models.toml に 3 preset (master / cheap / design) + 5 alias 整形 + `[archived_models]` declared 追加、cli.py に `--preset` / `--reasoning-effort` flag + `presets` subcommand + preset 解決 + argparse mutex + bare multi の default preset 適用 + strict parsing + output schema v1 (schema_version + preset metadata + effective_effort + usage) を実装。SKILL.md に primary agent 向け使い分けガイド追加。全 AC + INV-001 (mutex) pass。E2E で API 実呼び出しを伴う AC (usage 抽出、実 multi 並列実行) は Manual QA として deferred、dry-run で構造検証は完遂。

## Verification Verdict

Verdict: PARTIAL

理由: 2026-08-10 の実 API E2E run で AC-001 (3 モデル並列実 API 実行) と AC-008 (schema v1 全 field 生成) が PASS 昇格。全 AC / DEC / INV / Automated Test は PASS。ただし SKILL.md primary agent guide の実運用フィット (実 Claude Code session での preset 選定 flow) が LLM 挙動依存で programmatic 検証不能、および旧 alias breaking change / cost_usd 精度 / primary agent 品質という observation-based residual risks が残るため、qa-review skill の PARTIAL 定義 (「一部未確認だが残リスクと follow-up TODO が明示され、限定的に完了扱いにできる」) を採用。E2E 実行証跡は Commands Run / Automated Test Results / AC Coverage 参照。

## Commands Run

```bash
# Phase 3-A schema slice
Write skills/cheap-second-opinion/scripts/cheap_opinion/models.toml  # 5 alias, 3 preset, defaults, [archived_models]

# Phase 3-B CLI slice (full cli.py rewrite)
Write skills/cheap-second-opinion/scripts/cheap_opinion/cli.py  # SCHEMA_VERSION, resolve_preset, --preset/--reasoning-effort, presets subcommand, mutex, bare multi, strict parsing, output v1

# Phase 3-C doc slice
Write skills/cheap-second-opinion/SKILL.md  # primary agent guide, alias examples 更新, preset examples, reasoning-effort説明

# Verification batch
PYTHONPATH=skills/cheap-second-opinion/scripts python -m compileall -q skills/cheap-second-opinion/scripts   # exit 0
PYTHONPATH=skills/cheap-second-opinion/scripts python -m cheap_opinion presets   # 3 preset + default marker
PYTHONPATH=skills/cheap-second-opinion/scripts python -m cheap_opinion multi ask --dry-run "test"   # bare → default preset master
PYTHONPATH=skills/cheap-second-opinion/scripts python -m cheap_opinion multi ask --preset cheap --dry-run "test"
PYTHONPATH=skills/cheap-second-opinion/scripts python -m cheap_opinion multi ask --preset design --dry-run "test"
PYTHONPATH=skills/cheap-second-opinion/scripts python -m cheap_opinion multi ask --preset master --models kimi-k3 --dry-run "test"   # argparse error (mutex)
PYTHONPATH=skills/cheap-second-opinion/scripts python -m cheap_opinion multi ask --preset nonexistent --dry-run "test"   # SystemExit
PYTHONPATH=skills/cheap-second-opinion/scripts python -m cheap_opinion --reasoning-effort weird-val ask --model kimi-k3 --dry-run "test"   # warning + pass-through
PYTHONPATH=skills/cheap-second-opinion/scripts python -m cheap_opinion --reasoning-effort max ask --model kimi-k3 --dry-run "test"   # no warn (known enum)
CHEAP_OPINION_STRICT_CONFIG=1 CHEAP_OPINION_MODELS_TOML=<toml with bogus_section> python -m cheap_opinion models   # startup error
CHEAP_OPINION_MODELS_TOML=<toml with bogus_section> python -m cheap_opinion models   # warning only
CHEAP_OPINION_MODELS_TOML=/nonexistent python -m cheap_opinion models   # 'models file not found: /nonexistent' → env override 確認
./scripts/check-docs.sh   # 新規 ERROR/WARN 無し (残り全て pre-existing)

# E2E 実 API run (2026-08-10、rate limiter sample diff、user 明示コスト許可)
PYTHONPATH=skills/cheap-second-opinion/scripts python -m cheap_opinion multi review \
  --preset master --diff-file <sample.diff> --format json --concurrency 3 --max-findings 3
# 結果: exit=0, wall=60s, total_cost_usd=$0.0194
#   succeeded=[v4-flash-0731, gpt-5.6-luna, kimi-k3]、failed=[]
#   schema_version=1、summary.preset=master、summary.preset_description=使用者視点文言
#   各 runs[].effective_effort='high' (defaults 継承)、usage.{prompt_tokens, completion_tokens, cost_usd} 全生成
```

## Automated Test Results

| Command / Test | Result | Notes |
| --- | --- | --- |
| `compileall skills/cheap-second-opinion/scripts` | PASS | exit 0 |
| `python -m cheap_opinion --help` | PASS | 新 `--reasoning-effort` top-level 表示 |
| `python -m cheap_opinion presets` | PASS | 3 preset + default marker + 含有 alias 表示 |
| `python -m cheap_opinion multi ask --dry-run` (bare) | PASS | schema_version=1, preset=master, 3 models 展開 |
| `python -m cheap_opinion multi ask --preset cheap --dry-run` | PASS | preset=cheap, 2 models (v4-flash-0731, gpt-5.6-luna) |
| `python -m cheap_opinion multi ask --preset design --dry-run` | PASS | preset=design, 3 models (kimi-k3, glm-5.2, qwen3.8-max) |
| `python -m cheap_opinion multi ask --preset X --models Y` | PASS | argparse mutex error `--models: not allowed with argument --preset` |
| `python -m cheap_opinion multi ask --preset nonexistent` | PASS | SystemExit `Unknown preset 'nonexistent'. Known presets: cheap, design, master` |
| `python -m cheap_opinion --reasoning-effort weird-val ask ...` | PASS | stderr warning + payload pass-through |
| `python -m cheap_opinion --reasoning-effort max ask ...` | PASS | no warn (known enum) |
| `CHEAP_OPINION_STRICT_CONFIG=1` + unknown field | PASS | startup error 昇格 |
| Non-strict + unknown field | PASS | warning のみ、実行継続 |
| `CHEAP_OPINION_MODELS_TOML=/nonexistent models` | PASS | env override 経路確認 |
| `[archived_models]` empty parse | PASS | error 出ず data['archived_models'] = {} |
| 5 alias 命名 rule 準拠 | PASS | glm-5.2 / gpt-5.6-luna / kimi-k3 / qwen3.8-max / v4-flash-0731 |
| SKILL.md flag / subcommand ↔ CLI 整合 | PASS | SKILL.md 記載 `--preset` `--reasoning-effort` `presets` `multi ask` `multi review` 全て CLI に存在 |
| AGENTS.md 検証 4 種 (Refactor-6 保持) | PASS | compileall / --help / models / skill CLI models 全 exit 0 |
| `check-docs.sh` (Enhance-8 起因) | PASS | 新規 ERROR/WARN ゼロ (残り全て pre-existing) |

## Manual QA Results

| Checklist Item | Result | Notes |
| --- | --- | --- |
| `presets` subcommand 出力の読みやすさ | PASS | default marker、description (使用者視点)、alias list が階層表示、視認性 OK |
| `--reasoning-effort weird-val` warning message の informativeness | PASS | 未知値 + known list + pass-through 明示、実行継続を明示 |
| SKILL.md primary agent guide の primary agent-friendliness | DEFERRED | 実 primary agent session で preset 選定 flow は Docs-Doc-4/-10 と併せて別途評価 |

## Acceptance Criteria Coverage

| ID | Result | Evidence |
| --- | --- | --- |
| AC-001 (master preset 3 モデル並列) | PASS | 実 API run で `succeeded=['v4-flash-0731', 'gpt-5.6-luna', 'kimi-k3']`、wall=60s、`failed=[]`、`total_findings=5` を確認 (2026-08-10、rate limiter sample diff) |
| AC-002 (cheap / design 動作) | PASS | dry-run で対応 alias set 展開確認 |
| AC-003 (mutex) | PASS | argparse mutually_exclusive_group で `--models: not allowed with argument --preset` |
| AC-004 (bare multi = default preset) | PASS | `multi ask --dry-run` で preset=master 自動適用確認 |
| AC-005 (--reasoning-effort pass-through + warning) | PASS | 未知値で stderr warning + payload に値反映、known enum は無音 |
| AC-006 (strict env var で startup error) | PASS | `CHEAP_OPINION_STRICT_CONFIG=1` で unknown field 検出時 SystemExit、default は warning のみ |
| AC-007 (presets subcommand) | PASS | 3 preset + description + 含有 alias 表示、default marker |
| AC-008 (output schema v1) | PASS | 実 API run で全 field 生成確認: `schema_version=1`、`summary.preset='master'`、`summary.preset_description` (使用者視点文言)、`summary.total_cost_usd=0.0194`、各 `runs[].effective_effort='high'` (defaults 継承)、`runs[].usage.{prompt_tokens, completion_tokens, cost_usd}` 生成 |
| AC-009 (未定義 preset startup error) | PASS | `Unknown preset 'nonexistent'. Known presets: ...` |
| AC-010 (5 alias 命名整形) | PASS | `models` 出力に glm-5.2 / gpt-5.6-luna / kimi-k3 / qwen3.8-max / v4-flash-0731、命名 rule 準拠 |
| AC-011 (SKILL.md primary agent guide) | PASS | `## Preset selection (primary agent guide)` セクション、3 preset 各 1 行 + 単発 vs multi の使い分け方針 |
| AC-012 (models.toml 探索順) | PASS | `CHEAP_OPINION_MODELS_TOML=/nonexistent` で env override 経路確認、default_models_file() は project root → package default 順 |
| AC-013 (`[archived_models]` declared) | PASS | 空セクション parse で error 出ず、`data['archived_models']` = `{}` |

## Decision Conformance

| ID | Result | Why the implementation remains aligned |
| --- | --- | --- |
| [preset-model-selection] DEC-001 (master preset) | PASS | `[presets.master] models = ["v4-flash-0731", "gpt-5.6-luna", "kimi-k3"]` |
| DEC-002 (cheap preset) | PASS | `[presets.cheap] models = ["v4-flash-0731", "gpt-5.6-luna"]` |
| DEC-003 (design preset) | PASS | `[presets.design] models = ["kimi-k3", "glm-5.2", "qwen3.8-max"]` |
| DEC-004..008 (v4flash design 除外 / grok 除外 / gemini 除外 / muse-spark 除外 / qwen master 除外) | PASS | 各除外モデルは alias にも preset にも登録なし、Intent doc に rationale 明記 |
| DEC-009 (reasoning tier = high 統一) | PASS | `[defaults].reasoning_effort = "high"` |
| DEC-010 (alias 命名 rule) | PASS | 命名 rule comment を models.toml 冒頭に明記、5 alias すべて rule 準拠 |
| [preset-schema] DEC-001 (models.toml 統合) | PASS | `[presets.*]` を models.toml 内に配置、独立 file なし |
| DEC-002 (inline 配列) | PASS | `models = ["a", "b", "c"]` inline 表記 |
| DEC-003 (preset tier 持たない) | PASS | preset entry は `models` + `description` のみ |
| DEC-004 (フル alias 名参照) | PASS | preset の `models` list はフル alias 名で記載 |
| DEC-005 (--preset mutex) | PASS | argparse mutually_exclusive_group で拒否 |
| DEC-006 (preset validate 起動時) | PASS | resolve_preset で未定義即 SystemExit |
| DEC-007 (reasoning-effort pass-through + warning) | PASS | 未知値 warning + pass-through、strict mode で error 昇格 |
| DEC-008 (bare multi = default preset) | PASS | `_resolve_multi_aliases()` で fallback to `[defaults].preset` |
| DEC-009 (per-model 保持、normalize なし) | PASS | `runs[]` は per-model output 独立、集約層なし |
| DEC-010 (schema_version + metadata) | PASS | `schema_version: 1` + `summary.preset` + `runs[].effective_effort` + `runs[].usage` |
| DEC-011 (探索順) | PASS | `default_models_file()` で project root cwd → importlib.resources package default、env var は argparse 層 |
| DEC-012 (last_reviewed) | PASS | `[defaults].last_reviewed = "2026-08-10"` + comment 記載 |
| DEC-013 (`[archived_models]` declared) | PASS | 空セクション + comment 記載 |

## Invariant Coverage

| ID | Result | Evidence |
| --- | --- | --- |
| INV-001 (from [preset-schema] DEC-005): `--preset` と `--models` の同時指定は起動時に拒否される | PASS | argparse `add_mutually_exclusive_group()` で拒否。実装方式に関わらず「同時指定は非受理」結果を保つ |

## Deferred / Not Covered

| ID | Reason | Follow-up |
| --- | --- | --- |
| SKILL.md primary agent guide の実運用フィット | primary agent session で「code review してほしい」から preset 選定に至るかは skill 使用状況の実測でしか判定不能 | 実 Claude Code session の運用フィードバックで判定、必要なら SKILL.md ガイド強化 |

## Residual Risks

- **旧 alias 名 (`deepseek-v4-flash`, `qwen-max`) の breaking change**: 意図的 (Intent DEC-010 alias 命名 rule 統一)。過去の実行例が SKILL.md / README / guide に残っていれば動作しない。SKILL.md / README / usage guide は Docs-Doc-4 で更新済。primary agent が実運用で旧 alias を叩いた場合の recovery は SystemExit message で自動誘導される (`Known aliases: glm-5.2, gpt-5.6-luna, kimi-k3, qwen3.8-max, v4-flash-0731. Full OpenRouter IDs (containing '/') are also accepted.`)。
- **primary agent の preset 選定判断品質**: SKILL.md ガイド (「code review → master」等) が primary agent の判断を吸収する設計だが、実際に preset が正しく選ばれるかは LLM 依存で保証しがたい。運用フィードバックで判定、必要ならガイド強化 (Docs-Doc-4 で継続改善)。
- **cost_usd の OpenRouter 表示値 vs 実請求乖離**: pass-through 前提、乖離は skill の責務外 (SKILL.md にも将来注記予定)。

## Follow-up TODOs

- **Docs-Doc-4** (README + usage guide の alias / preset 例更新): SKILL.md 更新は本 verification で完了、README/guide は Docs-Doc-4 の未着手範囲。
- **Docs-Doc-10** (SKILL.md ↔ CLI --help diff CI): hard dep = Core-Enhance-8 完了、着手可能。SKILL.md 記載 flag/subcommand と `--help` 出力の整合を CI で監視。
- **Core-Test-9** (配布形態 smoke test CI): AC-001 / AC-008 の E2E カバレッジ、および `--preset` / `presets` / `--reasoning-effort` を含めた新 CLI surface の smoke test を含める形で実装。
- **Docs-Doc-7** (usage.md pre-existing errors): 未着手、優先度は依然 P3。
- **既存 primary agent (Claude Code / Codex) sessions への周知**: 旧 alias breaking change を beta 段階で明示。運用開始後に SKILL.md ガイドで自動吸収される想定だが、初回セッションで旧 alias を叩いた場合の error message はわかりやすい (`Unknown model alias 'deepseek-v4-flash'. Known aliases: glm-5.2, gpt-5.6-luna, kimi-k3, qwen3.8-max, v4-flash-0731. Full OpenRouter IDs (containing '/') are also accepted.`) ため recovery 可能。
