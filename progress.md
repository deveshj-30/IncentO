# IncentiveTrap Progress and Handoff

## How to Update This File

This file holds the shared status and the phase gate tracker, and P2 maintains it. Each person's handoff lives in their own file: `progress/p1.md`, `progress/p2.md`, `progress/p3.md`, `progress/p4.md`. It is the durable handoff for humans and replacement coding assistants.

- Edit only your own file under `progress/`. No merge slot is needed because nobody else edits it; commit it with your feature branch. P2 owns this file. Do not rewrite another person's notes.
- Update after a meaningful milestone, at least hourly, and before ending a session or approaching a token/context limit. Save unfinished work before the limit is reached.
- Commit code and its handoff together where practical; otherwise record the exact code commit/branch so the handoff can be matched to it.
- Record facts and command outcomes. Use `NOT STARTED`, `IN PROGRESS`, `BLOCKED`, or `DONE`; never mark planned work as complete.
- Include UTC timestamps, paths, reproducible commands, unresolved failures, and an exact next action. Never paste credentials or private customer records.
- If a code change is still uncommitted, list every changed/untracked path and how to recover it. A replacement on another machine needs a pushed branch or shared patch; local files alone are not a transferable handoff.

## Shared Status — P2 Maintains

- Last updated: 2026-11-07; documentation baseline (no implementation session started).
- Sprint start / eight-hour deadline: NOT SET; record UTC times at kickoff.
- Current phase: Phase 1 pending; implementation NOT STARTED. No phase gate has passed.
- Repository baseline: `AGENTS.md`, `.gitignore`, and four planning/handoff documents; `reference/` ignored. No initial commit existed when this baseline was inspected.
- Available application commands: None yet. Commands in the implementation plan are targets.
- Contract version: Proposed v1 in two slices (Slice A due at G1, Slice B by G2); not published or frozen.
- Latest integrated commit / PR: None.
- Verified features: None; no application code exists.
- Verification: Documentation reviewed; application build, tests, and live Hindsight checks NOT RUN.
- Assignments: P1/P2/P3/P4 human names pending.
- External setup: Hindsight Cloud account, API key, and bank isolation unverified (no live call yet). No LLM key needed because Cloud includes the models; Reflect `response_schema` fit unverified until G2. Git remote works (pushes to `origin/main` succeed). Content guide is in `reference/` and summarized in `implementation_plan.md`. Band AI desktop is deferred to final polish after G3.
- Decisions: Focus on acquisition incentives; React/TypeScript frontend, Python/FastAPI backend, SQLite records, Hindsight memory proposed. Separate clones, exclusive ownership, sequential merges, human-only commit attribution. Band AI desktop is used only for final polish after the skeleton works (no kickoff setup); articles and social posts are written at the end (Phases 6-7). Hindsight Cloud with one team account owned by P4 (banks `incento-<dev>-<scenario>` and `incento-demo-<scenario>`); no application-side LLM, explanations come from Reflect with `response_schema`. Demo reliability: fixed `action_type` set plus bank directives, a 4-of-5 repeat check for the off/live difference, `409 retention_pending` to avoid racing retention, a labeled known-good fallback, and a three-step learning-curve walkthrough. Explanation numbers: the model refers to results through metric tokens, P4 validates and substitutes them, proposal fields may hold labeled targets, and a failed explanation falls back to a labeled template. Memory timeline: records are retained only when known, live runs with an earlier `as_of` than the latest retained event are rejected (`409 as_of_before_memory`), recall results are post-filtered by event time, and retain is idempotent through `document_id`; no memory rewind. Analysis design: compare month-end deals against other deals for the policy's segment and channel, with a pre-policy baseline gap; three fixed metrics; status `flagged`/`watch`/`no_signal`/`insufficient_data` using interval lower bound above 0, a 10-point gap, and at least 30 deals per group (details in `implementation_plan.md`). API additions (to be written into `contracts/v1.md` at bootstrap): `memory_mode` on investigations, `analysis_digest`, incident endpoints, outcome retention retry, and a guarded demo reset; investigation ID equals `run_id`, and outcomes attach to incidents. Process: handoffs live in per-person files under `progress/` (no merge slots), and contracts freeze in two slices (A at G1, B at G2). P2 workload: a local `scripts/check.sh` replaces CI, owners merge their own single-owner PRs after one approval (P2 merges contract and shared-file PRs and gate commits), the top-level README is a thin index with folder READMEs written by owners, P4 owns `scripts/demo_check.py`, gate evidence lives in owners' files, and SQLite holds only run state while fixture files hold the business records. Open question for organizers: per-member or per-team video.
- Next integration gate: Bootstrap and Slice A contract freeze at elapsed 0:45.
- Release/demo links: Not available.

### Phase Gate Tracker — P2 Maintains

Exit checklists live in `implementation_plan.md`; this table records their verified results. Advance only when every checkpoint for the current gate passes. Allowed gate states: `NOT STARTED`, `IN PROGRESS`, `BLOCKED`, `PASSED`, `REOPENED`. A previously passed gate must reopen if a later change invalidates its evidence.

| Gate | Phase / target finish | Status | Reviewed commit | Evidence / reviewers / UTC time |
| --- | --- | --- | --- | --- |
| G1 | Foundation and contract freeze / 0:45 | NOT STARTED | None | None |
| G2 | Independently working modules / 2:00 | NOT STARTED | None | None |
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
