# Team Conversation and Handoff Log

Use this file for actionable handoffs between P1 (frontend), P2 (API/integration), P3 (data/analysis), and P4 (memory/demo). It is a durable record of requests, decisions, and replies, not a replacement for sending the message to its recipient. `progress/pN.md` remains each person's work status; P2 records contract freezes and phase gates in `progress.md`.

## Workflow

1. Send the message directly to the named teammate. Record it here with a UTC timestamp, sender, recipient, subject, exact request or decision, and the relevant commit, file, or gate. Mark it `SENT` only after delivery. Use `DRAFT` if it has not been sent.
2. The recipient replies directly, then records the response under the same entry with a UTC timestamp and a concrete result. Use `ACKNOWLEDGED`, `CHANGES REQUESTED`, `RESOLVED`, or `BLOCKED` as appropriate. Silence is never approval.
3. Link the implementation commit or updated handoff when resolving a request. For contract changes and phase gates, P2 also updates `progress.md`; this log alone does not freeze a contract or pass a gate.
4. Append new entries rather than rewriting another person's words. Each participant may append their own message or reply in a separate clone or branch. P2 coordinates merges of this shared file, one branch at a time, and resolves simultaneous additions without dropping either entry.
5. Keep secrets, private customer records, and raw credentials out of this file. Refer to a private channel without copying its contents.

## Entry template

### YYYY-MM-DD HH:MM UTC — Pn to Pn — Short subject

- Status: DRAFT | SENT | ACKNOWLEDGED | CHANGES REQUESTED | RESOLVED | BLOCKED
- Context: commit, path, contract slice, or gate
- Message: Exact request, decision, or information handed off.
- Requested next action: Owner and concrete deliverable.
- Reply (YYYY-MM-DD HH:MM UTC, Pn): Response and evidence, or `Pending`.

## Open handoffs known from repository records

These are requests recorded in handoff files. Their direct delivery is not verified here; the sender should send them and replace `DRAFT` with `SENT` and a real UTC time.

### Draft — P3 to P2 — Slice B fixture review and G1 status

- Status: ACKNOWLEDGED (by P2)
- Context: P3 Slice A review at `2dde205`; scenario drafts at `c992776`; P2's example fixes at `7013add`; `progress/p3.md` and `progress.md`.
- Message: P3 confirmed the Slice A shapes. P2 fixed the example evidence citations and `cancel_30d` status in `7013add`. The risk, outage, and sparse fixtures validate against the Dataset loader and need Slice B review. G1 remains in progress while P1 rechecks and P4 records confirmation and live Cloud proof.
- Requested next action: P2 reviews the fixtures with P4, tells P3 any Slice B changes needed, and records the Slice A freeze and G1 result in `progress.md` when their remaining checkpoints pass.
- Reply (2026-11-07 11:21 UTC, P2): ACKNOWLEDGED. Verified: `risk`, `outage` and `sparse` at `c992776` all load through the P2 fixture loader (references, duplicate IDs, synthetic-only), and `scripts/smoke_test.py` passes against each with stub analysis. No Slice B shape changes needed from P2. Slice A is NOT frozen: P1 has not yet rechecked the corrected example, and P4's confirmation is recorded only on the unmerged branch `feat/p4-memory`, not on `main`. Slice B reviewed commit will be recorded after P4 reviews the seeded history. G1 stays IN PROGRESS. See the P2 to P3 entry below for what `analyze` must satisfy.

## Entries

### 2026-11-07 11:21 UTC — P2 to P1 — Recheck the corrected example, then update your Slice A line

