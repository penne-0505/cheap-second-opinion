---
title: "QA Test Plan: CLI and models.toml unification (Refactor-6)"
status: active
draft_status: n/a
qa_status: planned
risk: Medium
qa_schema: 2
created_at: 2026-08-10
updated_at: 2026-08-10
references:
  - "_docs/intent/Core/cli-unification/decision.md"
  - "_docs/plan/Core/cli-unification/plan.md"
related_issues: []
related_prs: []
---

# QA Test Plan: CLI and models.toml unification (Refactor-6)

## Source of Intent

- TODO: `Core-Refactor-6` (`TODO.md`)
- Plan: `_docs/plan/Core/cli-unification/plan.md`
- Intent: `_docs/intent/Core/cli-unification/decision.md`

## Quality Goal

`cli.py` と `models.toml` が single source-of-truth から供給される状態を、既存挙動 (4 alias 動作、full-ID passthrough、reasoning_* サポート、logging、multi run) を全て保存したまま達成する。skill 利用者は現状同様 zero-install (Claude Code 登録のみ) で動作する。

## Acceptance Criteria

TODO Core-Refactor-6 の AC-001〜004 を採用。要旨:

- AC-001: cli.py と models.toml がそれぞれ single source-of-truth 化
- AC-002: skill 利用者が skill dir を取得した状態で skill CLI が動作 (repo 外 source 依存禁止)
- AC-003: `AGENTS.md` 記載検証コマンド 4 種すべて pass
- AC-004: behavior-preservation: 4 alias + full-ID passthrough + reasoning_* が Refactor 前後で同一動作

## Decision Review Scope

- [[cli-unification]] DEC-001 (skill dir を source-of-truth に)
- [[cli-unification]] DEC-002 (models.toml default + override)
- [[cli-unification]] DEC-003 (pip 経路格下げ)
- [[cli-unification]] DEC-004 (`src/cheap_opinion/` 削除)
- [[cli-unification]] DEC-005 (root `models.toml` 削除)
- [[cli-unification]] DEC-006 (bash wrapper 薄い launcher)

verification で各 DEC の `Why` と `Change freedom` に実装が沿うことを review する。特に「zero-install UX 保存」(DEC-003) と「single source-of-truth」(DEC-001, INV-001) の 2 つは実装方式が変わっても不変の結果として保つ。

## Intent-derived Invariants

- **INV-001** (from [[cli-unification]] DEC-001, DEC-002): cli.py と models.toml は各々単一 source-of-truth から供給される (drift 発生の余地を構造的に排除)
- **INV-002** (from [[cli-unification]] DEC-003): skill 利用者が skill dir を Claude Code に登録するだけで CLI が動作する (pip install 強制なし)

## Risk Assessment

- **Risk level**: Medium
- **Risk rationale**: リポジトリ構造の破壊的変更 (`src/` 削除、pyproject 再配線)。既存 CLI 挙動を壊す可能性がある。ただし削除対象は既存 skill 側 copy と機能同等 (skill 側は reasoning_* 未対応の drift のみ、Refactor で解消)。
- **Regression risk**: 高 — 既存の全 CLI 挙動 (単発、multi、logging、full-ID) がテスト対象。behavior-preservation checks を必須とする (TODO 規約 Category=Refactor 条件)。
- **Data safety risk**: 削除は `git rm` (revert 可能な形) で実施、user 承認必須 (AGENTS.md 遵守)。git 履歴で復元可能。
- **Security / privacy risk**: なし (内部 refactor、secret / auth / 外部 API 変更なし)。
- **UX risk**: SKILL.md 実行例が bash wrapper 経由なので変更不要。ただし `PYTHONPATH=src python -m cheap_opinion` を叩いていた開発者 flow は `PYTHONPATH=skills/cheap-second-opinion/scripts python -m cheap_opinion` に変わる可能性。README 更新が必要 (Docs スライスで扱う)。
- **Agent misbehavior risk**: 中 — coding agent が `src/` を復活させる誤操作、または 3 系統コピーに戻す修正を試みる可能性。intent doc + code コメントで意図明示。

## Test Strategy

