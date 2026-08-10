---
title: "Intent: Preset schema, CLI surface, and output schema v1"
status: active
draft_status: n/a
intent_schema: 2
created_at: 2026-08-10
updated_at: 2026-08-10
references:
  - "_docs/intent/Core/preset-model-selection/decision.md"
  - "_docs/intent/Core/cli-unification/decision.md"
  - "_docs/plan/Core/preset-mechanism/plan.md"
  - "_docs/qa/Core/preset-mechanism/test-plan.md"
  - "AGENTS.md"
related_issues: []
related_prs: []
---

# Preset Schema, CLI Surface, and Output Schema v1

## Context

[[preset-model-selection]] で 3 preset (master / cheap / design) の含有モデル・除外モデルは確定した。本 intent は preset を実装する上での schema 設計 (models.toml 拡張、CLI surface、output 形式) を記録する。

主導原理は item 2 で確立した「preset の存在意義 = 主導 agent (Claude Code / Codex) の判断負荷を skill 側で吸収」。この原理から派生する schema 設計上の判断を、reviewer 指摘 (silent ignore 対策、schema versioning、drift 検知) と併せて明文化する。

## Decisions

### DEC-001: preset は `models.toml` 統合 (`[presets.<name>]`)

- **What**: preset 定義を独立ファイル (`presets.toml`) ではなく `models.toml` の `[presets.<name>]` セクションに置く。
- **Why**: source of truth を分散させない。alias 定義 (`[models.<alias>]`) と preset 定義は同じ運用単位 (削除は archive セクションへ、リネームは連動、defaults 参照は共通) で、責務分離のコストが得るものより大きい。CLI 側も 1 ファイルの parse で済む。
- **Change freedom**: 将来 preset 数が大きく増えて (10+) 可読性が破綻したら別ファイルに分離可能。分離時は探索順 (env → project root → package default) を `presets.toml` にも同ロジック適用。
- **Why not**: 別ファイル案は責務分離の抽象的美しさはあるが、実運用で「preset 更新のたびに 2 ファイル touch」が発生するコストと比較して却下。

### DEC-002: preset entry は inline 配列表記

- **What**: `[presets.master]` セクション + `models = ["v4-flash-0731", "gpt-5.6-luna", "kimi-k3"]` の inline 配列。sub-table (`[presets.master.models]`) は使わない。
- **Why**: 最小 schema。preset entry の必須 field は `models` + `description` の 2 つのみで、per-model meta (tier 等) を持つ根拠が現時点でない (DEC-003 参照)。
- **Change freedom**: 将来 per-model meta が要る要求が出れば sub-table に拡張可能 (breaking change なので schema_version bump 必要)。

### DEC-003: preset schema は tier を持たない

- **What**: `[presets.<name>]` に `models` (list) と `description` (str) のみ。`default_effort` や per-model tier は持たない。
- **Why**: [[preset-model-selection]] DEC-009 で reasoning tier は `[defaults].reasoning_effort = "high"` 統一が決着済。preset ごとに tier を差別化する要求が実測から出ていない。preset に tier を持たせると主導 agent が「どの tier を選ぶか」の判断を preset 選定と別に必要とし、item 2 原理と衝突する。
- **Change freedom**: 将来 preset 別に tier を差別化したい要求が出れば sub-table に拡張。実装コストは低い (mapping 追加のみ)。
- **Why not**: 「preset ごと per-model tier」案は user 判断負荷が preset 選定と tier 選定に二重化するため却下。

### DEC-004: alias 参照はフル alias 名

- **What**: preset の `models` list には models.toml の `[models.<alias>]` の `<alias>` をフルで書く (`"v4-flash-0731"` 等)。短縮 alias は導入しない。
- **Why**: alias 名の一意性 = source of truth の一意性。preset 記述と alias 定義で名前が一致することで、grep / rename の一貫性が保たれる。
- **Change freedom**: alias 名変更は preset の連動更新必須。behavior-preservation は Core-Refactor-6 の QA で担保。

### DEC-005: `--preset` は multi サブコマンド専用、`--models` と mutex

- **What**: `cheap-opinion multi review --preset <name>` / `cheap-opinion multi ask --preset <name>` でのみ受け付ける。単発 `review` / `ask` には受け付けない。`--preset` と `--models` の同時指定は起動時 error。
- **Why**: 単発 CLI は `--model X` で明示、multi は `--preset X` or `--models a,b,c` で明示、と surface を分離することで意図性を保つ。mutex は主導 agent が preset を base に個別追加/削除する運用 (item 2 原理と衝突) を防ぐ。
- **Change freedom**: 将来 preset を単発でも使いたい要求が出れば拡張可能 (implicit multi 化)。ただし preset 存在意義から離れる方向なので慎重に判断。
- **Why not**: 「単発でも `--preset` を許して 1 モデル目を選ぶ」案は preset の意図 (パネル選定) と単発 (単モデル選定) を混ぜて主導 agent の判断負荷が増えるため却下。

