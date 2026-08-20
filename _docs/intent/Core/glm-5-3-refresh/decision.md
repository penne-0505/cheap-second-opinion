---
title: "Intent: Refresh the Z.ai design slot to GLM-5.3"
status: active
draft_status: n/a
intent_schema: 2
created_at: 2026-08-20
updated_at: 2026-08-20
references:
  - "_docs/intent/Core/preset-model-selection/decision.md"
  - "_docs/qa/Core/glm-5-3-refresh/test-plan.md"
  - "https://z.ai/blog/glm-5.3"
related_issues: []
related_prs: []
---

# GLM-5.3 Model Refresh

## Context

design preset の Z.ai 枠は GLM-5.2 を参照していた。Z.ai は 2026-08-14 に、GLM-5.2 と同じ base model へ追加 post-training を施し、coding と long-horizon task を改善した公式後継 GLM-5.3 を公開した。OpenRouter public API にも `z-ai/glm-5.3` が追加されたため、旧世代を固定して使い続ける理由を再検討する。

## Decisions

### DEC-001: Z.ai design 枠を GLM-5.3 へ世代更新する

- **What**: alias `glm-5.2` と OpenRouter ID `z-ai/glm-5.2` を、alias `glm-5.3` と `z-ai/glm-5.3` へ置き換える。design preset のモデル数・順序・他2モデルは維持する。
- **Why**: 同じ base model の公式後継が利用可能になった時点で旧世代を固定すると、後続 post-training による coding / long-horizon 改善を design review の別視点へ取り込めない。公開済みの exact model ID を採用し、存在しない将来 slug や moving alias には依存しない。
- **Change freedom**: Z.ai 枠は、OpenRouter で提供され、design preset の用途を満たす後継へ更新できる。alias は preset-model-selection DEC-010 の命名 rule に従う。モデル数と順序は別の roster 判断がある場合に変更できる。
- **Why not**: `z-ai/glm-latest` は将来の世代変更が明示的な review なしに入るため採用しない。GLM-5.2 と5.3の aliasを併存させる案は、preset 外 alias を増やさない DEC-010 と衝突する。
- **Revisit when**: GLM-5.3 の web design 出力が GLM-5.2 より明確に後退した場合、または OpenRouter で提供停止・後継移行が起きた場合。

## Consequences / Impact

- `glm-5.2` を明示指定していた利用者には alias breaking change となる。
- design preset は同じ3モデル構成を保ち、Z.ai 枠だけが GLM-5.3 へ進む。
- 過去の plan / verification にある GLM-5.2 表記は当時の証跡として保持する。

## Quality Implications

- active registry、README、preset-model-selection intent が同じ世代を指す必要がある。
- OpenRouter public API で exact model ID の存在を確認する。
- 有料API呼び出しを伴わない dry-run で alias と preset の解決を確認する。
- web design tier は独立再計測していないため、実運用で後退が観測された場合は DEC-001 を再検討する。

## Intent-derived Invariants

None

## Enforced in (optional)

- DEC-001: `skills/cheap-second-opinion/scripts/cheap_opinion/models.toml`

## Rollback / Follow-ups

- 回帰時は本 commit を revert し、registry / README / active intent を一体で GLM-5.2 へ戻す。
- design tier の再ベンチマークは今回の scope 外。実運用の後退が観測された場合に起票する。