- **Unit**: `default_models_file()` の探索順 (env / project root / package default) を mock ファイルシステムで確認、`importlib.resources` 経由 default 読み込み
- **Integration**: `AGENTS.md` 記載検証コマンド 4 種を Refactor 前後で実行、`models` 出力を diff で完全一致確認
- **E2E**: `cheap-opinion --dry-run` で単発 / multi の payload 生成、Refactor 前後で messages 内容の完全一致
- **Manual QA**: skill dir を Claude Code に別 project で登録して 1 セッション実行、bash wrapper 起動確認
- **Validator / static check**: `check-docs.sh`、`python -m compileall`、`grep -r "src/cheap_opinion" .` で src 参照残存確認 (残存 = 実装未完)、`grep "\[models\." models.toml` で 1 系統確認
- **Diff review**: [[cli-unification]] DEC-001..006 の `Why` に沿って PR review、削除は commit 分割で reviewable

## Test Matrix

| ID | Source | Requirement / Optional Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | TODO | cli.py / models.toml の source-of-truth 化 | Static + Unit | `find . -name cli.py -not -path './.venv/*' -not -path './.claude/*'` | 1 file のみ (`skills/cheap-second-opinion/scripts/cheap_opinion/cli.py`) | planned |
| AC-002 | TODO | skill 単独取得で動作 | Manual QA + Integration | 別 dir で `skills/cheap-second-opinion/` を copy → bash wrapper 実行 | `models` 出力が repo 外でも同一 | planned |
| AC-003 | TODO | AGENTS.md 検証 4 種 pass | Integration | `python -m compileall`, `python -m cheap_opinion --help`, `python -m cheap_opinion models`, skill CLI `models` | 全 exit 0 | planned |
| AC-004 | TODO | behavior-preservation | Integration | Refactor 前 `cheap-opinion models` 出力を保存 → Refactor 後 diff | 完全一致 | planned |
| AC-004b | TODO | full-ID passthrough 保存 | Integration | `cheap-opinion --model deepseek/deepseek-v4-flash-0731 review --dry-run` | ModelConfig が Refactor 前後で同一 | planned |
| AC-004c | TODO | reasoning_* サポート保存 | Unit | ModelConfig の field 存在確認 + payload 生成 | Refactor 前 src と同じ `reasoning` blob | planned |
| INV-001 | [[cli-unification]] DEC-001, DEC-002 | single source-of-truth (drift の構造的排除) | Static | `find` + `grep` で cli.py / models.toml が 1 系統ずつ | 実装方式 (symlink / copy / restructure) に関わらず 1 系統 | planned |
| INV-002 | [[cli-unification]] DEC-003 | zero-install UX (pip install 不要) | Manual QA + Integration | 別 dir で bash wrapper 経由 `models` / `--help` 実行 | pip install しなくても pass、Core-Test-9 で継続監視 | planned |

## Manual QA Checklist

- [ ] skill dir 単独で Claude Code に登録して 1 セッション実行 (別 project の scratchpad で)
- [ ] `PYTHONPATH=skills/cheap-second-opinion/scripts python -m cheap_opinion models` が pass
- [ ] `src/cheap_opinion/` / root `models.toml` の削除 commit が reviewable (単独 commit、diff が明確)

## Regression Checklist

- [ ] `cheap-opinion review --model kimi-k3 --dry-run` 出力が Refactor 前と一致
- [ ] `cheap-opinion multi review --models kimi-k3,v4-flash-0731 --dry-run` 出力が一致
- [ ] `cheap-opinion ask --template design --model kimi-k3 --dry-run "test"` 出力が一致
- [ ] `cheap-opinion logging status` 出力が一致
- [ ] `CHEAP_OPINION_MODELS_TOML=/custom/path.toml cheap-opinion models` で env var override が機能
- [ ] `./scripts/check-docs.sh` が Refactor による新規 error / WARN を出さない (pre-existing のみ)

## Out of Scope

- preset mechanism 実装 (Core-Enhance-8、`_docs/qa/Core/preset-mechanism/test-plan.md`)
- 配布形態 smoke test CI (Core-Test-9)
- SKILL.md ↔ CLI --help diff check CI (Docs-Doc-10)
- Windows 対応
- Claude Code plugin 化 (`.claude-plugin/plugin.json` 追加)

## Open Questions

- `pyproject.toml` の `[tool.setuptools.packages.find]` を `where` 変更で対応するか、`[tool.setuptools.packages]` で explicit list 指定するか。実装時に決定 (どちらでも INV-001 は満たせる)。
- 現行 `src/cheap_opinion/prompts.py` は skill 側 copy と完全同一か、drift ある場合の diff は Refactor 実装時に確認する。
