---
title: "QA Verification: CLI and models.toml unification (Refactor-6)"
status: active
draft_status: n/a
qa_status: partial
risk: Medium
qa_schema: 2
created_at: 2026-08-10
updated_at: 2026-08-10
references:
  - "_docs/intent/Core/cli-unification/decision.md"
  - "_docs/plan/Core/cli-unification/plan.md"
  - "_docs/qa/Core/cli-unification/test-plan.md"
related_issues: []
related_prs: []
---

# QA Verification: CLI and models.toml unification (Refactor-6)

## Summary

`src/cheap_opinion/` を削除、`skills/cheap-second-opinion/scripts/cheap_opinion/` を単一 source-of-truth とする Refactor-6 (d) 案の実装を検証した。`models.toml` は 3 系統から「default + override 意味論」に降格 (env var `CHEAP_OPINION_MODELS_TOML` → project root `./models.toml` → `importlib.resources` 経由 package default)。behavior-preservation は `models` 出力の baseline diff で完全一致確認。skill dir 単独で bash wrapper 経由 `models` 実行が pass、zero-install UX を保存。

## Verification Verdict

Verdict: PARTIAL

理由: 全 AC (001-004) / DEC (001-006) / INV (001-002) は構造検証で PASS。ただし Manual QA (別 project 上での skill 登録 → Claude Code session 実行) が tmp dir copy テストで structural 等価性を確認する形式に留まっているため、実 Claude Code 登録経路での動作は Core-Test-9 (配布形態 smoke test CI) で継続監視する。「pip install .」の wheel 生成挙動、agent misbehavior リスクも残るが、いずれも Follow-up TODOs (Core-Test-9 / intent 明示 / code comment) で対応済。qa-review skill の PARTIAL 定義 (「一部未確認だが残リスクと follow-up TODO が明示され、限定的に完了扱いにできる」) に合致。

## Commands Run

```bash
# Pre-implementation baseline
PYTHONPATH=src python -m cheap_opinion models > baseline/src-models.txt
./skills/cheap-second-opinion/scripts/cheap-opinion models > baseline/skill-models.txt

# Non-delete changes (Step B)
git mv skills/cheap-second-opinion/models.toml skills/cheap-second-opinion/scripts/cheap_opinion/models.toml
cp src/cheap_opinion/cli.py skills/cheap-second-opinion/scripts/cheap_opinion/cli.py
# + Edit: importlib.resources import, default_models_file rewrite, [archived_models] section
# + Edit: pyproject.toml packages.find where, AGENTS.md L21 PYTHONPATH

# Pre-delete verification (Step C)
PYTHONPATH=skills/cheap-second-opinion/scripts python -m compileall -q skills/cheap-second-opinion/scripts
PYTHONPATH=skills/cheap-second-opinion/scripts python -m cheap_opinion --help
PYTHONPATH=skills/cheap-second-opinion/scripts python -m cheap_opinion models  # matches baseline
./skills/cheap-second-opinion/scripts/cheap-opinion models  # matches baseline

# Deletion (Step E, user 実行)
git rm -rf src/cheap_opinion models.toml && rm -rf src

# Post-delete verification (Step F)
PYTHONPATH=skills/cheap-second-opinion/scripts python -m compileall -q skills/cheap-second-opinion/scripts
PYTHONPATH=skills/cheap-second-opinion/scripts python -m cheap_opinion --help
PYTHONPATH=skills/cheap-second-opinion/scripts python -m cheap_opinion models  # matches baseline
./skills/cheap-second-opinion/scripts/cheap-opinion models  # matches baseline
CHEAP_OPINION_MODELS_TOML=/nonexistent PYTHONPATH=skills/cheap-second-opinion/scripts python -m cheap_opinion models  # 'models file not found: /nonexistent' — env override 経路確認

# Additional verification (Step F+)
find . -name cli.py -not -path './.venv/*' -not -path './.claude/*' -not -path './.git/*' -not -path '*/__pycache__/*'  # 1 file only
find . -name "models.toml" -not -path './.venv/*' -not -path './.claude/*' -not -path './.git/*'  # 1 file only
# skill dir 単独動作テスト (別 tmp dir に copy → bash wrapper 実行 → baseline diff IDENTICAL)
# full-ID passthrough: resolve_model('deepseek/deepseek-v4-flash-0731', ...) → alias/model = 同 ID、provider=openrouter
# reasoning_effort payload build: ModelConfig.reasoning_effort='high' → payload に reasoning.effort='high'
./scripts/check-docs.sh  # 新規 ERROR/WARN 無し (残り全て pre-existing)
```