### DEC-006: preset 名 validate は起動時、fail fast

- **What**: 未定義 preset 名は起動時に models.toml 読み込み後即 error terminate。
- **Why**: multi 起動後に「preset 見つからない」で partial state を作らない。fail fast で cost 予防。
- **Change freedom**: error message の文言は自由。

### DEC-007: `--reasoning-effort` は pass-through + warning、`CHEAP_OPINION_STRICT_CONFIG=1` で strict

- **What**: CLI に `--reasoning-effort <val>` を追加、OpenRouter 側の受入値は skill が判断せず pass-through。既知 enum (low/medium/high/xhigh/max/minimal) 外は stderr に warning ログ、投入は継続。環境変数 `CHEAP_OPINION_STRICT_CONFIG=1` セット時のみ未知値を起動時 error にする。
- **Why**: OpenRouter の spec が provider ごとに拡張される可能性があり、skill が enum を hard-code すると provider 追従のたびに応急パッチが必要 (skill 修正で追従) となる。pass-through は「skill は provider 追従、値検証は OpenRouter に委ねる」設計判断。ただし完全 silent は reviewer 指摘の「silent ignore が真犯人」に該当するため、default で warning を出す。CI 等で strict が必要な場面は env var で opt-in。
- **Change freedom**: 既知 enum のリストは実装時に決定、追加は自由。warning ログの format は自由。
- **Revisit when**: OpenRouter が値 spec を安定化した (公式に enum 固定した) 時点で hard-code に切替検討。

### DEC-008: bare `multi` は `[defaults].preset` を暗黙適用

- **What**: `cheap-opinion multi review` / `cheap-opinion multi ask` で `--preset` も `--models` も無い場合、`[defaults].preset` (default 値: "master") を暗黙適用する。
- **Why**: `multi` サブコマンドを明示的に打っている時点で multi 実行意図は確定しており、preset 明示要求は判断負荷追加にしかならない (item 2 原理)。default 明示は models.toml で maintainer が制御可能。
- **Change freedom**: default preset を変更したい場合は `[defaults].preset = "cheap"` 等の 1 行編集で完結。CLI flag `--preset X` で単発 override 可能。
- **Why not**: 「error terminate で preset か models を明示強制」案は user 原理 (判断削減) と衝突するため却下 (2026-08-10 議論で明示的に前回推奨を撤回)。

### DEC-009: multi output は per-model 保持、normalize しない

- **What**: multi run の `runs[]` は各モデルの output を独立に保持。skill 側で findings の merge / dedupe / priority normalize は行わない。
- **Why**: 実測で priority calibration がモデル間で大きく異なる (GLM 全 P2、qwen 不安定、v4flash 鋭い、gpt 過大評価気味)。normalize すると各モデルの priority sense を失い、primary agent 側で判断できる情報を skill が捨てる形になる。
- **Change freedom**: 主導 agent 側で集約が必要な場合、下流で処理する。
- **Why not**: 「consensus / unique 分類 layer 追加」案は over-engineering と情報損失の両方をもたらすため却下。「skill 側で normalize」案は skill の判断で情報を捨てるため却下。

### DEC-010: output schema v1 で `schema_version` / preset metadata / effective_effort / usage を含める

- **What**: multi output JSON root に `schema_version: 1` (整数)、`summary.preset` (nullable str)、`summary.preset_description` (nullable str)、`summary.total_cost_usd` (nullable float)、`runs[].effective_effort` (nullable str)、`runs[].usage` ({prompt_tokens, completion_tokens, cost_usd}, nullable) を含める。
- **Why**: (1) schema_version で future breaking change 時に primary agent が version 検出可能に。(2) preset metadata で「どの preset で run したか」の縦断解析可能。(3) effective_effort で `--reasoning-effort` override の後追い可能。(4) usage で cost / token 集計可能。reviewer 指摘の「配布境界に drift が転移」対策の一部。
- **Change freedom**: schema_version bump は field 削除・型変更のみ (field 追加は non-breaking で v1 のまま)。cost_usd は OpenRouter 表示値 pass-through、実請求との乖離は認識のみ (README に注記予定)。
- **Why not**: schema_version を semver 化 (`"1.0"`) する案は現時点で minor version 区別の要求がないため簡潔さで整数採用。

### DEC-011: models.toml 探索順は env var → project root → package default

