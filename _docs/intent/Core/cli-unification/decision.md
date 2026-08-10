---
title: "Intent: Unification of cli.py and models.toml duplicates"
status: active
draft_status: n/a
intent_schema: 2
created_at: 2026-08-10
updated_at: 2026-08-10
references:
  - "_docs/intent/Core/preset-schema/decision.md"
  - "_docs/plan/Core/cli-unification/plan.md"
  - "_docs/qa/Core/cli-unification/test-plan.md"
  - "AGENTS.md"
related_issues: []
related_prs: []
---

# CLI and models.toml Unification (Refactor-6)

## Context

現状 cheap-second-opinion リポジトリは `cli.py` が 2 系統 (`src/cheap_opinion/cli.py` + `skills/cheap-second-opinion/scripts/cheap_opinion/cli.py`)、`models.toml` が 3 系統 (root / src / skill) 存在し、手動 sync が発生している。実際に drift が発生した (2026-08-10 時点、skill 側 cli.py が `reasoning_effort` field 未対応で放置されていた)。

本 intent は 3 方式候補 ((a) symlink / (b) build step / (c) restructure to `src/` + pip install) を外部 reviewer の指摘に基づき評価し、(d) 逆転案 = skill dir 側を単一 source-of-truth にする方式を採用した rationale を記録する。

主導原理は「二重管理を "防ぐ" ではなく "そもそも二重にしない" 根本解決」+ 「応急パッチ回避 / 長期安定性優先」。reviewer 指摘の Claude Code plugin 配布経路の仕様 (dir copy 挙動、agentskills.io 標準、Codex / claude.ai upload 互換) を判断基盤に据える。

## Decisions

### DEC-001: skill dir 側を単一 source-of-truth に (`(d)` 案採用)

- **What**: コード実体は `skills/cheap-second-opinion/scripts/cheap_opinion/` のみに置き、`src/cheap_opinion/` は削除する。pyproject.toml の `packages` mapping で `skills/cheap-second-opinion/scripts/cheap_opinion/` を wheel の `cheap_opinion` パッケージとして登録し、pip install 経路も温存する。
- **Why**: 二重管理を「防ぐ」ではなく「そもそも二重にしない」根本解決。cheap-second-opinion の repo 存在理由は skill そのものであり、Python packaging 慣習 (`src/` layout) より skill 配布実態を優先するのが repo の実態と整合する。skill 利用者は現状同様 zero-install (Claude Code に登録するだけ)、pip 経路は「開発者・外部利用者向けオプション」に格下げ。
- **Change freedom**: packaging tool (setuptools / hatchling / uv) は自由。wheel の package mapping 実装詳細も自由。`skills/cheap-second-opinion/scripts/cheap_opinion/` 内のモジュール分割は自由。
- **Why not (a) symlink**: Claude Code plugin install は plugin dir を copy し symlink を dereference する仕組み (公式仕様) だが、この救済は Claude Code 固有。zip 配布・claude.ai upload・Codex・Windows checkout (symlink がテキストファイル化する env) では保証がない。「構造で drift 不可能」を達成する代わりに「構造で配布可能」を経路依存にしてしまうため却下。
- **Why not (b) build step**: pre-commit hook or `scripts/sync-skill.sh` + CI sync check で drift を「merge 不可能」までは減らせるが「不可能」にはできない。plugin 配布が git repo 直取得である以上「生成物 commit せず release 時 assemble」変種は成立せず、commit ノイズが常態化する。誠実な次善案だが、根本解決には至らない。
- **Why not (c) `src/` + pip install (elected initial preference, revised)**: 「防ぐのではなく、そもそも二重にしない」の診断は正しいが処方が誤っていた。単一 source は `src/` である必要はない。(c) の欠点として (i) PEP 668 (最近の Homebrew Python / Debian で `pip install` が externally-managed error) の地雷、(ii) drift が SKILL.md ↔ PyPI CLI version 間の release ずれとして配布境界に転移する新軸を生む (「reasoning_effort 事件の再演」)。
- **Revisit when**: Claude Code plugin 配布仕様が大きく変わった時点、または cheap-second-opinion を独立 PyPI package として公開する要求が明確化した時点。