- Status: SENT (posted here on `main`; the lead confirmed this log is the delivery channel)
- Context: Slice A review at `2dde205`; fix at `7013add` on `main`; `progress/p1.md`; `progress.md` contract checkpoint.
- Message: Thanks for the review. `contracts/examples/investigation-response.json` now has matching `analysis.evidence` records for `DEAL-0188`, `DEAL-0191` and `CANCEL-0071`, and `cancel_30d` is `no_signal` (a 0.07 gap is below the 0.10 threshold). Two new tests (`test_example_evidence_is_self_consistent`, `test_example_metric_statuses_follow_the_decision_rule`) fail on the old file and pass on the fixed one. Your frontend passes the full `scripts/check.sh` on my side: lint, test, build and generated-types drift. Real scenario names are `risk`, `outage` and `sparse` (not the plan's names). Generated request types require `memory_mode` and `note` even though the API has defaults, so send them explicitly. The live backend flow needs P3's `analyze`; until then analysis is a labeled stub.
- Requested next action: P1 pulls `main`, rechecks the example, and updates the Slice A line in `progress/p1.md` to CONFIRMED (with the reviewed commit) or CHANGES REQUESTED with exact fields.
- Reply: Pending.

### 2026-11-07 11:21 UTC — P2 to P3 — What `analyze` must satisfy, and Slice B fixture review

- Status: SENT (posted here on `main`; the lead confirmed this log is the delivery channel)
- Context: `c992776` fixtures; `contracts/v1.md` section "Boundary guards"; `backend/app/core/guards.py`; `progress.md` contract checkpoint.
- Message: Thanks for confirming Slice A. It is not frozen yet (P1 recheck and P4's merged confirmation are pending). Your three fixtures load cleanly and need no shape changes from P2. Requirements for `analyze(dataset, policy_id, as_of) -> AnalysisResult`: (1) return `comparison_id` `month-end-v1`, so the incident ID is `inc-POL-RISK-001-month-end-v1`; (2) P2 rejects the analysis with a 500 unless `policy_id`, `as_of` and `scenario` match the request and dataset, each of the three metrics appears exactly once, every `Evidence.id` is a real dataset record ID, evidence IDs are unique, every ID cited by a metric or alternative appears in `analysis.evidence`, and no evidence is dated after `as_of`; (3) put `analyze` in `backend/app/analysis/service.py` and P2's module resolver picks it up automatically, then run `scripts/smoke_test.py --scenario risk`. Also: your seeded history has one prior incident with a fact and a rejected hypothesis. The demo needs `memory_mode` `off` and `live` to give different `action_type`s, so agree with P4 on a prior decision with a measured outcome. The plan's scenario file names differ from yours; P2 will update the plan.
- Requested next action: P3 implements `analyze` against these rules and coordinates the designed history with P4. P2 records the Slice B reviewed commit after P4's review.
- Reply: Pending.

### 2026-11-07 11:21 UTC — P2 to P4 — Integration problems found when merging `feat/p4-memory` with `main`

- Status: SENT (posted here on `main`; the lead confirmed this log is the delivery channel)
- Context: `feat/p4-memory` at `ef1e489` merged with `main` in a scratch worktree (not pushed). The combined test suite passes, but running P4's real module through P2's API showed the problems below. `backend/app/memory/service.py`, `backend/app/memory/hindsight_adapter.py`, `contracts/v1.md`.
- Message: Your Slice A and B confirmations are on `feat/p4-memory`; they count once the branch is merged to `main`, so please open the PR. Your handoff still says "ready for commit" although the branch is pushed. Findings: (1) Wrong bank on seed: `seed_history(incidents)` receives no scenario, so history was seeded into `incento-demo-default` while `explain` recalls from `incento-demo-risk`; a live run recalled nothing although seeding reported success. This is partly a P2 contract gap. P2 will pass `scenario` explicitly to both `seed_history` and `retain_outcome`; please accept it as a required argument with no default, or reply if you prefer another design. (2) Wrong bank on retain: `retain_outcome` derives the scenario by splitting `incident_id`, giving `incento-demo-POL`; use the scenario P2 passes. (3) False success: with no API key `retain_outcome` returns `retained` for data held only in a process-local dict, and `seed_history` returns `seeded` after a failed Cloud call. Return `failed` or `unavailable` with a reason such as `memory_not_configured`, so outcome status and the `as_of` guard stay truthful. (4) False labels: `explain` sets `explanation_source: reflect` and `memory_status: live` whenever a key is configured, but no Reflect call is made and recall silently falls back to the local dict. Use `reflect` only when Reflect's `structured_output` was used, and `live` only when this request's recall came from Cloud. G2 requires Reflect called with `response_schema`. (5) Recall quality: Cloud-recalled items are all typed `decision` and undated items get `as_of` as their event time; store `record_type` and event time as tags at retain time, and drop results without a timestamp. (6) Persistence: the local bank dict is lost on restart, so the G4 restart check cannot pass on it. P2 also replaces any explanation that cites unknown evidence or memories, recalls something dated after `as_of`, or recalls anything with `memory_mode` `off`; success should leave `validation_error_codes` empty.
- Requested next action: P4 replies to point (1), opens the PR, and fixes (2) to (6) in `backend/app/memory/`. P2 then adds `scenario` to the module calls and `contracts/v1.md`, and reruns the merged check.
- Reply: Pending.
- P2 update (2026-11-07 11:23 UTC, P2): The P2 side of point (1) is done on `main` at `571f089`. P2 now calls `seed_history(incidents, scenario)` and `retain_outcome(outcome, scenario)` with `scenario` as a required positional argument, and `contracts/v1.md` documents both signatures. P4's current `retain_outcome(outcome)` does not accept the second argument, so until it is updated every retention returns `failed` with `retention_error`. P4 must add the parameter and use it to build the bank name. Points (2) to (6) are still P4's.

### 2026-11-07 11:34 UTC — P2 to P1, P3, P4 — Slice A is frozen at `7013add`

- Status: SENT (posted here on `main`; the lead confirmed this log is the delivery channel)
- Context: `progress.md` contract checkpoint; confirmations in `progress/p1.md` (`feat/p1-contract-recheck`), `progress/p3.md` (`main`), `progress/p4.md` (`feat/p4-memory`).
- Message: All three Slice A confirmations are recorded, and the schema and contract artifacts are unchanged since `2dde205`, so P2 recorded Slice A as FROZEN at `7013add`. From now on Slice A changes are additive-only and go through P2 (`core/schemas.py`, regenerated contracts, a note here). Slice B is not frozen: it needs P3's fixture review, and confirmations from P1 and P3, by G2. The module signatures `seed_history(incidents, scenario)` and `retain_outcome(outcome, scenario)` are part of the contract in `contracts/v1.md`. G1 stays in progress: still open are P4's live Hindsight proof on `main`, git identity and push access for all four, and merging the P1 and P4 branches.
- Requested next action: P1 and P4 merge their branches so the confirmation lines reach `main` (P4 after answering the P2 to P4 entry above). P1 and P3 record a Slice B confirmation once P3's fixtures are reviewed. P3 and P4 record git identity and push access in their `progress/pN.md` if not already there.
- Reply: Pending.

