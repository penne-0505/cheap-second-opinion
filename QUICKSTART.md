# Quickstart

このリポジトリで、人間と Codex / Claude Code / 汎用 coding agent が `TODO.md` と `_docs/` を読みながら開発を進めるための入口です。プロジェクトの機能と利用方法は [README.md](README.md) と [cheap-second-opinion usage guide](_docs/guide/cheap-second-opinion-usage.md) を参照してください。

## 1. 最初に読むファイル

- [AGENTS.md](AGENTS.md)
- [TODO.md](TODO.md)
- [_docs/documentation_guide.md](_docs/documentation_guide.md)
- [_docs/standards/documentation_guidelines.md](_docs/standards/documentation_guidelines.md)
- [_docs/standards/documentation_operations.md](_docs/standards/documentation_operations.md)
- [_docs/standards/quality_assurance.md](_docs/standards/quality_assurance.md)
- [_docs/standards/security_for_agents.md](_docs/standards/security_for_agents.md)

## 2. 開発 workflow

1. [TODO.md](TODO.md) で Goal / Scope / Acceptance Criteria / Risk を確定する。
2. `Size >= M` または `Risk >= Medium` のタスクでは Plan / Intent / QA test-plan を用意する。
3. 実装後、必要な verification を `_docs/qa/<Area>/<slug>/verification.md` に残す。
4. 一回限りの実装プロンプトを root に残さない。残す必要がある場合は `_evals/prompts/` 等に移し、非運用の履歴資料として明記する。
5. 導入済み template revision は [docs-template.lock.json](docs-template.lock.json) の tag と full SHA を source of truth とする。

### Agent lifecycle hooks

このリポジトリは Codex / Claude Code 向けの lifecycle hook を同梱しています。

- Codex: [.codex/hooks.json](.codex/hooks.json)
- Claude Code: [.claude/settings.json](.claude/settings.json)
- 共通 script: [scripts/agent-workflow-hook.mjs](scripts/agent-workflow-hook.mjs)

hook は docs を自動更新しません。

- `SessionStart`: docs-driven workflow context を再注入します。
- `UserPromptSubmit`: 現在の仮説を既知の証拠・反証候補と照合し、Goal / Scope / Non-Goals / Intent を再確認する短い context を毎プロンプト注入します。
- `PreToolUse`: 書き込み前に、根本原因、呼び出し元やデータフローなどの非局所影響、短期パッチと恒久策、互換性維持期間と根拠を確認します。`rm` / `git rm` / file deletion / sensitive file 操作は止めます。
- `Stop`: relevant change の完了時に、`qa-review` / `docs-cleanup` / `check-docs` の証跡と、反証・全体影響・長期保守性・残リスクのうち複数観点からの自己監査を確認します。

自己監査は合意済み Scope を拡張する権限ではありません。広い変更が必要なら、実装へ混ぜず提案として切り分けます。また hook は guardrail であり、テスト、QA evidence、verification の代替にはなりません。ターン数カウンターは持たないため、session 再開・compact・並行実行でも同じ event 契約で動作します。

初回利用時は各 agent の `/hooks` で内容を確認し、信頼してください。不要な場合は、hook 設定を無効化または削除してから使います。

### Documentation inventory

久しぶりの再開、handoff 探索、または docs が形だけになっていないか確認したい場合は、`docs-inventory` skill を使います。`docs-inventory` は read-only の棚卸しであり、archive や TODO 削除は行いません。整理を実行する場合は、棚卸し結果を確認してから `docs-cleanup` に進みます。

### 既存プロジェクトへ後付け導入する場合

既存 docs を一斉に検証対象にしないため、段階的導入スコープを設定します。

1. 導入時点の commit SHA または tag を baseline として控える。このリポジトリでは `ff0da513bc5d88d58aab62ea60a5b5a3fb6d08bc` を使う。
2. CI の環境変数に `DD_SCOPE_BASE: <baseline commit>` を設定する。これで、導入前から存在し、導入後も変更されていない docs を検証対象から外せる。
3. このリポジトリの CI は `DD_SCOPE_DIFF_FILTER: ACMR` も設定し、baseline から追加・コピー・変更・改名された docs を validator 対象にする。これにより、導入前から存在する docs も将来編集された時点で検証される。
4. `actions/checkout` で `fetch-depth: 0` を設定し、baseline commit を参照できるようにする。
5. スコープ対応 validator の実行に `--allow-env`（git 使用時はさらに `--allow-run=git`）を付与する。`scripts/check-docs.sh` は設定済み。
6. `TODO.md` は段階導入でも常に全体が検証対象である点に注意する。

詳細は [段階的導入スコープ](_docs/standards/documentation_operations.md) を参照してください。

### Fresh adoption の保全境界

導入 baseline `ff0da513bc5d88d58aab62ea60a5b5a3fb6d08bc` の時点で、`src/cheap_opinion/` の package runtime と `skills/cheap-second-opinion/` の self-contained distribution は、実装と model config が同一ではありません。docs-driven template の fresh adoption はこの既存状態を変更せず、runtime / distribution behavior の同期は scope 外とします。両者を同期する場合は、別タスクで behavior と model aliases の互換性を定義し、project test を伴わせてください。

