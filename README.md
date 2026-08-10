# cheap-second-opinion

OpenRouter-hosted モデルを、Claude Code / Codex の外部セカンドオピニオンとして呼ぶ Skill です。

意図的に「native subagent」ではなく、非対話 CLI を skill から wrap する構成にしています。外部モデルには編集権限を渡さず、review や意見出しの結果だけを親 agent が検証します。

## Skill Layout

Skill としての配布単位は `skills/cheap-second-opinion/` です。Python CLI と デフォルトの `models.toml` は package 内 (`scripts/cheap_opinion/`) に同梱しているため、このフォルダだけをコピーしても動きます (Refactor-6 で single source-of-truth 化)。

```text
skills/cheap-second-opinion/
├── SKILL.md
└── scripts/
    ├── cheap-opinion              # bash wrapper
    └── cheap_opinion/
        ├── cli.py
        ├── prompts.py
        └── models.toml            # default alias / preset roster
```

最小限の運用ガイドは [`_docs/guide/cheap-second-opinion-usage.md`](_docs/guide/cheap-second-opinion-usage.md) にあります。

## Commands

### Preset (推奨)

`multi` サブコマンドは preset で組み合わせを選ぶだけで済みます。

```bash
SKILL_DIR="$(pwd)/skills/cheap-second-opinion"

"$SKILL_DIR/scripts/cheap-opinion" presets                            # preset 一覧
"$SKILL_DIR/scripts/cheap-opinion" multi review --preset master       # セカンドオピニオン、迷ったらこれ
"$SKILL_DIR/scripts/cheap-opinion" multi ask --preset cheap "..."     # 安く広く多発
"$SKILL_DIR/scripts/cheap-opinion" multi review --preset design       # web/UI design 判断
"$SKILL_DIR/scripts/cheap-opinion" multi review                       # bare = [defaults].preset (master) 暗黙適用
```

### 単発 (デバッグ・比較検証用)

```bash
"$SKILL_DIR/scripts/cheap-opinion" models                             # alias 一覧
"$SKILL_DIR/scripts/cheap-opinion" review --model v4-flash-0731 --format json
"$SKILL_DIR/scripts/cheap-opinion" ask --model kimi-k3 --file src/foo.ts "この設計の穴を見て"
"$SKILL_DIR/scripts/cheap-opinion" multi review --models v4-flash-0731,gpt-5.6-luna,kimi-k3 --format markdown
"$SKILL_DIR/scripts/cheap-opinion" logging status
"$SKILL_DIR/scripts/cheap-opinion" logging enable
"$SKILL_DIR/scripts/cheap-opinion" logging disable
```

### Reasoning Effort 一時 override

```bash
"$SKILL_DIR/scripts/cheap-opinion" --reasoning-effort max multi review --preset master
"$SKILL_DIR/scripts/cheap-opinion" --reasoning-effort medium ask --model kimi-k3 "..."
```

未知値は pass-through (stderr warning)、`CHEAP_OPINION_STRICT_CONFIG=1` で startup error に昇格。

### repo 内で開発用 package として実行

```bash
cd /path/to/cheap-second-opinion
PYTHONPATH=skills/cheap-second-opinion/scripts python -m cheap_opinion models
PYTHONPATH=skills/cheap-second-opinion/scripts python -m cheap_opinion review --model v4-flash-0731 --format markdown
```

### editable install

```bash
cd /path/to/cheap-second-opinion
python -m pip install -e .
cheap-opinion multi review --preset master --format json
```

`multi` は合議や多数決ではなく、複数の独立した視点を集めるためのモードです。1 つのモデルが失敗しても他の結果は返します。全モデルが失敗した場合だけ終了コード `1` になります。

API キーは環境変数で渡します。

```bash
export OPENROUTER_API_KEY="..."
```

## Preset Roster

デフォルトで 3 preset が定義されています ([_docs/intent/Core/preset-model-selection/decision.md](_docs/intent/Core/preset-model-selection/decision.md) 参照):

