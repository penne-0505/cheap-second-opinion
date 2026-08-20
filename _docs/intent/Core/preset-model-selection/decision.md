---
title: "Intent: Preset model selection for cheap-second-opinion"
status: active
draft_status: n/a
intent_schema: 2
created_at: 2026-08-10
updated_at: 2026-08-20
references:
  - "_docs/intent/Core/preset-schema/decision.md"
  - "_docs/plan/Core/preset-mechanism/plan.md"
  - "_docs/qa/Core/preset-mechanism/test-plan.md"
  - "_docs/qa/Core/glm-5-3-refresh/test-plan.md"
  - "https://z.ai/blog/glm-5.3"
  - "AGENTS.md"
related_issues: []
related_prs: []
---

# Preset Model Selection

## Context

cheap-second-opinion は primary agent (Claude Code / Codex) が実装や設計判断で「別視点の意見」を取る skill である。preset を導入する動機は、モデル特性の判断負荷を skill 側で吸収し、主導 agent が「どのモデルを組み合わせるか」を毎回 re-inference しない状態を作ることにある。

本 intent は、2026-08-10 の実測 (rate limiter review task) と web design tier に関する maintainer の generative-task 実測 (Breakout game generation) をベースに、preset roster (master / cheap / design) と含有モデル、alias 追加基準、除外モデルの rationale を記録する。

含有・除外の判断根拠は 2026-08-10 時点のもので、モデル世代交代時 (半年周期の粗い推定) に再検討することを想定する。定期見直しの trigger は設けず、maintainer が「向上している」と体感したタイミングで [[preset-schema]] DEC-012 の `last_reviewed` 起点に見直す。

## Decisions

### DEC-001: `master` preset の構成

- **What**: `master = [v4-flash-0731 (high), gpt-5.6-luna (high), kimi-k3 (high)]`。default preset。
- **Why**: 3 ラボ (DeepSeek / OpenAI / Moonshot) の family diversity を確保、iteration しやすい速度感 (並列 wall ~26s)、合算コスト ~$0.016/run。「セカンドオピニオンが必要なとき、迷ったらこれ」を果たす。
- **Change freedom**: 3 モデルは差替可能。tier は `[[preset-schema]] DEC-006` の `[defaults].reasoning_effort` で管理、preset entry には持たない。ラボ diversity・並列 wall・コストの 3 制約が保たれる限り、モデルの入替は自由。
- **Why not**: 4 モデル案 (grok 追加) は grok が review shape で差別化なし (P2 flat) だったため却下。5 モデル案は wall/cost の iteration 敵性 (item 2 原理) から不採用。qwen 追加は DEC-008 参照。
- **Revisit when**: いずれかのラボが flagship 更新、または速度・コストが reviewer 期待と乖離した時点。

### DEC-002: `cheap` preset の構成

- **What**: `cheap = [v4-flash-0731 (high), gpt-5.6-luna (high)]`。
- **Why**: 2 ラボ (DeepSeek / OpenAI) を最小 diversity として維持しつつ最安価枠。「安く広く多発で意見が欲しいとき、探索や発想」を果たす。合算コスト ~$0.0019/run で単発 v4flash の $0.00047 との差は絶対値で無視でき、correlated error (同ラボ 2 モデルの盲点共有) を回避できる。
- **Change freedom**: 2 モデル差替可能。lab diversity と最安価枠の 2 制約が保たれる限り自由。
- **Why not**: 単発 `--model v4flash` で代替する案は preset の存在意義 (item 2 原理) と衝突するため却下。preset は主導 agent の判断負荷吸収であり、単発は代替にならない。v4flash x2 案 (同ラボ 2 モデル) は correlated error で diversity 目的を果たせず却下。
- **Revisit when**: v4flash と同等以下の cost で lab diversity を代替できる第 3 モデルが登場した時点、または探索 flow の実運用で lens 不足が判明した時点。

### DEC-003: `design` preset の構成

