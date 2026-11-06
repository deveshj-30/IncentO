# IncentiveTrap Progress and Handoff

## How to Update This File

This file is the durable handoff for humans and replacement coding assistants. Use `progress.md` (the requested `progress.mf` is treated as a typo).

- Each person owns only their P1/P2/P3/P4 section; P2 owns shared status. Keep headings stable and do not rewrite another person's notes.
- Update after a meaningful milestone, at least hourly, and before ending a session or approaching a token/context limit. Save unfinished work before the limit is reached.
- Use the serialized progress merge slots in `implementation_plan.md`. Commit code and its handoff together where practical; otherwise record the exact code commit/branch so the handoff can be matched to it.
- Record facts and command outcomes. Use `NOT STARTED`, `IN PROGRESS`, `BLOCKED`, or `DONE`; never mark planned work as complete.
- Include UTC timestamps, paths, reproducible commands, unresolved failures, and an exact next action. Never paste credentials or private customer records.
- If a code change is still uncommitted, list every changed/untracked path and how to recover it. A replacement on another machine needs a pushed branch or shared patch; local files alone are not a transferable handoff.

## Shared Status — P2 Maintains

- Last updated: 2026-11-07; documentation baseline (no implementation session started).
- Sprint start / eight-hour deadline: NOT SET; record UTC times at kickoff.
- Current phase: Phase 1 pending; implementation NOT STARTED. No phase gate has passed.
- Repository baseline: `AGENTS.md`, `.gitignore`, and four planning/handoff documents; `reference/` ignored. No initial commit existed when this baseline was inspected.
- Available application commands: None yet. Commands in the implementation plan are targets.
- Contract version: Proposed v1; not published or frozen.
- Latest integrated commit / PR: None.
- Verified features: None; no application code exists.
- Verification: Documentation reviewed; application build, tests, and live Hindsight checks NOT RUN.
- Assignments: P1/P2/P3/P4 human names pending.
- External setup: Hindsight Cloud account, API key, and bank isolation unverified (no live call yet). No LLM key needed because Cloud includes the models; Reflect `response_schema` fit unverified until G2. Git remote works (pushes to `origin/main` succeed). Content guide is in `reference/` and summarized in `implementation_plan.md`. Band AI desktop is deferred to final polish after G3.
- Decisions: Focus on acquisition incentives; React/TypeScript frontend, Python/FastAPI backend, SQLite records, Hindsight memory proposed. Separate clones, exclusive ownership, sequential merges, human-only commit attribution. Band AI desktop is used only for final polish after the skeleton works (no kickoff setup); articles and social posts are written at the end (Phases 6-7). Hindsight Cloud with one team account owned by P4 (banks `incento-<dev>-<scenario>` and `incento-demo-<scenario>`); no application-side LLM, explanations come from Reflect with `response_schema`. Explanation numbers: the model refers to results through metric tokens, P4 validates and substitutes them, proposal fields may hold labeled targets, and a failed explanation falls back to a labeled template. Memory timeline: records are retained only when known, live runs with an earlier `as_of` than the latest retained event are rejected (`409 as_of_before_memory`), recall results are post-filtered by event time, and retain is idempotent through `document_id`; no memory rewind. Analysis design: compare month-end deals against other deals for the policy's segment and channel, with a pre-policy baseline gap; three fixed metrics; status `flagged`/`watch`/`no_signal`/`insufficient_data` using interval lower bound above 0, a 10-point gap, and at least 30 deals per group (details in `implementation_plan.md`). API additions (to be written into `contracts/v1.md` at bootstrap): `memory_mode` on investigations, `analysis_digest`, incident endpoints, outcome retention retry, and a guarded demo reset; investigation ID equals `run_id`, and outcomes attach to incidents. Open question for organizers: per-member or per-team video.
- Next integration gate: Bootstrap and contract freeze at elapsed 0:45.
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

## P1 — Frontend

- Human owner: Unassigned.
- Status: NOT STARTED.
- Last update (UTC): Not started.
- Branch / worktree or clone path: Pending; intended branch `feat/p1-frontend`.
- Owned paths: `frontend/**`; this section only in shared documents.
- Current task: Build overview, investigation/evidence detail, and management outcome form.
- Completed: Nothing implemented.
- Files changed / uncommitted work: None.
- Last pushed commit / PR / integration status: None.
- Decisions and assumptions: Work against frozen v1 response fixtures; display synthetic-data and memory-status labels.
- Verification (exact command, directory, result): NOT RUN; tooling absent.
- Blockers / dependency requests: P2 contract examples and API base URL.
- Next actions: Read contracts; scaffold frontend; establish scripts and lockfile; render one fixture investigation.
- Resume notes: Do not scaffold backend or change shared API contracts. Own frontend dependency changes.

