---
title: "QA Test Plan: Preset mechanism and output schema v1"
status: active
draft_status: n/a
qa_status: planned
risk: Medium
qa_schema: 2
created_at: 2026-08-10
updated_at: 2026-08-10
references:
  - "_docs/intent/Core/preset-mechanism/decision.md"
  - "_docs/intent/Core/preset-model-selection/decision.md"
  - "_docs/intent/Core/preset-schema/decision.md"
  - "_docs/plan/Core/preset-mechanism/plan.md"
related_issues: []
related_prs: []
---

# QA Test Plan: Preset mechanism and output schema v1

## Source of Intent

- TODO: `Core-Enhance-8` (`TODO.md`)
- Plan: `_docs/plan/Core/preset-mechanism/plan.md`
- Intent: `_docs/intent/Core/preset-model-selection/decision.md`, `_docs/intent/Core/preset-schema/decision.md`

## Quality Goal

主導 agent (Claude Code / Codex) が用途タグ (master / cheap / design) を指定するだけで、モデル選定・reasoning tier・output schema 解析の全てを skill 側の contract に沿って処理できる。primary agent 側の判断負荷を preset の存在意義 (item 2 原理) に沿って構造的に吸収する。

## Acceptance Criteria

TODO Core-Enhance-8 の AC-001〜013 を採用。要旨:

- AC-001: `multi review --preset master` で 3 モデル並列実行
- AC-002: `--preset cheap` / `--preset design` 動作
- AC-003: `--preset` と `--models` mutex (起動時 error)
- AC-004: bare `multi review` / `multi ask` は default preset 適用
- AC-005: `--reasoning-effort <val>` pass-through + warning (未知値)
- AC-006: `CHEAP_OPINION_STRICT_CONFIG=1` で未知 field startup error
- AC-007: `presets` subcommand が preset 一覧を人間可読形式で表示
- AC-008: multi output に `schema_version: 1` + preset metadata + effective_effort + usage
- AC-009: 未定義 preset 名は起動時 error
- AC-010: 5 alias 整形 (命名 rule 準拠、deepseek 例外)
- AC-011: SKILL.md 冒頭に primary agent 向け 3 preset 使い分けガイド
- AC-012: models.toml 探索順が env → project root → package default
- AC-013: `[archived_models]` 空セクション declared で parse OK

## Decision Review Scope

- [[preset-model-selection]] DEC-001..010 全て
- [[preset-schema]] DEC-001..013 全て

verification で各 DEC の `Why` と `Change freedom` に実装が沿うことを review する。

## Intent-derived Invariants

- **INV-001** (from [[preset-schema]] DEC-005): `--preset` と `--models` の同時指定は起動時に拒否される。

## Risk Assessment

- **Risk level**: Medium
- **Risk rationale**: CLI 拡張 3 flag + 1 subcommand + output schema 変更で影響範囲が広い。ただし backward compat (単発 CLI 挙動不変、multi 既存 output に field 追加のみ) を保つ設計。
- **Regression risk**: 現行の単発 `--model` / `multi --models` 挙動が壊れる可能性。behavior-preservation は Core-Refactor-6 QA と重複しない範囲で確認する。
- **Data safety risk**: なし (read-only CLI、ファイル書き込みは logging のみで既存挙動維持)。
- **Security / privacy risk**: `CHEAP_OPINION_STRICT_CONFIG` env var の値検証は不要 (bool 判定のみ)。preset name の validate で injection 攻撃余地なし (TOML key として parse される)。
- **UX risk**: `--preset` と `--models` mutex による user 側の使い分け学習コスト。SKILL.md ガイド (AC-011) で吸収。
- **Agent misbehavior risk**: primary agent が bare `multi` を叩いた時に default preset (master) が silent に発火してコスト発生。SKILL.md で「bare multi = master 起動」を明示する必要 (AC-011 に含める)。

## Test Strategy

- **Unit**: preset 解決関数 (alias 展開)、mutex validation、strict parsing 判定、schema_version 付き output builder、`default_models_file()` の探索順
- **Integration**: `cheap-opinion presets`、`cheap-opinion models`、`cheap-opinion multi review --preset master --dry-run`、`cheap-opinion multi review --preset X --models a,b` (error)、`cheap-opinion --reasoning-effort unknown-val --model kimi-k3 ask "..."` (warning 検証、dry-run)
- **E2E**: OpenRouter API mock (subprocess env var で HTTP interceptor) で multi run 完全実行、schema v1 output の全 field 生成確認
- **Manual QA**: SKILL.md ガイド追記後に primary agent (別 Claude session) で「code review してほしい」を投げ、preset 選定 flow が期待通りか観察
- **Validator / static check**: `PYTHONPATH=... python -m compileall -q ...`、`./scripts/check-docs.sh`、`python -m cheap_opinion --help` の出力に新 flag / subcommand が現れるか diff review
- **Diff review**: [[preset-model-selection]] DEC-001..010 と [[preset-schema]] DEC-001..013 の `Why` に沿って PR review

