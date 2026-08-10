---
title: "Plan: CLI and models.toml unification (Refactor-6)"
status: active
draft_status: n/a
created_at: 2026-08-10
updated_at: 2026-08-10
references:
  - "_docs/intent/Core/cli-unification/decision.md"
  - "_docs/qa/Core/cli-unification/test-plan.md"
  - "TODO.md"
related_issues: []
related_prs: []
---

<!-- Canonical path: _docs/plan/Core/cli-unification/plan.md -->
<!-- 対応 TODO: Core-Refactor-6。preset 実装 (Core-Enhance-8) の hard dependency。 -->

## Overview

cheap-second-opinion リポジトリの二重管理 (`cli.py` 2 系統、`models.toml` 3 系統) を単一 source-of-truth 化する。方式は [[cli-unification]] DEC-001 で採択の (d) 案 = skill dir 側を source にし、pyproject.toml の package mapping で pip 経路も温存、models.toml は「default + override」意味論に降格。

## Scope

- `src/cheap_opinion/` の 3 file (`cli.py`, `prompts.py`, `models.toml`) 削除 (user 承認必要)
- `skills/cheap-second-opinion/scripts/cheap_opinion/cli.py` を最新版 (現行 src と機能同等 = reasoning_* サポート、full-ID passthrough を含む) に更新
- `skills/cheap-second-opinion/scripts/cheap_opinion/prompts.py` を src と同一に更新
- `skills/cheap-second-opinion/scripts/cheap_opinion/models.toml` を package default として保持
- repo root `models.toml` 削除 (user 承認必要)
- `pyproject.toml` の `[tool.setuptools.packages.find]` を新 layout 対応に変更 (`where = ["skills/cheap-second-opinion/scripts"]` または `[tool.setuptools.packages]` で明示指定)
- `[tool.setuptools.package-data]` の `cheap_opinion` を新位置 (`skills/cheap-second-opinion/scripts/cheap_opinion/models.toml`) に対応
- `default_models_file()` を `importlib.resources` 経由に書き換え、探索順を env var `CHEAP_OPINION_MODELS_TOML` → project root `./models.toml` → package default に変更
- `AGENTS.md` 記載検証コマンド 4 種の pass 確認 (path 変更対応)

## Non-Goals

- preset mechanism 実装 (Core-Enhance-8 で別実装)
- PyPI publish
- Windows 対応 (現状 Linux/Mac 前提維持、bash wrapper のみ)
- Claude Code plugin 化 (`.claude-plugin/plugin.json` 追加): 現状 project skill layout を保つ、将来別途検討
- user home config 探索
- symlink 方式 / build step 方式の実装: [[cli-unification]] で却下済

## Requirements

### Functional

- [cli-unification] DEC-001〜006 の全 decision を実装する。
- Core-Refactor-6 の AC-001〜004 を全て満たす。
- `skills/cheap-second-opinion/scripts/cheap-opinion` bash wrapper 経由での起動が現状同様に動作する (zero-install UX 保存)。
- `PYTHONPATH=<something> python -m cheap_opinion` 経由でも起動可能 (開発者経路)。

### Non-Functional

- 挙動保存 (behavior-preservation): 4 alias + full-ID passthrough + reasoning_* が Refactor 前後で同一に動作する。
- CLI 起動時間 regression 無し。
- git history 保持: `git rm` / `rm` 恒久削除は user 承認後に実行 (AGENTS.md 遵守)。

## Tasks

1. Refactor-6 の Intent / Plan / QA test-plan 揃っていることを確認 (揃っている)
2. `skills/cheap-second-opinion/scripts/cheap_opinion/cli.py` / `prompts.py` / `models.toml` を最新化
3. `pyproject.toml` の packages mapping / package-data を新 layout 対応に更新
4. `default_models_file()` を `importlib.resources` + 探索順変更に書き換え
5. `src/cheap_opinion/` 削除提案 → user 承認 → 削除
6. root `models.toml` 削除提案 → user 承認 → 削除
7. `AGENTS.md` 記載検証コマンド 4 種を pass 確認
8. QA test-plan の behavior-preservation checks で回帰確認
9. verification.md 作成 → TODO 削除

## QA Plan

- QA document: `_docs/qa/Core/cli-unification/test-plan.md`
- Risk level: Medium
- Test strategy:
  - Unit: `default_models_file()` の探索順テスト、`importlib.resources` 経由 default 読み込みテスト
  - Integration: `AGENTS.md` 記載 4 種検証コマンド (compileall / `--help` / `models` / skill CLI `models`)
  - E2E: `--dry-run` で multi_review / multi_ask の payload 生成
  - Manual QA: skill を Claude Code に登録して 1 セッション実行、bash wrapper の起動確認
  - Validator / static check: `check-docs.sh`
- Refactor category 必須の **behavior-preservation checks** を Test Matrix に含める: (i) `models` 出力が Refactor 前後で同一、(ii) `--dry-run` 出力の messages 内容同一、(iii) full-ID passthrough (`--model deepseek/deepseek-v4-flash-0731`) の解決結果同一。
- 影響する DEC: [[cli-unification]] DEC-001..006 全て。verification で Decision Conformance を確認。

## Deployment / Rollout

- リリース手順: PR で pyproject.toml + skill dir 内 cli.py 更新 + `src/` 削除 (別 commit で reviewable) を一括変更、CI で検証コマンド 4 種を pass 確認。削除操作は user 承認後 (J-2)。
- rollback: git revert で削除前 commit に戻れば src / root models.toml が復元する (git 履歴に残っている)。
- 監視: 特になし。