| Preset | 用途タグ | 含有モデル |
|---|---|---|
| **master** (default) | セカンドオピニオンが必要なとき、迷ったらこれ | v4-flash-0731 / gpt-5.6-luna / kimi-k3 |
| **cheap** | 安く広く多発で意見が欲しいとき。探索や発想 | v4-flash-0731 / gpt-5.6-luna |
| **design** | web / UI デザインの taste 判断が必要なとき | kimi-k3 / glm-5.2 / qwen3.8-max |

`--preset` と `--models` は mutually exclusive です。

## Model Aliases

`skills/cheap-second-opinion/scripts/cheap_opinion/models.toml` で短い alias を OpenRouter model ID へ割り当てます。命名 rule は `<series>-<version>[-<variant>]` (deepseek は vendor prefix 抜きの例外)。

```toml
[models."v4-flash-0731"]
provider = "openrouter"
model = "deepseek/deepseek-v4-flash-0731"
description = "堅実枠 / 既定。Opus 4.8 に肉薄する汎用推論・コード評価。"
```

Full OpenRouter ID (e.g. `openai/gpt-5.6-luna`) を `--model provider/name` として渡せば alias 未登録モデルも単発で使えます (full-ID passthrough)。

別の設定を使う場合は、`--models-file` か `CHEAP_OPINION_MODELS_TOML` で上書きできます。探索順は `CHEAP_OPINION_MODELS_TOML` → project root `./models.toml` → package default。

## Output Schema

`multi` の JSON 出力は `schema_version: 1` を持ちます。詳細は [_docs/intent/Core/preset-schema/decision.md](_docs/intent/Core/preset-schema/decision.md) DEC-010 参照。

## Logging

ログはデフォルト無効です。対象 repo の git root に `.second-opinion-poc/state.toml` が作られ、enable 時だけ `.second-opinion-poc/logs/*.json` へ保存します。`review --repo /path/to/repo` はその repo の git root を使います。

```bash
"$SKILL_DIR/scripts/cheap-opinion" logging enable
"$SKILL_DIR/scripts/cheap-opinion" review --model v4-flash-0731
"$SKILL_DIR/scripts/cheap-opinion" logging --repo /path/to/repo enable
"$SKILL_DIR/scripts/cheap-opinion" review --repo /path/to/repo --model v4-flash-0731
"$SKILL_DIR/scripts/cheap-opinion" logging disable
```

ログには prompt/response が入るため、機密 repo では必要なときだけ有効化してください。

`multi` 実行時は複数モデル分の prompt/response が 1 つの集約ログに入ります。ログ量と機密露出が増えるため、通常より慎重に扱ってください。

## Review Prompt

`review` は OpenAI Codex CLI OSS の `codex-rs/core/review_prompt.md` を参照し、PoC 向けに再構成した prompt を使います。

元 prompt の要点:

- P0-P3 の優先度
- diff 上の短い位置指定
- discrete で actionable な bug だけを報告
- JSON schema で出力
- patch 生成はしない

全文コピーではなく、同じレビュー思想を PoC 向けに短く実装しています。

Source: [OpenAI Codex review prompt](https://github.com/openai/codex/blob/main/codex-rs/core/review_prompt.md)

## Skill Wrapper

Skill wrapper は `skills/cheap-second-opinion/SKILL.md` にあります。skill 内の `scripts/cheap-opinion` が同梱 CLI を起動します。

## Development Workflow

このリポジトリでは [`TODO.md`](TODO.md) を未完了タスクの source of truth とし、[`_docs/documentation_guide.md`](_docs/documentation_guide.md) と `_docs/standards/` のドキュメント駆動開発ルールを使います。中規模以上またはリスクのある変更では、Plan / Intent / QA test-plan / verification を対応付けます。

ローカルのドキュメント検証は次で実行します。

```bash
./scripts/check-docs.sh
```

導入済み template revision は [`docs-template.lock.json`](docs-template.lock.json) に固定しています。後続 release を取り込む場合は、moving branch tip ではなく推奨 tag と full SHA を使い、同梱の `docs-template-migration` skill で project 固有の変更を保全します。