## P2 — Backend and Integration

- Human owner: Unassigned.
- Status: NOT STARTED.
- Last update (UTC): Not started.
- Branch / worktree or clone path: Pending; intended branch `feat/p2-api`.
- Owned paths: API/core/main/package bootstrap, integration tests, contracts, scripts, CI, shared configuration/documents; see ownership table for exact paths.
- Current task: Establish baseline, publish contracts, and coordinate integration.
- Completed: Planning documents committed and pushed to `origin/main`; no application code implemented.
- Files changed / uncommitted work: Documentation baseline is committed and pushed; inspect `git status --short` before staging. Assistant workspace directories (`.codex/`, `.claude/`) and the local `CLAUDE.md` are ignored via `.gitignore`; never commit private workspace state.
- Last pushed commit / PR / integration status: `6606516` pushed to `origin/main` (docs and ignore rules only); no PRs or integrated code.
- Decisions and assumptions: SQLite owns structured facts; Hindsight owns qualitative memory; only P2 changes backend dependency files.
- Verification (exact command, directory, result): Repository inspection confirms no application scaffold. Application checks NOT RUN.
- Blockers / dependency requests: Human assignments, runtime choices, Hindsight Cloud account and key (P4), answer on per-member versus per-team video.
- Next actions: Agree kickoff time; configure ignore rules; create reviewed baseline; publish v1 contracts and examples; bootstrap API and dependency files.
- Resume notes: Never stage all files blindly. Queue merges and progress updates sequentially. Leave `AGENTS.md` unchanged unless requested.

## P3 — Data and Analysis

- Human owner: Unassigned.
- Status: NOT STARTED.
- Last update (UTC): Not started.
- Branch / worktree or clone path: Pending; intended branch `feat/p3-analysis`.
- Owned paths: `backend/app/analysis/**`, `backend/tests/analysis/**`, `data/**`; this progress section.
- Current task: Generate linked synthetic datasets and deterministic cohort evidence.
- Completed: Nothing implemented.
- Files changed / uncommitted work: None.
- Last pushed commit / PR / integration status: None.
- Decisions and assumptions: Fixed observation windows; stable source IDs; no future events; no causal claims; thresholds are demo heuristics.
- Verification (exact command, directory, result): NOT RUN; tooling absent.
- Blockers / dependency requests: P2 data/result schemas and backend dependencies.
- Next actions: Specify hand-calculable expected metrics; create risk/control fixtures; implement `analyze`; test sparse and immature cohorts.
- Resume notes: Keep analysis free of HTTP, SQLite, and external model calls. Request dependencies through P2.

## P4 — Hindsight Memory and Demo

- Human owner: Unassigned.
- Status: NOT STARTED.
- Last update (UTC): Not started.
- Branch / worktree or clone path: Pending; intended branch `feat/p4-memory`.
- Owned paths: `backend/app/memory/**`, `backend/tests/memory/**`, `docs/demo/**`; this progress section.
- Current task: Implement real memory integration and a demonstrable learning loop.
- Completed: Nothing implemented; reference requirements reviewed during planning.
- Files changed / uncommitted work: None.
- Last pushed commit / PR / integration status: None.
- Decisions and assumptions: Keep facts, hypotheses, decisions, and measured outcomes distinct; verify recalled references and chronology.
- Verification (exact command, directory, result): NOT RUN; no live service tested.
- Blockers / dependency requests: Hindsight access/configuration, actual supported SDK methods, P2 contracts and dependency additions.
- Next actions: Verify official API documentation; prove real retain/recall; agree output schema; build adapter; demonstrate outcome persistence after restart.
- Resume notes: Never report a stub as live memory. Store environment-variable names and setup steps, never secret values. Prepare the demo script while integration proceeds.

## Replacement Session Checklist

1. Read `AGENTS.md`, `agent_help.md`, `implementation_plan.md`, and your section here.
2. Confirm assigned person, branch, worktree, latest commit, and actual `git status`; this document may lag behind code.
3. Read changed files and the current contracts. Check whether the last PR merged before continuing the same branch.
4. Run the last relevant verification command if available; preserve and investigate failures rather than assuming success.
5. Continue the recorded next action within owned paths. Coordinate missing contracts or cross-owner edits with P2.
6. Update this handoff before yielding, including a small recovery checkpoint if work is incomplete.
