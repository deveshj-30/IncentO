# IncentO Progress and Handoff

## How to Update This File

This file holds the shared status and the phase gate tracker, and P2 maintains it. Each person's handoff lives in their own file: `progress/p1.md`, `progress/p2.md`, `progress/p3.md`, `progress/p4.md`. It is the durable handoff for humans and replacement coding assistants.

- Edit only your own file under `progress/`. No merge slot is needed because nobody else edits it; commit it with your feature branch. P2 owns this file. Do not rewrite another person's notes.
- Update after a meaningful milestone, at least hourly, and before ending a session or approaching a token/context limit. Save unfinished work before the limit is reached.
- Commit code and its handoff together where practical; otherwise record the exact code commit/branch so the handoff can be matched to it.
- Record facts and command outcomes. Use `NOT STARTED`, `IN PROGRESS`, `BLOCKED`, or `DONE`; never mark planned work as complete.
- Include UTC timestamps, paths, reproducible commands, unresolved failures, and an exact next action. Never paste credentials or private customer records.
- If a code change is still uncommitted, list every changed/untracked path and how to recover it. A replacement on another machine needs a pushed branch or shared patch; local files alone are not a transferable handoff.

## Shared Status — P2 Maintains

- Last updated: 2026-11-06T23:25Z; assignments and kickoff time recorded; implementation not started by the team (P2 backend skeleton is on `main`).
- Sprint start / eight-hour deadline: Start 2026-11-07 16:00 IST (10:30Z); deadline 2026-11-08 00:00 IST (2026-11-07 18:30Z). Times assume the team's local time is IST (UTC+5:30); correct this line if not. Gate targets (IST / UTC): G1 16:45 / 11:15, G2 18:00 / 12:30, G3 19:30 / 14:00, G4 21:00 / 15:30, G5 and feature freeze 22:00 / 16:30, G6 23:00 / 17:30, G7 00:00 / 18:30. Record actual UTC times at kickoff.
- Current phase: Phase 1 pending; implementation NOT STARTED. No phase gate has passed.
- Repository baseline: `AGENTS.md`, `.gitignore`, and four planning/handoff documents; `reference/` ignored. No initial commit existed when this baseline was inspected.
- Available application commands: None yet. Commands in the implementation plan are targets.
- Contract version: v1 Slice A is FROZEN at commit `7013add` (recorded 2026-11-07T11:34Z): additive-only changes from here, through P2 and `contracts/openapi.json` diff review. Slice B (dataset, incident, outcome shapes) is FROZEN at `9d9658a` (recorded 2026-11-07T13:12Z; P1, P3 and P4 confirmed). Schemas and generated contracts are unchanged since `7013add`.
- Latest integrated commit / PR: `0bd1544` on `main`. Merged PRs: #1 (P1 frontend shell, P3 scenario drafts, `487e0c0`), #2 (P4 memory module, `cdaab0d`), #3 (P1 Slice A confirmation, `221bdec`), #4 (P4 bank directives, `283b805`), P3 deterministic analysis (`817baab`), #6 (P1 Slice B UI, `0bd1544`). The real analysis and memory modules are bound (`stubbed_modules` is empty); Hindsight is not reachable from P2's machine (no key), so P2 ran the memory path in the adapter's simulation mode only.
- Verified features: None; no application code exists.
- Verification: Documentation reviewed; application build, tests, and live Hindsight checks NOT RUN.
- Assignments (GitHub usernames): P1 `anushkam-19`, P2 `doublerook777`, P3 `deveshj-30`, P4 `ayushrai-10`. Each person should fill the `Human owner` line in their own `progress/pN.md`.
- External setup: Hindsight Cloud account, API key, and bank isolation unverified (no live call yet). No LLM key needed because Cloud includes the models; Reflect `response_schema` fit unverified until G2. Git remote works (pushes to `origin/main` succeed). Content guide is in `reference/` and summarized in `implementation_plan.md`. Band AI desktop is deferred to final polish after G3.
- Decisions: Focus on acquisition incentives; React/TypeScript frontend, Python/FastAPI backend, SQLite records, Hindsight memory proposed. Separate clones, exclusive ownership, sequential merges, human-only commit attribution. Band AI desktop is used only for final polish after the skeleton works (no kickoff setup); articles and social posts are written at the end (Phases 6-7). Hindsight Cloud with one team account owned by P4 (banks `incento-<dev>-<scenario>` and `incento-demo-<scenario>`); no application-side LLM, explanations come from Reflect with `response_schema`. Demo reliability: fixed `action_type` set plus bank directives, a 4-of-5 repeat check for the off/live difference, `409 retention_pending` to avoid racing retention, a labeled known-good fallback, and a three-step learning-curve walkthrough. Explanation numbers: the model refers to results through metric tokens, P4 validates and substitutes them, proposal fields may hold labeled targets, and a failed explanation falls back to a labeled template. Memory timeline: records are retained only when known, live runs with an earlier `as_of` than the latest retained event are rejected (`409 as_of_before_memory`), recall results are post-filtered by event time, and retain is idempotent through `document_id`; no memory rewind. Analysis design: compare month-end deals against other deals for the policy's segment and channel, with a pre-policy baseline gap; three fixed metrics; status `flagged`/`watch`/`no_signal`/`insufficient_data` using interval lower bound above 0, a 10-point gap, and at least 30 deals per group (details in `implementation_plan.md`). API additions (to be written into `contracts/v1.md` at bootstrap): `memory_mode` on investigations, `analysis_digest`, incident endpoints, outcome retention retry, and a guarded demo reset; investigation ID equals `run_id`, and outcomes attach to incidents. Process: handoffs live in per-person files under `progress/` (no merge slots), and contracts freeze in two slices (A at G1, B at G2). P2 workload: a local `scripts/check.sh` replaces CI, owners merge their own single-owner PRs after one approval (P2 merges contract and shared-file PRs and gate commits), the top-level README is a thin index with folder READMEs written by owners, P4 owns `scripts/demo_check.py`, gate evidence lives in owners' files, and SQLite holds only run state while fixture files hold the business records. Contracts are generated from the Pydantic models in `core/schemas.py` (OpenAPI export, JSON schemas, generated TypeScript types) with drift checks in `scripts/check.sh`. Untrusted text: the model sees only evidence IDs, themes, and metric tokens (never raw customer text), nothing raw is retained into memory, outcome notes are capped and sanitized, and an injection canary fixture is tested at G5. UX: three screens (Overview, Investigation with a Compare memory tab, Incident timeline with the outcome form), always-visible synthetic-data, memory-status, and explanation-source badges, and honest loading and error states. Realistic data: P3 generates the fixture structure deterministically from a seed, and the surface text (names, ticket excerpts, narratives, logs) is written once with P3's own assistant and frozen in `data/text/`; hero records by G3, full text by G5, with a labeled template fallback. Video: one team video (team decision); not confirmed with the organizers, since the problem statement's wording says every member completes a video.
- Next integration gate: Bootstrap and Slice A contract freeze at elapsed 0:45 (16:45 IST).
- Release/demo links: Not available.