- **What**: `default_models_file()` の探索順を (1) env var `CHEAP_OPINION_MODELS_TOML` → (2) project root `./models.toml` → (3) package default (`importlib.resources` で skill dir 内同梱) とする。user home config (`~/.config/cheap-opinion/models.toml`) は追加しない。
- **Why**: `default + override` 意味論の実装形。project 単位で override できる余地を残しつつ、user home config は cheap-second-opinion の想定利用シナリオ (単一 project 想定) では over-engineering。3 系統コピー問題は「意味論の整理」で解消される (Core-Refactor-6 と連動)。
- **Change freedom**: user home config が必要になれば探索順 (2) と (3) の間に挿入可能 (後方互換保持)。
- **Why not**: 「env var のみ」案は project 単位の override 余地を失う。「user home 含む 4 段」案は cheap-second-opinion の想定利用者数 (単一 maintainer 前提) で over-engineering。

### DEC-012: `[defaults].last_reviewed` を preset / モデル陳腐化の見直し起点にする

- **What**: models.toml `[defaults]` に `last_reviewed = "YYYY-MM-DD"` を持ち、maintainer が「モデル向上を体感した」タイミングで比較起点にする。定期見直し trigger は設けない。
- **Why**: モデル世代交代は非線形で予測困難。定期見直しは trigger としてノイズになる (陳腐化していないのに review が発火する / 陳腐化しているのに次の定期を待つ)。maintainer が使っているうちに「向上した」と体感するのが最も信頼できる trigger であり、判断基準として `last_reviewed` から今日までの差分で「この頃と比べて向上している」を評価できるようにする。
- **Change freedom**: 見直し scope (preset 内訳 / alias / doc 含む) は maintainer 判断。
- **Why not**: 「四半期定期 review」案は maintainer の運用実態 (時間投資できる時に集中対応) と乖離するため却下。「trigger 記載なし」案は将来「なぜ更新されないのか」が不明瞭になるため却下。

### DEC-013: `[archived_models]` 空セクション declared で schema 明示

- **What**: models.toml に `[archived_models]` セクションを空で declared する。archive 対象モデルはここに `[archived_models.<alias>]` 形式で移送。TODO: 現時点で archive 対象なし、セクションは comment 付きで空。
- **Why**: schema を TOML 上に明示することで、将来 maintainer が「archive はここに書く」を認識できる。CLI 側で `archived_models` を optional 参照する robustness を持たせる。AGENTS.md "恒久削除禁止" 遵守 (削除ではなく格納) と [[preset-model-selection]] DEC-010 alias 追加基準 (preset 採用のみ) の運用を両立させる。
- **Change freedom**: セクション形式 (flat vs nested) は将来変更可能。
- **Why not**: 「セクション自体書かず、archive 発生時に追加」案は schema 明示性が失われ、将来 maintainer が archive 位置を推測する必要が生じるため却下。「comment placeholder のみ」案は TOML パーサーが認識しないため schema 明示性が中途半端。

## Consequences / Impact

- cli.py の実装拡張範囲: `--preset` / `--reasoning-effort` flag、preset 解決、mutex validation、`presets` subcommand、`[defaults].preset` 参照、`[archived_models]` optional 認識、output schema v1 化。
- models.toml の schema 拡張範囲: `[defaults].preset`、`[defaults].reasoning_effort`、`[defaults].last_reviewed`、`[presets.*]` 3 個、`[archived_models]` (空)、alias 整形 5 個、`[models."gpt-5.6-luna"]` 追加、命名 convention comment、default + override 意味論の comment。
- primary agent 向け SKILL.md 拡張: 3 preset 使い分けガイド (各 1 行) 追加。
- 実装は Core-Refactor-6 完了後 (単一 source-of-truth 化後) に着手が durable。

## Quality Implications

- schema_version 導入で future breaking change に対する contract を明示。
- pass-through + warning 方針は provider 追従の応急パッチ発生を予防。
- normalize しない方針は情報保全と judgment 委譲を primary agent 側に持たせる (skill 責務の最小化)。
- INV-001 (mutex) の Why: 併用を許すと preset の意図 (パネル選定を skill 側で吸収) と主導 agent 側でのパネル組み立てが混在し、item 2 原理 (判断負荷吸収) と衝突する。Change freedom: error message 文言・拒否手段 (argparse mutex or 手動 validation) は自由。Test: QA test-plan の INV-001 行で確認。

## Intent-derived Invariants

- INV-001 (from DEC-005): `--preset` と `--models` の同時指定は起動時に拒否される。実装方式が変わっても「同時指定は起動時に非受理」結果が保たれる。

## Rollback / Follow-ups

- schema_version bump は breaking change (field 削除・型変更) のみ (DEC-010)。field 追加は non-breaking で v1 維持。
- preset 実装後の drift 監視は Docs-Doc-10 (SKILL.md ↔ --help diff CI) で継続。
- output schema v1 の実 API run による `runs[].usage` / `runs[].effective_effort` 生成検証は Core-Test-9 (配布形態 smoke test CI) で継続。
- OpenRouter の `reasoning.effort` spec 安定化時は hard-code に切替検討 (DEC-007 Revisit when)。