### DEC-002: `models.toml` は「default + override」意味論に降格

- **What**: 3 系統コピー (root / src / skill) を意味論の整理で解消する。default は package 内に 1 つだけ同梱 (`importlib.resources` で package `cheap_opinion` からロード)、上書きは実行時解決で env var (`CHEAP_OPINION_MODELS_TOML`) → project root `./models.toml` → package default の順で探索する。root と src の従来コピーは削除する。
- **Why**: 3 コピーを「同期すべき複製」として扱う限り drift は再発する。「default + override」に降格することで、コピーは 1 つ (package 同梱 default) + 実行時 optional override となり、drift の余地が消える。
- **Change freedom**: 探索順の追加段 (e.g. user home config) は将来必要になれば挿入可能 ([[preset-schema]] DEC-011 参照)。default toml の物理位置は package 内であれば自由。
- **Why not**: 「3 コピー sync script」案は build step (b) と同じ運用コストが継続するため却下。「実行時 override なし」案は project 単位のカスタマイズ余地を失うため却下。

### DEC-003: pip install は「開発者・外部利用者向けオプション経路」に格下げ

- **What**: pyproject.toml で pip install 可能性を温存 (`[project.scripts] cheap-opinion = "cheap_opinion.cli:main"`) するが、skill 利用者の主経路は現状どおり skill 登録のみで動作する zero-install を維持する。SKILL.md の実行例は skill dir 内 bash wrapper (`${CLAUDE_SKILL_DIR}/scripts/cheap-opinion`) 経由を primary とする。
- **Why**: 現行 UX (skill dir を Claude Code に登録するだけで動く) を保存。pip install を skill 利用者に強制すると PEP 668 地雷を踏むリスクがあり、UX 悪化と応急対応の温床になる。
- **Change freedom**: 将来 PyPI publish するかは自由。pip install 経路の Python version 制約 (`requires-python = ">=3.11"`) は自由。
- **Why not**: 「pip install 強制」案は PEP 668 と UX 変更のため却下。「pip install 経路完全削除」案は開発者・外部利用者の pip 経由試用可能性を無くし、Refactor-6 が preset 実装だけの局所化になるため却下。

### DEC-004: `src/cheap_opinion/` 削除、`skills/cheap-second-opinion/scripts/cheap_opinion/` を保持

- **What**: `src/cheap_opinion/cli.py`、`src/cheap_opinion/prompts.py`、`src/cheap_opinion/models.toml` を削除。`skills/cheap-second-opinion/scripts/cheap_opinion/cli.py` を最新版 (現行 src 版の reasoning_* サポート + preset 拡張後の実装) に更新して保持。
- **Why**: DEC-001 の帰結。single source-of-truth 化のために `src/` を消す必要がある。
- **Change freedom**: 移送後の module 分割は自由。
- **Why not**: 「src と skill 両方保持、CI で sync 検証」案は (b) build step 相当で応急対応、根本解決に至らない。
- **Operational note**: AGENTS.md "恒久削除禁止" に該当するため、削除は user 承認を都度取得する (J-2)。

### DEC-005: root `models.toml` 削除、skill dir 内 default に集約

- **What**: repo root の `models.toml` を削除。skill dir 内 (`skills/cheap-second-opinion/scripts/cheap_opinion/models.toml`) を package 同梱 default とし、`importlib.resources` 経由でロードする。
- **Why**: 3 系統コピーの解消 (DEC-002 の帰結)。root コピーは開発 mode で src override として機能していたが、default + override 意味論では project root `./models.toml` (実行時 CWD) が override 対象となり、repo root コピーは無用。
- **Change freedom**: default toml の package 内位置は自由。
- **Operational note**: 削除は user 承認 (J-2)。

### DEC-006: bash wrapper は薄い package launcher に留める