- **What**: `design = [kimi-k3 (high), glm-5.3 (high), qwen3.8-max (high)]`。
- **Why**: web / UI design taste 要求時の preset。Kimi K3 / GLM-5.2 / Qwen3.8-Max は maintainer 実測 (Breakout game generation) で上位グループだった。GLM-5.3 は GLM-5.2 と同じ base model に追加 post-training を施した公式後継で、Z.ai が coding と long-horizon task の改善を報告し、OpenRouter も `z-ai/glm-5.3` を提供したため、Z.ai 枠を旧世代に固定せず後継へ更新する。3 モデルとも CN lab (Moonshot / Z-ai / Alibaba) だが、design ability 純度を lab diversity より優先する意図的判断は維持する。
- **Change freedom**: モデル差替は上位 tier 内で自由。並列 wall (~84s、qwen 律速) は use case (design は 1 発本気、iteration しない) から許容範囲。
- **Why not**: v4flash (DEC-004)、grok (DEC-005)、gemini (DEC-006) の除外 rationale を各 DEC 参照。
- **Revisit when**: GLM-5.3 の web design 実測が GLM-5.2 より明確に後退した時点、design ability tier に新モデルが加わり上位相当と確認できた時点、または現 3 モデルのいずれかが陳腐化した時点。

### DEC-004: `v4-flash-0731` を design preset に含めない

- **What**: master / cheap に含めるが、design には含めない。
- **Why**: maintainer の web design tier 実測で v4flash は B tier。design ability の上位 3 モデル (K3=A+, GLM=A, Qwen=A) と混ぜると「安くて強い汎用モデル」の印象が preset キャラを希釈し、主導 agent が「じゃあ v4flash 単独でいいのでは」と判断を戻す誘因になる (item 2 原理と衝突)。
- **Change freedom**: v4flash 後継 (e.g. deepseek v5 flash) が design ability で A tier 相当に上がった時点で再検討可能。
- **Why not**: 「コスト・latency 無視できるから入れて損なし」案は、design preset の character 純度と主導 agent の判断削減原理を天秤にかけて後者を取る判断。
- **Revisit when**: deepseek 系が web design generation で A tier に到達した時点。

### DEC-005: grok 4.5 を全 preset で採用しない

- **What**: master / cheap / design いずれにも含めない。alias にも登録しない。
- **Why**: review shape 実測で grok 4.5 は max/high で挙動ほぼ同一 (35s vs 37.9s、finding 同一 A(P2)/B(P2))、tier が効いていない。priority 判定も flat で差別化なし。web design tier では maintainer 判定で B tier、かつ generative task で「executor として堅実だが UI design sense が確認されない」。3 preset いずれの用途タグにも lens contribution が見えない。
- **Change freedom**: xAI lab の後継 (grok 5 等) が review / design で明確な lens contribution を示した時点で再検討可能。
- **Why not**: xAI lab diversity 単独では preset に入れる根拠として弱い (maintainer 実測ベース + item 2 原理より)。alias 単発登録案も判断削減原理から却下 (6-5)。
- **Revisit when**: xAI 系の後継モデルが review or generative で差別化点を示した時点。

### DEC-006: gemini を全 preset で採用しない

- **What**: gemini 系 (3.6 flash / spark 1.2 / 3 pro 系列) を alias / preset に含めない。
- **Why**: maintainer 判定で gemini 3.6 flash はハルシネーション癖が残存、design ability は使用不可の gemini 3 pro に劣る。design preset の実測 lens contribution が期待できない。 v4flash とも比較して勝てる見込みがない。
- **Change freedom**: gemini 系の後継 (4.x 世代) が hallucination + design ability で明確に上位を示した時点で再検討可能。
- **Why not**: Google lab diversity 目的も、design preset で意味ある lens を出さないなら preset キャラを希釈するだけ (DEC-004 と同構造)。
- **Revisit when**: gemini 4.x 世代のリリース、または design ability 検証で A tier 到達を確認した時点。

### DEC-007: muse-spark 1.2 を alias / preset に含めない

- **What**: preset にも alias にも含めない。
- **Why**: maintainer 提示の web design tier で C tier 下段。preset 採用予定なし、単発検証需要も判断削減原理 (6-5) から full-ID passthrough で対応。
- **Change freedom**: 後継版で tier が上がった時点で再検討可能。
- **Revisit when**: 後継 (muse-spark 2.x 等) が上位 tier で登場した時点。

### DEC-008: qwen3.8-max を master preset に含めない

- **What**: design preset に含めるが、master には含めない。
- **Why**: 実測で qwen high は wall 83.8s (最遅) + cost $0.024 (最高価)、findings も v4flash / gpt / kimi と役割かぶり。master の目的 (iteration しやすい速度感) と正面衝突。qwen max では priority calibration が更に平準化して情報損失 (max 禁忌)。design では「発想寄り (A tier)」として lens contribution を持つ。
- **Change freedom**: qwen 後継が speed で v4flash 相当に改善した時点で master 再検討可能。
- **Why not**: Alibaba lab diversity 目的で master に入れる案は、既に master に 3 ラボあり iteration 敵性を優先する判断と衝突するため却下。
- **Revisit when**: qwen 系の速度改善版、または master preset の speed 予算が緩められる要求が出た時点。