## Automated Test Results

| Command / Test | Result | Notes |
| --- | --- | --- |
| `compileall skills/cheap-second-opinion/scripts` | PASS (exit 0) | 新 layout で python bytecode 生成成功 |
| `python -m cheap_opinion --help` (new PYTHONPATH) | PASS | 全 subcommand 表示 |
| `python -m cheap_opinion models` (new PYTHONPATH) | PASS | baseline と完全一致 |
| skill wrapper `models` | PASS | baseline と完全一致 |
| env var override `CHEAP_OPINION_MODELS_TOML=/nonexistent` | PASS | 'models file not found: /nonexistent' → argparse 層 env var pickup 確認 |
| DEFAULT_MODELS_FILE 解決 | PASS | Post-delete で `importlib.resources` 経由 package default (`skills/.../scripts/cheap_opinion/models.toml`) にフォールバック |
| `resolve_model('deepseek/deepseek-v4-flash-0731', ...)` | PASS | full-ID passthrough で alias=同 ID / provider=openrouter |
| `find -name cli.py` | PASS | 1 file only (`skills/cheap-second-opinion/scripts/cheap_opinion/cli.py`) |
| `find -name models.toml` | PASS | 1 file only (`skills/cheap-second-opinion/scripts/cheap_opinion/models.toml`) |
| `ask --template design --model kimi-k3 --dry-run` | PASS | 2 messages 生成、template intent 反映 |
| `logging status` | PASS | 既存挙動維持 |
| `check-docs.sh` (Refactor 起因) | PASS | 新規 ERROR/WARN ゼロ |

## Manual QA Results

| Checklist Item | Result | Notes |
| --- | --- | --- |
| skill dir 単独で bash wrapper 経由 `models` 実行 | PASS | `mktemp -d` に skill dir を cp → `./scripts/cheap-opinion models` → baseline diff IDENTICAL |
| `src/cheap_opinion/` / root `models.toml` 削除 commit reviewable | PASS | user 承認済ワンライナー実行、git status で D 6 個 (`__init__`, `__main__`, `cli.py`, `models.toml`, `prompts.py`, root `models.toml`) が明示 |
| 別 project の scratchpad で skill 登録 → session 実行 | DEFERRED | Core-Test-9 で CI 自動化予定。本 verification では tmp dir copy テストで代替 |

## Acceptance Criteria Coverage

| ID | Result | Evidence |
| --- | --- | --- |
| AC-001 | PASS | `find -name cli.py` = 1、`find -name models.toml` = 1、single source-of-truth 達成 |
| AC-002 | PASS | tmp dir copy → bash wrapper 実行が baseline と IDENTICAL、依存が skill dir 内に閉じる |
| AC-003 | PASS | AGENTS.md 更新後の検証コマンド 4 種全て exit 0 で pass (compileall / --help / models / skill CLI models) |
| AC-004 | PASS | behavior-preservation: `models` 出力 baseline 完全一致、`resolve_model` full-ID 解決同一、`reasoning_effort` payload build 同一 (ModelConfig.reasoning_effort='high' → `{'effort': 'high'}`) |
| AC-004b (full-ID passthrough) | PASS | `resolve_model('deepseek/deepseek-v4-flash-0731', ...)` = alias/model/provider 同一 |
| AC-004c (reasoning_*) | PASS | ModelConfig に reasoning_effort/reasoning_max_tokens/reasoning_exclude field 存在、payload build で reasoning blob 生成 |

## Decision Conformance

