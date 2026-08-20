---
title: "QA Test Plan: GLM-5.3 model refresh"
status: active
draft_status: n/a
qa_status: planned
risk: Medium
qa_schema: 2
created_at: 2026-08-20
updated_at: 2026-08-20
references:
  - "_docs/intent/Core/glm-5-3-refresh/decision.md"
  - "_docs/intent/Core/preset-model-selection/decision.md"
related_issues: []
related_prs: []
---

# QA Test Plan: GLM-5.3 model refresh

## Source of Intent

- TODO: `Core-Enhance-11` (`TODO.md`)
- Plan: None (Size S)
- Intent: `_docs/intent/Core/glm-5-3-refresh/decision.md` DEC-001 and `_docs/intent/Core/preset-model-selection/decision.md` DEC-003, DEC-010

## Quality Goal

配布 skill の Z.ai design-preset 枠を、OpenRouter が提供する GLM-5.3 へ一貫して更新し、旧 alias や世代不一致による agent の誤選択を残さない。

## Acceptance Criteria

- AC-001: default registry の alias `glm-5.3` が `z-ai/glm-5.3` を解決し、`glm-5.2` は active registry に残らない。
- AC-002: design preset が `kimi-k3`, `glm-5.3`, `qwen3.8-max` をこの順で解決する。
- AC-003: README と active intent が GLM-5.3 の採用理由・現在の roster を示す。
- AC-004: AGENTS.md 所定の4コマンド、skill smoke test、dry-run が成功する。

## Decision Review Scope

- `_docs/intent/Core/glm-5-3-refresh/decision.md` DEC-001: 同じ Z.ai design 枠の世代更新として、公開済み OpenRouter ID を使うこと。
- DEC-003: design preset の用途と3モデル構成を保った世代更新であること。
- DEC-010: alias は preset 採用モデルだけに限定し、命名 rule に従うこと。
- `_docs/intent/Core/preset-schema/decision.md` DEC-012: `last_reviewed` が今回の見直し日を示すこと。

## Intent-derived Invariants

- None

## Risk Assessment

- **Risk level**: Medium
- **Risk rationale**: default agent skill のモデル解決先と preset roster を変更するため。
- **Regression risk**: alias / preset / docs の一部だけが旧世代に残ると、agent が存在しない alias を選ぶか、意図と実装が不一致になる。
- **Data safety risk**: なし。設定・文書のみで、ユーザーデータを変更しない。
- **Security / privacy risk**: なし。secret を扱わず、検証では課金API呼び出しを行わない。
- **UX risk**: `glm-5.2` を明示指定していた利用者には alias breaking change となる。full OpenRouter ID passthrough は継続する。
- **Agent misbehavior risk**: historical verification の 5.2 表記を active registry と誤認し、旧 alias を復活させる可能性がある。active config / README / intent と historical evidence を分離して review する。

## Test Strategy

- **Unit**: 既存 config parser で alias と preset を解決する。
- **Integration**: AGENTS.md 所定の4コマンドと skill smoke test を実行する。
- **E2E**: design preset の `multi ask --dry-run` で3モデルの request を生成し、外部APIには送信しない。
- **Manual QA**: `models` / `presets` 出力と OpenRouter public model list を照合する。
- **Validator / static check**: active config / README / intent の旧 alias 残存を検索し、`check-docs.sh` を実行する。
- **Diff review**: historical plan / verification が書き換えられていないこと、DEC-003 / DEC-010 に適合することを確認する。

## Test Matrix

| ID | Source | Requirement / Optional Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | TODO | `glm-5.3` → `z-ai/glm-5.3` | Static + integration | `cheap-opinion models` / `models.toml` | 5.3 alias と full ID が表示され、active config に 5.2 がない | planned |
| AC-002 | TODO | design preset の3モデル解決 | E2E dry-run | `cheap-opinion multi ask --preset design --dry-run test` | `kimi-k3`, `glm-5.3`, `qwen3.8-max` の3 request | planned |
| AC-003 | TODO | active docs の世代一貫性 | Static + diff review | `README.md`, preset-model-selection intent | roster と理由が5.3を示し、historical evidence は未変更 | planned |
| AC-004 | TODO | 配布 skill の起動と検証gate | Integration + validator | AGENTS.md 4 commands, `scripts/test-skill-smoke.sh`, `scripts/check-docs.sh` | 全コマンド exit 0 | planned |

## Manual QA Checklist

- [ ] OpenRouter public API に `z-ai/glm-5.3` が存在する。
- [ ] `models` と `presets` が `glm-5.3` を表示する。
- [ ] dry-run がネットワーク request を送らずに3モデルを解決する。

## Regression Checklist

- [ ] master / cheap preset は変更されていない。
- [ ] alias 総数は5のまま。
- [ ] active registry に `glm-5.2` が残っていない。
- [ ] 過去の plan / verification は当時の証跡として変更されていない。
- [ ] diff に secret や無関係な template migration 変更が含まれていない。

## Out of Scope

- GLM-5.3 の有料API実呼び出しと web design tier の再ベンチマーク。
- historical plan / verification の表記更新。
- preset mechanism や CLI schema の変更。

## Open Questions

- None
