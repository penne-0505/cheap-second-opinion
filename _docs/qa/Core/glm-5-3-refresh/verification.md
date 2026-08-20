---
title: "QA Verification: GLM-5.3 model refresh"
status: active
draft_status: n/a
qa_status: verified
risk: Medium
qa_schema: 2
created_at: 2026-08-20
updated_at: 2026-08-20
references:
  - "_docs/intent/Core/glm-5-3-refresh/decision.md"
  - "_docs/intent/Core/preset-model-selection/decision.md"
  - "_docs/qa/Core/glm-5-3-refresh/test-plan.md"
related_issues: []
related_prs: []
---

# QA Verification: GLM-5.3 model refresh

## Summary

default model registry と design preset の Z.ai 枠を `glm-5.2` / `z-ai/glm-5.2` から `glm-5.3` / `z-ai/glm-5.3` へ更新した。OpenRouter public API で exact model ID を確認し、alias / preset 出力、課金APIを呼ばない dry-run、skill単体 smoke test、docs validator を検証した。

## Verification Verdict

Verdict: PASS

## Commands Run

```bash
git diff --check
PYTHONPATH=skills/cheap-second-opinion/scripts python -m compileall -q skills/cheap-second-opinion/scripts
PYTHONPATH=skills/cheap-second-opinion/scripts python -m cheap_opinion --help
PYTHONPATH=skills/cheap-second-opinion/scripts python -m cheap_opinion models
./skills/cheap-second-opinion/scripts/cheap-opinion models
./skills/cheap-second-opinion/scripts/cheap-opinion presets
./skills/cheap-second-opinion/scripts/cheap-opinion multi ask --preset design --dry-run test
./scripts/test-skill-smoke.sh
./scripts/check-docs.sh
curl -fsSL https://openrouter.ai/api/v1/models | node -e 'let s="";process.stdin.on("data",d=>s+=d);process.stdin.on("end",()=>{const j=JSON.parse(s);if(!j.data.some(m=>m.id==="z-ai/glm-5.3"))process.exit(1)})'
if rg -n 'glm-5\\.2|z-ai/glm-5\\.2' skills/cheap-second-opinion/scripts/cheap_opinion/models.toml README.md; then exit 1; fi
```

Result:

```text
All commands exited 0. check-docs.sh reported schema-marker warnings already present for intent_schema / qa_schema, then passed validator fixtures and workflow checks. The active-registry/README old-alias search returned no matches.
```

## Automated Test Results

| Command / Test | Result | Notes |
| --- | --- | --- |
| `git diff --check` | PASS | whitespace error なし |
| AGENTS.md 所定の4コマンド | PASS | compileall / module help / module models / wrapper models が exit 0 |
| wrapper `presets` | PASS | design = kimi-k3 / glm-5.3 / qwen3.8-max |
| design preset dry-run | PASS | `moonshotai/kimi-k3`, `z-ai/glm-5.3`, `qwen/qwen3.8-max` の3 request を生成 |
| `scripts/test-skill-smoke.sh` | PASS | tmp dir へ skill 配布単位をcopyし、models / presets / help が成功 |
| `scripts/check-docs.sh` | PASS | validator fixtures、hook / skill sync checks が成功。schema marker は既存 validator の warning |
| OpenRouter public model list | PASS | `z-ai/glm-5.3` / `Z.ai: GLM 5.3` を確認 |
| active old-alias search | PASS | registry と README に `glm-5.2` / `z-ai/glm-5.2` なし |

## Manual QA Results

| Checklist Item | Result | Notes |
| --- | --- | --- |
| `models` と `presets` の表示確認 | PASS | alias / full ID / preset roster が5.3で一貫 |
| historical evidence の保持 | PASS | preset-mechanism plan / test-plan / verification は変更していない |
| 有料API呼び出しの回避 | PASS | public model list と `--dry-run` のみ使用 |

## Acceptance Criteria Coverage

| ID | Result | Evidence |
| --- | --- | --- |
| AC-001 | PASS | `models` が `glm-5.3: z-ai/glm-5.3` を表示し、active registry に5.2なし |
| AC-002 | PASS | `presets` と dry-run が `kimi-k3`, `glm-5.3`, `qwen3.8-max` を順番どおり解決 |
| AC-003 | PASS | README roster、専用 intent DEC-001、preset-model-selection DEC-003 を更新 |
| AC-004 | PASS | AGENTS.md 4 commands、skill smoke、dry-run、docs gate が成功 |

## Decision Conformance

| ID | Result | Why the implementation remains aligned |
| --- | --- | --- |
| glm-5-3-refresh DEC-001 | PASS | exact OpenRouter ID を使い、moving alias を避け、Z.ai枠だけを後継へ更新した |
| preset-model-selection DEC-003 | PASS | design preset の用途、3モデル構成、順序、他2モデルを維持した |
| preset-model-selection DEC-010 | PASS | preset外 alias を増やさず、`<series>-<version>` rule で5.2を5.3へ置換した |
| preset-schema DEC-012 | PASS | `last_reviewed` を実確認日 2026-08-20 へ更新した |

## Invariant Coverage

None

## Deferred / Not Covered

| ID | Reason | Follow-up |
| --- | --- | --- |
| GLM-5.3 web design tier 再ベンチマーク | モデルregistry更新の scope 外で、有料API呼び出しを避けた | 実運用で GLM-5.2 からの明確な後退が観測された場合に DEC-001 を再検討 |

## Residual Risks

None

## Follow-up TODOs

- None