### Phase Gate Tracker — P2 Maintains

Exit checklists live in `implementation_plan.md`; this table records their verified results. Advance only when every checkpoint for the current gate passes. Allowed gate states: `NOT STARTED`, `IN PROGRESS`, `BLOCKED`, `PASSED`, `REOPENED`. A previously passed gate must reopen if a later change invalidates its evidence.

| Gate | Phase / target finish | Status | Reviewed commit | Evidence / reviewers / UTC time |
| --- | --- | --- | --- | --- |
| G1 | Foundation and contract freeze / 0:45 | IN PROGRESS | None | 2026-11-07T11:10Z: P2 `scripts/check.sh` passes on `main` with the frontend merged (backend lint and 53 tests (including P3's fixture tests), contract drift check, frontend lint, test, build, generated-types drift). Backend `/api/health` verified. 2026-11-07T11:34Z: Slice A FROZEN at `7013add`. 2026-11-07T11:40Z: P4's memory module merged (`cdaab0d`); `scripts/check.sh` on `main` passes (68 tests). Git identity and push access: P1 recorded, P3 recorded, P4 reports verified, P2 pushing to `main`. Open: P4's live Hindsight retain/recall proof is P4-reported in `progress/p4.md` and not independently verified by P2 (no API key); P1's confirmation reaches `main` when PR #3 merges. |
| G2 | Independently working modules / 2:00 | IN PROGRESS | None | 2026-11-07T12:29Z: P2 `scripts/check.sh` on `main` (`0bd1544`): 76 pytest tests, contract drift clean, frontend lint/test/build/types clean. Full flow with real P3 analysis and P4 memory through P2's API (`scripts/smoke_test.py --scenario risk`, simulation memory): all checks pass including the outcome flow. Open: 2026-11-07T12:53Z: re-check of P4's fixes on `main` (`b4dd142`): store path, empty recall when unavailable and the action enum are fixed; the off/live action difference is not driven by memory content, the fixture lacks P3's `HIST-RISK-DECISION`/`HIST-RISK-RESULT`, live Reflect output is discarded by the number rule, recalled IDs are duplicated, and the demo bank still holds test data (reset awaiting the lead's go-ahead). Slice B freeze waits for P3's line. |
| G3 | First integrated investigation / 3:30 | NOT STARTED | None | None |
| G4 | Persistent learning loop / 5:00 | NOT STARTED | None | None |
| G5 | Correctness and resilience / 6:00 | NOT STARTED | None | None |
| G6 | Release candidate and demo rehearsal / 7:00 | NOT STARTED | None | None |
| G7 | Final submission and handoff / 8:00 | NOT STARTED | None | None |

For each review, append a short record in this shared section:

```text
Gate / result / reviewed commit:
Reviewed at (UTC) / reviewers:
Checkpoint evidence: exact commands, working directories, results, run IDs, links
Failed or reopened checkpoints: owner, required fix, retest time
Scope changes or deferred optional work:
Next permitted phase / action:
```

Do not put secrets in evidence. A draft demo, mocked memory test, or unmerged feature branch cannot satisfy a checkpoint that requires live integration or a merged release.

### Contract Review Checkpoint — ACTION REQUIRED from P1, P3, P4 (P2 Maintains)

Slice A (and Slice B) are on `main` but **not frozen**. If you are P1, P3, or P4 (or their assistant), do this before building against the contracts, and before G1:

1. Read `contracts/v1.md`, `backend/app/core/schemas.py`, and `contracts/examples/*.json` (current `main`).
2. Check the items for your role below.
3. Record the result in **your own** `progress/pN.md` (you cannot edit other files), using one line: `Contract review: Slice A CONFIRMED` or `Contract review: Slice A CHANGES REQUESTED: <exact field, why, proposed change>`; add the commit you reviewed (`git rev-parse --short HEAD`) and UTC time. Tell P2 so the table below is updated.
4. "Confirmed" means you can build against the shapes as they are. It does not mean you found no flaws forever: after the freeze, changes are additive-only and go through P2. Do not edit `schemas.py` yourself.

| Role | Check before confirming |
| --- | --- |
| P1 | `npm run gen:types` runs on `contracts/openapi.json` and the generated types are usable; the `Investigation`, `AnalysisResult`, `Outcome`, and `Incident` fields cover the three screens and the Compare memory tab (including `analysis_digest`, `history_influence`, `recalled`, `explanation_source`, `memory_status`, `synthetic`). |
| P3 | You can produce every `AnalysisResult` and `MetricResult` field from your analysis (counts, intervals, `pre_policy_gap`, `status`, evidence IDs, alternatives, insufficient reasons); `Dataset` and its records can hold your fixtures (`data/scenarios/<scenario>.json`); metric names and thresholds match your design. **New rule:** `Evidence.id` must be the ID of a real dataset record (deal, ticket, cancellation, or seeded incident), every ID cited by a metric or alternative must be in `AnalysisResult.evidence`, and no evidence may be dated after `as_of`; see "Boundary guards" in `contracts/v1.md`. |
| P4 | `Explanation`, `Recommendation`, `RecalledMemory`, and `ExplainContext` can carry what Reflect returns; the metric token names in `contracts/v1.md` are right; the four signatures (`explain`, `retain_outcome`, `seed_history`, `reset_demo_bank`) and `HistoricalIncident` fit your adapter; confirm or replace the proposed `HINDSIGHT_API_KEY` and `HINDSIGHT_BASE_URL` names in `.env.example`. **New rules:** P2 replaces any explanation that cites unknown evidence or memories, recalls a memory dated after `as_of`, or uses memory while `memory_mode` is `off` with a labeled fallback; your adapter must refuse any bank not named `incento-demo-<scenario>` (P2 cannot enforce this); see "Boundary guards" in `contracts/v1.md`. |

| Reviewer | Slice A | Slice B | Reviewed commit | Recorded in / notes |
| --- | --- | --- | --- | --- |
| P1 | CONFIRMED | CONFIRMED | A: `3dad33d`; B: `8c43b84` | `progress/p1.md` on `main` (PR #3 `221bdec`, PR #6 `0bd1544`). |
| P3 | CONFIRMED | CONFIRMED | A: `2dde205`; B: `9d9658a` | `progress/p3.md` on `main` (recorded 2026-11-07T13:04Z, merged at `144086c`). P3's fixtures (`risk`, `outage`, `sparse`) load, and P3's `analyze` runs on them through P2's API. |
| P4 | CONFIRMED | CONFIRMED (shapes; before P3's fixtures) | `7013add` | `progress/p4.md`, now on `main` (PR #2, `cdaab0d`). |

**Slice A is FROZEN at `7013add`** (recorded 2026-11-07T11:34Z UTC). Basis: P1, P3 and P4 each recorded `Contract review: Slice A CONFIRMED`; `backend/app/core/schemas.py`, `contracts/openapi.json` and `contracts/schemas/` are unchanged since `2dde205` (checked with `git diff`), so the three reviews cover the same contract. The P1 and P4 lines are recorded on their unmerged branches (`feat/p1-contract-recheck`, `feat/p4-memory`); the confirmations stand, but they reach `main` only when those branches merge. Changes to Slice A are now additive-only: edit `core/schemas.py`, regenerate, and tell every consumer in `conversation.md`. Module signatures (`seed_history` and `retain_outcome` gained a required `scenario` argument at `571f089`) are documented in `contracts/v1.md` and tracked in `conversation.md`.

**Slice B is FROZEN at `9d9658a`** (recorded 2026-11-07T13:12Z UTC). Basis: P1 (`8c43b84`), P3 (`9d9658a`) and P4 (`7013add`) each recorded `Contract review: Slice B CONFIRMED`; `backend/app/core/schemas.py`, `contracts/openapi.json` and `contracts/schemas/` are unchanged since `7013add` (checked with `git diff 7013add HEAD`, empty), so the three reviews cover the same contract. Changes to Slice B are additive-only through P2, with notice in `conversation.md`. A slice is recorded as frozen only when every reviewer has a CONFIRMED line; silence is not confirmation.

## Per-Person Handoffs

- P1 — Frontend: `progress/p1.md`
- P2 — Backend and integration: `progress/p2.md`
- P3 — Data and analysis: `progress/p3.md`
- P4 — Hindsight memory and demo: `progress/p4.md`

## Replacement Session Checklist

1. Read `AGENTS.md`, `agent_help.md`, `implementation_plan.md`, and your own file under `progress/`.
2. Confirm assigned person, branch, worktree, latest commit, and actual `git status`; the handoff files may lag behind code.
3. Read changed files and the current contracts. Check whether the last PR merged before continuing the same branch.
4. Run the last relevant verification command if available; preserve and investigate failures rather than assuming success.
5. Continue the recorded next action within owned paths. Coordinate missing contracts or cross-owner edits with P2.
6. Update your handoff file before yielding, including a small recovery checkpoint if work is incomplete.