### DEC-009: reasoning tier は全モデル `high` 統一、`max` 積極採用しない

- **What**: `[defaults].reasoning_effort = "high"` を全モデル default。alias 個別 override は当面不要。max / xhigh は escalate 的単発 (`--reasoning-effort max`) 用途のみ。
- **Why**: review shape 実測で 6 モデル (v4flash / k3 / gpt / grok / glm / qwen) 全てで max→high 移行に finding 損失なし (むしろ qwen は priority 改善)。max は 2.4-3.1x 時間・2-2.4x コストで追加 signal は薄い or ゼロ。
- **Change freedom**: alias 個別 tier 指定は将来必要になれば追加可能 (schema 拡張)。preset entry は tier を持たない ([[preset-schema]] DEC-003 参照)。
- **Why not**: 「preset ごとに tier を持つ」案 (5-3-ii) は user 判断負荷が preset 選定と tier 選定に二重化するため却下。「max default」案は実測から Pareto 劣位のため却下。
- **Revisit when**: reasoning-heavy な難タスク (debug 系) で max が明確に生きる場面が実測で確認された時点。escalate preset の別途起票を検討する。

### DEC-010: alias 追加基準 = preset 採用モデルのみ

- **What**: models.toml の `[models.<alias>]` セクションは、いずれかの preset (`master` / `cheap` / `design`) に採用されているモデルのみ登録する。preset 外の単発需要は CLI の full-ID passthrough (`--model deepseek/deepseek-v4-flash-0731` 等) で対応。
- **Why**: alias が preset 外に増えると主導 agent の「どれ選ぶか」判断肢が増え、preset の存在意義 (item 2 原理 = 判断負荷吸収) と直接衝突する。maintainer 検証需要は full-ID passthrough で満たせるため、alias 化に構造的な理由がない。preset 外れ時は [[preset-schema]] DEC-013 の `[archived_models]` に移送する (削除しない)。
- **Change freedom**: 命名 rule (`<series>-<version>[-<variant>]`、deepseek は vendor prefix 抜きの例外) は将来変更可能だが変更時は 5 alias 全ての整形が伴う。
- **Why not**: 「preset 外でも "使える" モデルは alias 化」案は maintainer 目線 (開発者 UX) の判断で、主導 agent 目線 (skill 利用者 UX) と衝突する。cheap-second-opinion の主 user は主導 agent なので後者を取る。
- **Revisit when**: full-ID passthrough が UX 上の障害になった時点、または命名 rule が実際の alias 増加で破綻した時点。

## Consequences / Impact

- 3 preset の合意により、cli.py 実装は preset 解決ロジック (alias 展開)、`--preset` mutex validation、bare multi での default preset 適用が必要 ([[preset-schema]] 参照)。
- alias 追加基準を preset 採用に絞ることで、models.toml のサイズが preset の union で決定的に定まる (現在 5 alias)。
- 除外モデル (grok / gemini / muse-spark) の rationale は将来「なぜ入れないのか」の再議論を防ぐ。maintainer の generative-task 実測が judgment の一次資料。

## Quality Implications

- preset 選定は maintainer の実測 (rate limiter review + Breakout generation) が判断基盤。preset 陳腐化リスクへの対応は models.toml の `last_reviewed` field (2026-08-10) を起点として maintainer 主導で行う。
- 除外理由は「絶対不可」ではなく「現時点で採用根拠が薄い」形。将来の後継モデル出現時に revisit できるよう `Revisit when` を各 DEC に明示している。
- 本 intent の decisions はすべて maintainer 判断で revisit 可能な設計選択であり、実装方式が変わっても守るべき「結果」ではない。preset roster 変更や alias 追加/削除はいつでも decision update で対応する。

## Intent-derived Invariants

None

## Rollback / Follow-ups

- preset 見直し trigger: DEC-012 の `last_reviewed` を起点、maintainer が「モデル向上を体感した」タイミング。GLM-5.3 は web design の独立再計測前なので、実運用で GLM-5.2 からの後退が見えた場合も再検討する。
- 除外モデル (grok / gemini / muse-spark) は各 DEC の `Revisit when` を trigger として再検討可能。
- alias 命名 rule (DEC-010) の変更は 5 alias 全ての整形を伴うため、変更時は breaking change として beta 段階で明示する。