| ID | Result | Why the implementation remains aligned |
| --- | --- | --- |
| DEC-001 (skill dir 側 source-of-truth) | PASS | `src/cheap_opinion/` 削除、`skills/cheap-second-opinion/scripts/cheap_opinion/` のみ残存。pyproject.toml `packages.find where = ["skills/cheap-second-opinion/scripts"]` で pip 経路も新位置対応。二重管理を「そもそも二重にしない」根本解決 |
| DEC-002 (default + override 意味論) | PASS | `default_models_file()` を `importlib.resources.files("cheap_opinion") / "models.toml"` フォールバック + `Path.cwd() / "models.toml"` project root override に書換。env var は argparse 層で継続処理。3 系統コピーは意味論の整理で消滅 (default 1 + override optional) |
| DEC-003 (pip 経路格下げ) | PASS | pyproject.toml `[project.scripts] cheap-opinion = "cheap_opinion.cli:main"` 温存、bash wrapper `skills/.../scripts/cheap-opinion` 実行経路変更なし、zero-install UX 保存 (tmp dir copy テストで確認) |
| DEC-004 (`src/cheap_opinion/` 削除) | PASS | 削除 5 files (`cli.py`, `prompts.py`, `models.toml`, `__init__.py`, `__main__.py`) + `__pycache__` + empty dirs、user 承認後 `git rm -rf src/cheap_opinion` 実行 |
| DEC-005 (root `models.toml` 削除) | PASS | 削除、`git rm -rf models.toml` 実行 |
| DEC-006 (bash wrapper 薄い launcher) | PASS | `skills/cheap-second-opinion/scripts/cheap-opinion` は現状の `exec python "$SCRIPT_DIR/cheap_opinion/cli.py" "$@"` を維持、変更なし |

## Invariant Coverage

| ID | Result | Evidence |
| --- | --- | --- |
| INV-001 (single source-of-truth) | PASS | `find -name cli.py` = 1、`find -name models.toml` = 1、`find -name prompts.py` = 1。実装方式に関わらず「単一である」結果を確認 |
| INV-002 (zero-install UX) | PASS | tmp dir に skill dir を cp して bash wrapper 経由 `models` 実行が baseline 完全一致、pip install 不要。Core-Test-9 で CI 継続監視予定 |

## Deferred / Not Covered

| ID | Reason | Follow-up |
| --- | --- | --- |
| Manual QA: 別 project の scratchpad で skill 登録 → session 実行 | tmp dir copy テストで structural 等価性を確認済、実際の Claude Code skill 登録セッションは manual 手順が長い | Core-Test-9 (配布形態 smoke test CI) で自動化継続監視 |
| Windows 対応 | Non-Goal (Plan に明記)、現状 Linux/Mac 前提 | 必要時に別 TODO 起票 |

## Residual Risks

- **Skill dir を別 project に登録した際の Claude Code 挙動**: Manual QA 未実行 (tmp dir copy による代替検証のみ)。Core-Test-9 で CI 自動化してから継続監視。実際の Claude Code skill 登録経路で問題が出た場合は Core-Refactor-6 の revisit が必要。
- **`pip install .` の新 packages.find 挙動**: pyproject.toml で `where = ["skills/cheap-second-opinion/scripts"]` に変更したが、実際に `pip install .` を実行して wheel が正しく生成されるかは未検証 (skill dir を source-of-truth とする DEC-003 で pip 経路は格下げされたため優先度低)。PyPI publish 時に別途検証。
- **agent misbehavior**: coding agent が「二重管理に戻す」修正を提案するリスク。Intent doc + `default_models_file` 内 comment (`# intent: DEC-002 ...`) + AGENTS.md 検証コマンド更新で予防、実際に発生した場合は intent doc 参照で reject。

## Follow-up TODOs

- **Core-Enhance-5** (skill CLI reasoning_* back-port): Refactor-6 完了で自動解消 (skill cli.py が src と完全同一 + reasoning_* fields 保有)。AC-001/AC-002 満たされたため、TODO から削除する。
- **Core-Enhance-8** (preset mechanism): Refactor-6 完了で hard dependency 解消、Ready phase へ移行可能。Phase 3 で実装。
- **Core-Test-9** (配布形態 smoke test CI): Refactor-6 完了後着手。INV-002 の継続監視を担う。
- **Docs-Doc-10** (SKILL.md ↔ CLI --help diff CI): Core-Enhance-8 完了後着手。
