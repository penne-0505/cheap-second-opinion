# cheap-second-opinion

OpenRouter-hosted modelsを、Codexの外部セカンドオピニオンとして呼ぶPoCです。

意図的に「native subagent」ではなく、非対話CLIをCodex skillからwrapする構成にしています。外部モデルには編集権限を渡さず、reviewや意見出しの結果だけを親agentが検証します。

## Skill Layout

Codex skillとしての配布単位は `skills/cheap-second-opinion/` です。Python CLIとデフォルトの `models.toml` はskillフォルダ内に同梱しているため、このフォルダだけをコピーしても動く構成です。

```text
skills/cheap-second-opinion/
├── SKILL.md
├── models.toml
└── scripts/
    ├── cheap-opinion
    └── cheap_opinion/
```

## Commands

```bash
SKILL_DIR="$(pwd)/skills/cheap-second-opinion"

"$SKILL_DIR/scripts/cheap-opinion" models
"$SKILL_DIR/scripts/cheap-opinion" review --model qwen-coder --format json
"$SKILL_DIR/scripts/cheap-opinion" ask --model kimi --file src/foo.ts "この設計の穴を見て"
"$SKILL_DIR/scripts/cheap-opinion" multi review --models qwen-coder,deepseek,kimi --format markdown
"$SKILL_DIR/scripts/cheap-opinion" multi ask --models qwen-coder,deepseek,kimi --template risk "この方針を再検討して"
"$SKILL_DIR/scripts/cheap-opinion" logging status
"$SKILL_DIR/scripts/cheap-opinion" logging enable
"$SKILL_DIR/scripts/cheap-opinion" logging disable
```

repo内で開発用packageとして実行する場合:

```bash
cd /path/to/cheap-second-opinion
PYTHONPATH=src python -m cheap_opinion models
PYTHONPATH=src python -m cheap_opinion review --model deepseek --format markdown
```

editable installする場合:

```bash
cd /path/to/cheap-second-opinion
python -m pip install -e .
cheap-opinion review --model deepseek --format markdown
```

複数モデルで同じ問いを並列実行する場合:

```bash
cheap-opinion multi review --models qwen-coder,deepseek,kimi --format json
cheap-opinion multi ask --models qwen-coder,kimi --template design "この設計判断の代替案は？"
```

`multi` は合議や多数決ではなく、複数の独立した視点を集めるためのモードです。1つのモデルが失敗しても他の結果は返します。全モデルが失敗した場合だけ終了コード `1` になります。

APIキーは環境変数で渡します。

```bash
export OPENROUTER_API_KEY="..."
```

## Model Aliases

`skills/cheap-second-opinion/models.toml`で短いaliasをOpenRouter model idへ割り当てます。model idはOpenRouter側で変わることがあるので、PoCでは編集しやすさを優先しています。

```toml
[models.qwen-coder]
provider = "openrouter"
model = "qwen/qwen3-coder"
```

別の設定を使う場合は、`--models-file` か `CHEAP_OPINION_MODELS_TOML` で上書きできます。

## Logging

ログはデフォルト無効です。対象repoのgit rootに `.second-opinion-poc/state.toml` が作られ、enable時だけ `.second-opinion-poc/logs/*.json` へ保存します。`review --repo /path/to/repo` はそのrepoのgit rootを使います。

```bash
"$SKILL_DIR/scripts/cheap-opinion" logging enable
"$SKILL_DIR/scripts/cheap-opinion" review --model qwen-coder
"$SKILL_DIR/scripts/cheap-opinion" logging --repo /path/to/repo enable
"$SKILL_DIR/scripts/cheap-opinion" review --repo /path/to/repo --model qwen-coder
"$SKILL_DIR/scripts/cheap-opinion" logging disable
```

ログにはprompt/responseが入るため、機密repoでは必要なときだけ有効化してください。

`multi` 実行時は複数モデル分のprompt/responseが1つの集約ログに入ります。ログ量と機密露出が増えるため、通常より慎重に扱ってください。

## Review Prompt

`review`はOpenAI Codex CLI OSSの `codex-rs/core/review_prompt.md` を参照し、PoC向けに再構成したpromptを使います。

元promptの要点:

- P0-P3の優先度
- diff上の短い位置指定
- discreteでactionableなbugだけを報告
- JSON schemaで出力
- patch生成はしない

全文コピーではなく、同じレビュー思想をこのPoC向けに短く実装しています。

Source: https://github.com/openai/codex/blob/main/codex-rs/core/review_prompt.md

## Skill Wrapper

Codex skill wrapperは `skills/cheap-second-opinion/SKILL.md` にあります。skill内の `scripts/cheap-opinion` が同梱CLIを起動します。