- **What**: `skills/cheap-second-opinion/scripts/cheap-opinion` bash wrapper は python module 起動 (`exec python "${SCRIPT_DIR}/cheap_opinion/cli.py" "$@"`) の薄い形を維持。python module `cheap_opinion` を `PYTHONPATH` に含めるための wrapper 経路も現状通り。
- **Why**: SKILL.md の実行例 (`"$SKILL_DIR/scripts/cheap-opinion"`) 互換保持。UX を変えない。
- **Change freedom**: bash → sh、python → uvx 等の切替は将来自由。ただし互換性のため慎重に検討。

## Consequences / Impact

- Refactor-6 の実装で以下が発生:
  - `src/cheap_opinion/` の 3 file 削除 (user 承認必要)
  - `skills/cheap-second-opinion/scripts/cheap_opinion/cli.py` を最新版 (reasoning_* サポート + preset 拡張後の実装) に更新
  - `skills/cheap-second-opinion/scripts/cheap_opinion/models.toml` を package default として同梱、`[archived_models]` セクション declared 追加
  - root `models.toml` 削除 (user 承認必要)
  - `pyproject.toml` の `[tool.setuptools.packages.find]` を新 layout 対応に更新 (`where` を `skills/cheap-second-opinion/scripts` に変更、または `packages = [...]` mapping で明示指定)
  - `[tool.setuptools.package-data]` を新 package 位置に対応
  - `default_models_file()` を `importlib.resources` 経由に書き換え、探索順を env var → project root → package default に
- `AGENTS.md` 記載の検証コマンド 4 種 (`compileall`, `--help`, `models`, skill CLI `models`) は Refactor 後に compileall のパス変更、python module 起動経路の確認が必要。
- Core-Enhance-5 (skill CLI reasoning back-port) は Refactor-6 完了で自動的に解消 (2 系統統合により差分そのものが消える)。TODO 記載通り「Refactor が長引く場合の応急パッチとしてのみ実行」の位置付けは Refactor 実行で不要化。

## Quality Implications

- INV-001 (single source-of-truth) は Refactor-6 完了後、preset 実装 (Core-Enhance-8) を含む後続変更で drift 発生の余地が構造的にゼロになる。
- INV-002 (zero-install UX) は Core-Test-9 (配布形態 smoke test CI) で継続監視する。
- SKILL.md ↔ CLI --help drift は Docs-Doc-10 で継続監視する。
- reviewer 指摘の「schema_version + strict parsing」は preset 実装側 ([[preset-schema]] DEC-007, DEC-010) で扱う。本 intent の scope 外だが同時期に対応する。
- INV-001 の Why: reasoning_effort drift 事件 (2026-08-10 に検知) の再発防止、二重管理を仕組みで排除。Change freedom: source-of-truth の物理位置 (skill dir 内 / 別 package / PyPI 経由) は将来変更可能。Test: CI grep で cli.py / models.toml が 1 系統ずつ、behavior-preservation として `models` 出力が Refactor 前後で同一。
- INV-002 の Why: 現行 UX 保存、pip install 強制は PEP 668 地雷とサポートコスト増。Change freedom: bash wrapper 実装・python module 起動経路の内部形は自由。Test: Core-Test-9 で bash wrapper 経由起動継続検証。

## Intent-derived Invariants

- INV-001 (from DEC-001): cli.py と models.toml は各々単一 source-of-truth から供給される (DEC-002 の default+override 意味論も同結果を保つ)。
- INV-002 (from DEC-003): skill 利用者が skill dir を Claude Code に登録するだけで CLI が動作する (pip install 強制なし)。

## Rollback / Follow-ups

- Refactor-6 revert は git revert で削除前 commit に戻せば src / root models.toml が復元可能 (git 履歴に残存)。
- Refactor 後の drift 継続監視: Core-Test-9 (配布形態 smoke test) + Docs-Doc-10 (SKILL.md ↔ --help diff)。
- Claude Code plugin 化 (`.claude-plugin/plugin.json` 追加) は現状 Non-Goal だが、将来 marketplace 配布時に別 TODO として起票検討。
- pip install `.` の wheel 生成挙動は PyPI publish 時に別途検証 (現時点は pip 経路格下げのため優先度低)。