## Test Matrix

| ID | Source | Requirement / Optional Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | TODO | master preset 3 モデル並列実行 | Integration | `cheap-opinion multi review --preset master --dry-run` | dry-run payload に v4-flash-0731 / gpt-5.6-luna / kimi-k3 の 3 モデル含む | planned |
| AC-002 | TODO | cheap / design preset 動作 | Integration | 同上を `--preset cheap` / `--preset design` で | 対応 alias set が payload に現れる | planned |
| AC-003 | TODO | `--preset` と `--models` mutex | Unit + Integration | `cheap-opinion multi review --preset master --models kimi-k3` | 起動時 argparse error / SystemExit 2 | planned |
| AC-004 | TODO | bare multi は default preset 適用 | Integration | `cheap-opinion multi review --dry-run` (`--preset`/`--models` 無し) | master preset の 3 モデルが payload に現れる | planned |
| AC-005 | TODO | `--reasoning-effort` pass-through + warning | Unit + Integration | `cheap-opinion --reasoning-effort weird-val --model kimi-k3 ask --dry-run "test"` | stderr に warning、payload に `reasoning.effort = "weird-val"` | planned |
| AC-006 | TODO | strict env var で未知 field error | Unit | `CHEAP_OPINION_STRICT_CONFIG=1 cheap-opinion models` (models.toml に未知 field 追加した状態) | startup error / non-zero exit | planned |
| AC-007 | TODO | `presets` subcommand | Integration | `cheap-opinion presets` | 3 preset name + description + models 表示 | planned |
| AC-008 | TODO | output schema v1 | E2E | mock 経由で `cheap-opinion multi review --preset master` 実行 | JSON に `schema_version: 1`、`summary.preset`、`runs[].effective_effort`、`runs[].usage` | planned |
| AC-009 | TODO | 未定義 preset 名は error | Unit | `cheap-opinion multi review --preset nonexistent` | 起動時 error | planned |
| AC-010 | TODO | 5 alias 整形 | Static | `cat models.toml \| grep "\[models\."` | `v4-flash-0731`, `gpt-5.6-luna`, `kimi-k3`, `glm-5.2`, `qwen3.8-max` が並ぶ | planned |
| AC-011 | TODO | SKILL.md 冒頭ガイド | Diff review | `git diff skills/cheap-second-opinion/SKILL.md` | 3 preset 各 1 行の使い分けガイド追加 | planned |
| AC-012 | TODO | models.toml 探索順 | Unit | `default_models_file()` の unit test | env → project root → package default の順で解決 | planned |
| AC-013 | TODO | `[archived_models]` declared | Static + Unit | `cat models.toml \| grep archived_models` + parse test | セクション存在、CLI parse で error 出ない | planned |
| INV-001 | [[preset-schema]] DEC-005 | `--preset`/`--models` mutex 起動時拒否 | Unit | argparse mutex test | 実装方式に関わらず、同時指定は起動時に非受理 | planned |

## Manual QA Checklist

- [ ] SKILL.md 冒頭ガイド追加後、`skills/cheap-second-opinion/SKILL.md` を primary agent session で読ませ、preset 選定が期待どおり (「code review → master」等) 起きるかを確認
- [ ] `cheap-opinion presets` の出力が読みやすいか (整形、description の使用者視点確認)
- [ ] `--reasoning-effort weird-val` warning message が informative か (未知値の告知 + 実行継続の明示)

## Regression Checklist

- [ ] 現行 `cheap-opinion --model X review` 単発が Refactor 前と同一動作
- [ ] 現行 `cheap-opinion multi review --models a,b,c` が Refactor 前と同一動作
- [ ] `cheap-opinion models` の出力が新 alias 5 個を反映しつつ既存 CLI 互換
- [ ] logging enable / disable が既存挙動維持

## Out of Scope

- Refactor-6 (`_docs/qa/Core/cli-unification/test-plan.md` で担保)
- Docs-Doc-10 (SKILL.md ↔ --help diff CI、別 TODO)
- Core-Test-9 (配布形態 smoke test、別 TODO)
- primary agent の実際の preset 選定質評価 (LLM 判定は skill 側の責務外)

## Open Questions

- OpenRouter が `reasoning.effort` 非対応モデルに未知値を投げた場合の挙動 (silent ignore / error) は実装時に curl 等で verify する。
- E2E 段階での OpenRouter mock 実装方式 (HTTP interceptor / conftest fixture) は Plan slice で決定。
