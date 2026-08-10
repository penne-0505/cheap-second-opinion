---
title: "Intent: Preset mechanism (consolidation index)"
status: active
draft_status: n/a
intent_schema: 2
created_at: 2026-08-10
updated_at: 2026-08-10
references:
  - "_docs/intent/Core/preset-model-selection/decision.md"
  - "_docs/intent/Core/preset-schema/decision.md"
  - "_docs/plan/Core/preset-mechanism/plan.md"
  - "_docs/qa/Core/preset-mechanism/test-plan.md"
  - "AGENTS.md"
related_issues: []
related_prs: []
---

# Preset Mechanism (Consolidation)

## Context

Core-Enhance-8 (preset mechanism 実装) の decision は 2 side に分割されている:

- **モデル選定 rationale**: [[preset-model-selection]] — 3 preset (master / cheap / design) の含有・除外モデル、alias 追加基準、除外モデル (v4flash design / grok / gemini / muse-spark / qwen master) の Why not。
- **schema / CLI / output 設計**: [[preset-schema]] — models.toml `[presets.*]` 統合、`--preset` mutex、`--reasoning-effort` pass-through、output schema v1、`[archived_models]` declared 等。

本 index intent は、QA test-plan / verification (`_docs/qa/Core/preset-mechanism/*.md`) が canonical intent path (`_docs/intent/Core/preset-mechanism/decision.md`) を validator 要件として参照するための consolidation node であり、独自の decisions を持たない。全 DEC は上記 2 file に記載。

## Decisions

### DEC-001: preset mechanism intent は 2 file 分割 + index

- **What**: モデル選定 (preset-model-selection) と schema/CLI 設計 (preset-schema) を独立 intent doc とし、本 index (preset-mechanism) から consolidate する。
- **Why**: 2 側面 (モデル選定 = which models、schema = how to wire them) は revisit trigger が独立しており (前者は新モデル出現、後者は CLI UX 変更)、単一 file にまとめると変更履歴が絡み合って traceability が下がる。QA validator が canonical slug (`preset-mechanism`) の intent を要求するため、index を薄く残して 2 file への pointer とする。
- **Change freedom**: 分割数 (2 → N) と各 file の scope 境界は将来変更可能。ただし index は常に QA slug と同名で存在させる。
- **Why not**: 単一 file にまとめる案は revisit 追跡性の低下と file size 肥大化のため却下。QA slug 側を分割する案は plan / test-plan / verification の対応関係が複雑化するため却下。

## Consequences / Impact

- QA test-plan / verification (`_docs/qa/Core/preset-mechanism/*.md`) は本 index を references に含めることで validator 要件 (canonical intent path) を satisfy する。
- 実 decision は sub-intent 2 file を review する必要がある。primary reader (validator / agent) は本 index から始めて sub-intent へ辿る。

## Quality Implications

- 本 index は独自 decision を持たないため、QA test-plan の Decision Review Scope は sub-intent の DEC を直接引用する ([[preset-model-selection]] DEC-001..010 と [[preset-schema]] DEC-001..013)。
- index が薄い状態を保つこと (独自 decision を追加しないこと) が保守性に寄与する。追加 decision が必要になった場合は sub-intent 側に置く。

## Intent-derived Invariants

None

## Rollback / Follow-ups

- sub-intent (preset-model-selection / preset-schema) は独立 revisit 可能。本 index の rollback は sub-intent の rollback に従属する。
- 将来 preset 実装が大幅に見直される (別 mechanism 移行等) 場合、本 index 経由で sub-intent を obsolete 化した上で新 intent を作成する。