### Template の継続更新

導入後の project へ新しい template release を統合する場合は、moving `main` ではなく推奨 tag を更新単位にします。

1. `docs-template.lock.json` から、前回取り込んだ tag と full SHA (`B`) を確認する。
2. 取り込む推奨 tag (`U`) を full SHA へ解決し、tag の付け替えがないことを確認する。
3. [`docs-template-migration`](.agents/skills/docs-template-migration/SKILL.md) skill を使い、`B -> U` の upstream 差分と、`B` から現在の project までのカスタマイズを three-way inventory にする。
4. `U` の配布ファイルを reconciliation し、compatibility checks が成功した後に、lock を最後の migration write として `U` の tag と full SHA へ更新する。closure verification では更新後の lock を確認する。
5. strict schema migration を延期した場合は、lock ではなく migration verification に状態と follow-up を残す。

`v1.0.0` より前に導入された project は lock と local migration skill を持たない場合があります。その場合は project 固有ルールを安全境界とし、対象 `U` に含まれる skill を外部入力として先にレビューします。repository history、導入記録、upstream と一致する blob から最後に採用した template commit `B` を復元し、owner 確認後に移行します。`v1.0.0` を中継する必要はなく、`v1.0.0` 以降の任意の推奨 tag へ直接移行できます。`B` を推測でしか決められない場合は、書き込み前に停止します。

`DD_SCOPE_BASE` は導入先 repository 内で validator の対象を絞る値です。upstream template revision を示す `docs-template.lock.json` とは用途が異なります。詳細は [template revision provenance](_docs/standards/documentation_operations.md) を参照してください。

## 3. Agent に渡す初回プロンプト例

### Codex

```text
AGENTS.md、TODO.md、_docs/documentation_guide.md、_docs/standards/ を読んで、このリポジトリのドキュメント駆動開発ルールを把握してください。まず TODO.md の Backlog を確認し、最初に着手すべき小さなタスクを提案してください。
```

```text
qa-prepを実行して、対象タスクのDECごとのWhyとChange freedomを確認し、必要な場合だけintent-derived invariantを作ってtest matrixへ割り当ててください。
```

```text
実装後、qa-reviewを実行してverification verdictを出してください。
```

```text
docs-inventoryを実行して、TODO、intent、QA、guide、reference、draft/plan/surveyの棚卸しをしてください。自動整理はせず、次に判断すべき点を1-3件に絞ってください。
```

```text
docs-template-migrationを実行して、docs-template.lock.jsonのBと推奨tag Uをfull SHAで固定し、project固有変更を保全するthree-way migration計画を作ってください。互換移行とstrict schema移行は別に判定してください。
```

### Claude Code

```text
Read AGENTS.md, TODO.md, and _docs/documentation_guide.md first. Follow the documentation operations and security standard. Do not delete files with rm or git rm. Start by reviewing the initial TODO items and propose the first safe change.
```

### Generic Agent

```text
Use TODO.md as the task source of truth. For Size >= M or Risk >= Medium tasks, require Plan / Intent / QA test-plan. Keep intent and QA documents permanent, archive only draft/plan/survey after the archive checklist, and remove completed tasks from TODO.md only after verification.
```

## 4. TODO の開始点

[TODO.md](TODO.md) の Backlog から対象を選びます。Backlog が空の場合は、新しい作業を schema に従って追加します。完了タスクは TODO から取り除き、履歴は commit / PR / intent / QA verification に残します。

## 5. 検証コマンド

```bash
deno fmt --check scripts/*.mjs
deno run --allow-read --allow-env --allow-run=git scripts/validate-frontmatter.mjs
deno run --allow-read scripts/validate-todo.mjs
deno run --allow-read --allow-env --allow-run=git scripts/validate-doc-links.mjs
deno run --allow-read --allow-env --allow-run=git scripts/validate-intent.mjs
deno run --allow-read --allow-env --allow-run=git scripts/validate-qa.mjs
deno run --allow-read --allow-write --allow-env --allow-run scripts/test-validators.mjs
deno run --allow-read --allow-run=git scripts/test-agent-workflow-hook.mjs
deno run --allow-read scripts/test-agent-workflow-smoke.mjs
```

`--allow-env` / `--allow-run=git` は段階的導入スコープ（`DD_SCOPE_BASE`）向けの権限です。スコープ未設定なら全走査の従来挙動になります。まとめて実行する場合:

```bash
./scripts/check-docs.sh
```

CI では markdownlint と上記 Deno validator を実行します。手元で Node.js / npx が使える場合は、次の markdownlint も実行できます。

```bash
npx markdownlint-cli2 "_docs/**/*.md" "_evals/**/*.md" "README.md" "AGENTS.md" "TODO.md" "QUICKSTART.md" "!_docs/archives/**/*" "!_docs/standards/templates/**/*" --config .markdownlint.jsonc
```
