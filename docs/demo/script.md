# IncentO — Demo Script (about 2 minutes 15 seconds)

One team video. All data is synthetic. The screen text below matches the app as built; do not change numbers or promise causation.

**Setup before recording** (see `README.md`, "Running the demo"): backend with the team key and a fresh `HINDSIGHT_BANK_SUFFIX`, `POST /api/demo/reset` once, frontend on port 5173, browser at 1440×810 or larger. The header must show `Synthetic data` and `Memory: live`. If Cloud is unavailable, record with `HINDSIGHT_SIMULATE=1` and say on screen that memory is simulated (`fixture`), never "live".

Two recordings are made with `docs/demo/record_demo.mjs` (captions only, no audio; add the voiceover below) and kept out of Git in `.local/demo/`:
- `incento-demo-fallback-fixture.mp4` — simulated memory, captioned "FALLBACK RECORDING, simulated memory (fixture), not live Hindsight". Use only as a labeled fallback.
- The live recording, made after Hindsight credits are topped up, on a fresh bank.

## Scene by scene

| Time | On screen | Voiceover |
|---|---|---|
| 0:00–0:17 | Overview, `Synthetic data` badge | "Sales teams often pay a bonus for month-end acquisitions. That can encourage heavy discounting, and organizations forget what they already tried. IncentO links the policy to deals, tickets and cancellations, and uses Hindsight to remember past decisions and results." |
| 0:17–0:30 | Click **Load and investigate** (Memory: Live) | "Step one: investigate the acquisition bonus policy with Hindsight memory on." |
| 0:30–0:50 | Overview metric cards | "These numbers come from code, not a model: 120 month-end deals against 880 others, with three flagged gaps of 15 points." |
| 0:50–1:15 | **Investigation**, evidence trail, then explanation | "Every claim cites a source record. Customer text is labeled untrusted and shown as plain text. The wording says associated, not caused. With seeded history the advice is a guardrail pilot, citing the remembered result HIST-RISK-RESULT." |
| 1:15–1:35 | **Compare memory**, click **Run with memory off** | "Step two: the same evidence with memory off. The calculated numbers match. Without memory the advice is to revert the policy. With memory it is to pilot a guardrail. The rejected hypothesis is recalled but never cited." |
| 1:35–1:50 | **Incident timeline**, type **Decision**, note, **Save outcome** | "Step three: record what management decided. It is saved and retained in Hindsight, with a retry button if retention ever fails." |
| 1:50–2:10 | Overview, As of `2026-11-08`, Memory Live, **Load and investigate**, then **Compare memory** | "Now investigate again at a later date. The decision we just saved, dated today, appears in the recalled history from Hindsight. The loop is closed." |
| 2:10–2:15 | Title card or last frame | "IncentO: calculated evidence, remembered outcomes, no causal claims. Powered by Hindsight." |

## Notes for the presenter

- **As-of date:** the outcome form stamps the decision with the current time, so the later investigation must use an `As of` date after today. A live run dated before a saved outcome is rejected with `as_of_before_memory`; that is intended.
- **Indexing delay:** after **Save outcome** wait about 15 seconds before the later investigation. Cloud indexes a new record shortly after it is retained; the earlier run may show nothing new.
- **Explanation source:** the screen says `Explanation: template` on purpose. Reflect's own text is rejected by the no-causation rule, so the labeled template is shown with real recalled history. Say so if asked.
- **What changes with memory:** the recommended action (`revert_change` to `pilot_guardrail`) and the cited record. The numbers never change.
- **Do not say** "caused", "proved" or "will reduce". Say "associated with", "followed by", "may".
- **Honest limits to mention if asked:** recall returns some, not always all, of the remembered records per run (Cloud relevance cutoff) but the cited record is stable; Hindsight Cloud needs credits; one team video, not confirmed with the organizers.
