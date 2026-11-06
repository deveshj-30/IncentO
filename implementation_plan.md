# IncentiveTrap Implementation Plan

## Goal and Current State

Build an eight-hour hackathon MVP with four people, each using their own coding assistant. Help a Revenue Operations manager investigate whether acquisition-based commissions may be encouraging poor-fit SaaS deals. Connect numerical signals, customer feedback, and remembered incidents without claiming causation.

Current state: the documentation baseline is committed and pushed; the local `reference/` folder is ignored. No application, dependencies, or tests exist yet. Everything below is a proposed implementation. Person labels P1-P4 are placeholders to assign at kickoff.

## Deliverable and Scope

The demo must let a user load synthetic business data, run an investigation, inspect evidence, see relevant past experience, record a management response, and recall that response in a later investigation.

Must ship:

- One company, one acquisition incentive, and a reproducible dataset with policies, deals, support tickets, and cancellations.
- A risk overview and investigation detail showing cohort sizes, metric changes, source records, alternatives, and recommended next steps.
- Actual Hindsight Retain, Recall, and Reflect integration, with persistence across application restarts.
- A second scenario involving a product outage, where evidence does not justify blaming incentives.
- An outcome form and a subsequent investigation demonstrating how saved experience changes the recommendation.

Defer live CRM integrations, authentication, multi-company access, streaming infrastructure, autonomous policy changes, employee rankings, and financial-loss forecasts. Simulate incoming data with explicit replay batches; describe this as a replay demo rather than production continuous monitoring.

## Architecture

Proposed stack: React + TypeScript + Vite frontend; Python + FastAPI backend; SQLite for application records; Hindsight for persistent qualitative memory. Use one backend process and simple synchronous investigation requests with bounded external-call timeouts. Choose and pin compatible runtime and dependency versions during bootstrap.

```mermaid
flowchart LR
    UI[React dashboard] --> API[FastAPI routes and orchestration]
    Fixtures[Synthetic replay batches] --> API
    API --> DB[(SQLite: records, runs, decisions)]
    API --> Analysis[Deterministic cohort analysis]
    Analysis --> Evidence[Metrics and source IDs]
    Evidence --> Memory[Memory adapter and explanation workflow]
    Memory <--> Hindsight[Hindsight: Retain, Recall, Reflect]
    Memory --> API
    API --> UI
```

SQLite is the source of truth for structured records and run state. Hindsight stores policy context, incident narratives, hypotheses, decisions, and observed outcomes. Numerical results come from analysis code; generated explanations cannot replace calculated values.

### External services

- **Hindsight Cloud (decided).** One team account owned by P4; its LLM, embedding, and reranking models are included, so the application needs no LLM key. Self-hosting is not planned: it requires bringing your own LLM, and Groq's free tier (8,000 tokens per minute against roughly 64,000 for one retain call, per the Hindsight docs) is too small.
- **Banks.** Development banks are named `incento-<dev>-<scenario>`; demo banks are `incento-demo-<scenario>`. P4 confirms bank creation and isolation against the official documentation.
- **Explanations.** `explain()` calls Reflect with a `response_schema` (action, evidence-linked rationale, success metric, guardrail) and reads the `structured_output` field. P4 verifies at G2 that Reflect fills the agreed schema reliably and cites only retrieved memory IDs. If it cannot, record the failure and decide on a fallback with P2; do not add an application-side LLM silently.
- **Secrets.** The only backend secrets are the Hindsight API URL and key (placeholder names `HINDSIGHT_API_URL` and `HINDSIGHT_API_KEY`, plus `HINDSIGHT_BANK_PREFIX`; P4 confirms them against the SDK). They go in `.env.example` as placeholders at bootstrap, are shared privately, never committed, and are revoked after the event.
- **Credits.** The Hindsight site offers $5 of sign-up credit and the reference PDF gives promo code `MEMHACK99` for $50, applied in the billing section after registering. Check the balance before each rehearsal and before the live demo.

Planned layout and exclusive ownership:

| Owner | Paths | Responsibilities |
| --- | --- | --- |
| P1: frontend | `frontend/**` | Screens, API client, UI types, component tests, frontend manifest and lockfile |
| P2: backend and integration lead | `backend/app/api/**`, `backend/app/core/**`, `backend/app/main.py`, `backend/app/__init__.py`, `backend/tests/integration/**`, `contracts/**`, `scripts/**`, `.github/**` | API, SQLite, orchestration, contracts, integration, release |
| P3: data and analysis | `backend/app/analysis/**`, `backend/tests/analysis/**`, `data/**` | Synthetic fixtures, cohort calculations, evidence extraction, analytical tests |
| P4: memory and explanations | `backend/app/memory/**`, `backend/tests/memory/**`, `docs/demo/**` | Hindsight adapter, prompts, memory tests, demo script and recording checklist |

P2 alone owns remaining shared files: backend dependency/lock files, root configuration, `.gitignore`, `.env.example`, `README.md`, and these planning documents. `AGENTS.md` stays unchanged unless the user requests an update. Each person may edit only their own section in `progress.md` using the serialized workflow below. P2 owns its shared status section.

P2 may create package boundary files during bootstrap; ownership transfers when the bootstrap commit is merged. After that, no cross-folder fixes without explicit coordination. Each person owns tests beside their own module; avoid a shared test utility file during this sprint.

## Planned File Structure

This is the target layout, not an inventory of existing code. Create files as their features are implemented; do not generate empty placeholders for the entire tree. Ownership labels apply to each directory's contents unless a child has a different owner.

```text
IncentO/
|-- AGENTS.md                         # Existing contributor guide; preserve
|-- implementation_plan.md            # Architecture, ownership, and schedule (P2)
|-- progress.md                       # Fixed per-person handoff sections
|-- agent_help.md                     # Coding assistant workflow (P2)
|-- matka.md                          # Plain-language project explanation (P2)
|-- README.md                         # Setup, commands, and demo instructions (P2)
|-- .gitignore                        # Local files and build exclusions (P2)
|-- .env.example                      # Backend configuration placeholders (P2)
|-- .github/                          # P2
|   `-- workflows/checks.yml          # Frontend and backend verification
|-- contracts/                        # P2; reviewed by all before freezing
|   |-- v1.md                         # API and internal module contracts
|   |-- schemas/
|   |   |-- dataset.schema.json       # Policies, deals, tickets, cancellations
|   |   |-- analysis.schema.json      # Cohorts, calculated metrics, evidence
|   |   |-- investigation.schema.json # API response and explanation fields
|   |   `-- outcome.schema.json       # Decisions and measured outcomes
|   `-- examples/
|       |-- investigation-request.json
|       |-- investigation-response.json
|       |-- outcome-request.json
|       `-- error-response.json
|-- frontend/                         # P1 owns this entire subtree
|   |-- package.json
|   |-- package-lock.json
|   |-- index.html
|   |-- vite.config.ts
|   |-- tsconfig.json
|   |-- eslint.config.js
|   |-- public/                       # Static icons and demo assets
|   `-- src/
|       |-- main.tsx                  # Browser entry point
|       |-- App.tsx                   # Screen navigation and app shell
|       |-- api/client.ts             # Typed backend requests and errors
|       |-- types/contracts.ts        # Types aligned with contracts/v1.md
|       |-- pages/
|       |   |-- Overview.tsx          # Policies and investigation list
|       |   `-- Investigation.tsx     # Evidence, memories, and outcome form
|       |-- components/
|       |   |-- MetricCard.tsx
|       |   |-- EvidenceList.tsx
|       |   |-- MemoryPanel.tsx
|       |   `-- OutcomeForm.tsx
|       |-- styles/global.css
|       `-- tests/                    # Component and API-state tests
|-- backend/
|   |-- pyproject.toml                # Python/tool configuration (P2)
|   |-- requirements.txt              # Pinned backend dependencies (P2)
|   |-- app/
|   |   |-- __init__.py                # Package bootstrap (P2)
|   |   |-- main.py                    # FastAPI entry point (P2)
|   |   |-- api/                       # P2
|   |   |   |-- health.py
|   |   |   |-- demo.py
|   |   |   |-- policies.py
|   |   |   |-- investigations.py
|   |   |   `-- outcomes.py
|   |   |-- core/                      # P2
|   |   |   |-- config.py              # Environment loading and validation
|   |   |   |-- schemas.py             # Shared typed models matching contracts
|   |   |   |-- database.py            # SQLite connection and schema setup
|   |   |   |-- repository.py          # Record persistence and idempotency
|   |   |   |-- fixtures.py            # Validate and load demo batches
|   |   |   `-- orchestration.py       # Analyze, explain, and persist a run
|   |   |-- analysis/                  # P3
|   |   |   |-- service.py             # analyze() public module entry point
|   |   |   |-- cohorts.py             # Matching, maturity, and time filters
|   |   |   |-- metrics.py             # Rates, deltas, and uncertainty
|   |   |   `-- evidence.py            # Source linkage and corroboration
|   |   `-- memory/                    # P4
|   |       |-- service.py             # explain() and retain_outcome()
|   |       |-- hindsight_adapter.py   # Actual Hindsight SDK/API calls
|   |       |-- validation.py          # Output, citation, and chronology checks
|   |       `-- prompts/              # Explanation/reflection templates
|   `-- tests/
|       |-- integration/               # P2: complete API and persistence flow
|       |-- analysis/                  # P3: exact metrics and edge cases
|       `-- memory/                    # P4: adapter, output, and recall checks
|-- data/                             # P3; synthetic data only
|   |-- README.md                     # Field meanings and expected metrics
|   |-- scenarios/
|   |   |-- incentive-risk.json
|   |   |-- product-outage.json
|   |   `-- insufficient-data.json
|   `-- history/incidents.json        # Historical facts, decisions, outcomes
|-- docs/demo/                        # P4
|   |-- walkthrough.md                # Live demo and memory comparison
|   `-- submission-checklist.md       # Recording and individual deliverables
|-- scripts/                          # P2
|   `-- smoke_test.py                 # Repeatable full-flow verification
|-- reference/                        # Existing local PDF; ignored by Git
`-- .local/                           # Generated SQLite/runtime files; ignore
```

Add Python `__init__.py` files where package imports require them, under the same directory ownership. P2 owns shared models in `backend/app/core/schemas.py`; P3 and P4 consume those models without editing them. Their modules must not import API routes, database access, or each other; P2 connects them through orchestration.

Keep contract examples small and stable for independent development. P3 owns synthetic historical records and coordinates their content with P4; P4 owns the logic that retains and recalls them. Frontend contract types are maintained by P1 against P2's frozen schemas.

Only synthetic fixtures and placeholder configuration belong in Git. Before scaffolding, P2 adds exclusions for `.env`, `.local/`, `.venv/`, Python caches, `node_modules/`, `dist/`, and local assistant workspace files, while retaining `.env.example`. The frontend gets only a non-secret API base URL; backend credentials remain server-side.

## Contracts to Freeze in the First 45 Minutes

P2 publishes `contracts/v1.md`, machine-readable schemas, and example requests/responses. P1/P3/P4 review once, then build independently against these examples. These are internal application contracts, not assumed Hindsight SDK signatures.

Data rules:

- Stable string IDs: `policy_id`, `customer_id`, `deal_id`, `ticket_id`, `incident_id`, `run_id`. Tickets and cancellations reference a deal and customer; deals reference the applicable policy version.
- Record event timestamps and policy effective dates in UTC. Give each replay an `as_of` timestamp; exclude future events from calculations and memory retrieval.
- Store money as integer minor units plus currency, discounts as fractions from 0 to 1, and missing values explicitly. Do not join customers by display name.
- Define `Policy`, `Deal`, `Ticket`, `Cancellation`, `Incident`, and `ManagementOutcome` schemas. Deals include segment, acquisition channel, close time, and revenue; outcomes distinguish decisions from later measured results.
- Define `Evidence` with source ID, source type, timestamp, excerpt where applicable, and an exact record reference.
- Define `AnalysisResult` with cohort definitions/counts, metric denominators, deltas, uncertainty, evidence IDs, alternative explanations, and `insufficient_data` reasons.
- Define `Investigation` with run/policy IDs, analysis, hypothesis, supporting and conflicting evidence, recommendations, recalled incident IDs, and memory status: `live`, `unavailable`, or `fixture`.
- Every recommendation includes an action, a rationale linked to evidence, a proposed success metric, and a guardrail. Never invent citations or a numerical confidence score.

Entities and relationships:

- **Investigation.** One stored run of analysis plus explanation. Its ID is the `run_id`; there is no separate investigation ID. Each run records `memory_mode` and an `analysis_digest` (a hash of the calculated results, so two runs can be checked for identical numbers).
- **Incident.** The tracked case that persists across runs, with a deterministic ID, `inc-<policy_id>-<comparison_id>`, so a later investigation of the same policy finds the same incident and its saved outcomes. An investigation with insufficient data has `incident_id: null`. Seeded history incidents keep their own IDs from `data/history/incidents.json`.
- **Outcome.** Has an `outcome_id`, a `type` (`decision` or `measured_result`), the `incident_id`, the `run_id` it responds to, an `event_time` (so replays can exclude future outcomes), a client `idempotency_key`, and a `retention_status` (`pending`, `retained`, or `failed`, with a non-secret error reason).
- `memory_mode` is `live` (default) or `off`. `off` explains with no recalled history; P4 chooses the mechanism. Calculated results must be identical in both modes.

| API | Purpose |
| --- | --- |
| `GET /api/health` | App and memory configuration/status, without exposing secrets |
| `POST /api/demo/load` | Load a named scenario/batch idempotently into an isolated demo dataset, and seed its historical incidents into memory (idempotent by incident ID); report a seed status |
| `POST /api/demo/reset` | Body `{scenario, confirm: true}`. Clear that scenario's SQLite demo data and delete and re-seed its demo memory bank. Refuses any bank without the `incento-demo-` prefix; works only when `DEMO_RESET_ENABLED=true` |
| `GET /api/policies` | List available policies and versions |
| `POST /api/investigations` | Accept policy, scenario, `as_of`, `memory_mode` (`live` or `off`), and idempotency key; create an investigation. The response includes `memory_mode`, `incident_id`, and `analysis_digest` |
| `GET /api/investigations` | List stored investigations |
| `GET /api/investigations/{id}` | Return complete investigation and evidence (`id` is the `run_id`) |
| `GET /api/incidents` | List tracked incidents |
| `GET /api/incidents/{id}` | Return the incident, its linked `run_id`s, and its outcomes with retention status |
| `POST /api/incidents/{id}/outcomes` | Save a decision or measured outcome and retain it in memory. The same `idempotency_key` returns the existing outcome with no duplicate; the same key with a different body returns `409 idempotency_conflict` |
| `POST /api/outcomes/{outcome_id}/retention` | Retry retaining a `failed` or `pending` outcome in Hindsight; no-op if already `retained` |

Agree on validation errors, empty responses, and a common error shape (`code`, `message`, `request_id`). Return partial analytical results if memory fails, clearly marked. Persist retention status; support retry without duplicating the management outcome.

Internal boundaries: P3 exports `analyze(dataset, policy_id, as_of) -> AnalysisResult`; P4 exports `explain(analysis, context) -> Explanation`, `retain_outcome(outcome) -> RetentionResult` (idempotent by `outcome_id`, so the retry endpoint simply calls it again), `seed_history(incidents) -> SeedResult`, and `reset_demo_bank(scenario) -> ResetResult`. P4 verifies in the official documentation that a Hindsight bank can be deleted before building reset. P2 handles loading, persistence, and serialization. P4 verifies actual Hindsight methods against the official documentation before implementation: <https://hindsight.vectorize.io/>.

## Phases and Eight-Hour Schedule

Elapsed times start at kickoff. The seven rows below are Phases 1-7, in order. Hold a five-minute check-in at each phase gate; report contract changes and blockers immediately. Time windows are targets, not permission to advance without passing a checkpoint.

| Time | P1: frontend | P2: API/integration | P3: analysis/data | P4: memory/demo | Exit gate |
| --- | --- | --- | --- | --- | --- |
| 0:00-0:45 | Sketch three screens; review examples | Bootstrap repo; freeze contracts and ownership | Define cohorts and fixture fields | Verify credentials; prove a real retain/recall call | Shared contracts and runnable skeleton |
| 0:45-2:00 | Build against local contract fixtures | Routes, SQLite, fixture loading, stub module wiring | Generate scenarios and pure analysis functions | Adapter, reflection output, historical incident seed | Each module runs independently |
| 2:00-3:30 | Connect overview and evidence detail | Merge modules; wire complete investigation | Finish metrics and failure-case tests | Connect recalled evidence and recommendations | First real end-to-end investigation |
| 3:30-5:00 | Outcome form, memory panel, error states | Persistence, replay/idempotency, timeout handling | Outage control, sparse-data case, maturity checks | Save outcome; prove later recall after restart | Complete memory learning loop |
| 5:00-6:00 | UI usability and empty/loading states | Clean-checkout smoke test; resolve integration failures | Verify displayed numbers against fixtures | Validate citations, memory failure behavior, demo script | Feature freeze at hour 6 |
| 6:00-7:00 | Fix presentation blockers; capture screens | Rehearse launch; finish README/config instructions | Verify demo evidence; explain analytical limits | Record end-to-end demo and memory comparison | Reproducible release candidate |
| 7:00-8:00 | Personal submission materials and rehearsal | Final sequential merges, release checklist, submission | Personal submission materials and Q&A | Personal submission materials; final live rehearsal | Submission ready with buffer |

Every person prepares required personal content in Phases 6-7, after the skeleton works; none of it blocks earlier phases. The official content guide is already in `reference/`; its requirements are summarized in the Event Requirements and Release Checklist below. If content work needs more time, cut optional UI polish early.

### Gate Rules

- A phase is complete only when **every exit checkpoint below passes**. All implementation gates start as `NOT STARTED`; writing this plan does not complete them.
- The named owner supplies evidence. P2 and the relevant owner review it; another contributor reviews P2's own deliverables. P2 records the gate result, UTC time, reviewed commit, evidence, and reviewers in `progress.md`.
- Run integration checks against the merged `main` commit, not an unmerged personal branch. Include exact commands and outcomes, plus run IDs or screenshots for interactive checks. Screenshots alone do not prove calculations or persistent memory work.
- Start Phase N+1 only after Gate GN passes. While a gate is blocked, people may prepare independent fixtures, tests, or presentation material, but must not treat blocked functionality as accepted or build dependent integration on an unapproved contract.
- A failed checkpoint gets an owner, a concrete fix, and a retest time. Reduce optional scope to recover time; do not waive evidence integrity, live memory, or the outcome loop. Record scope changes before reassessment.
- Reopen a passed gate if a later change breaks its acceptance criteria. Recheck affected downstream gates before release. Feature freeze remains at elapsed hour 6 even if earlier gates run late; spend remaining time fixing the minimum demo.

### Phase 1 — Foundation and Contract Freeze (0:00-0:45)

**Objective:** Give all four people a stable starting point. **Coordinator:** P2. **Entry:** Planning documents available; kickoff begins.

Exit checkpoints — **G1**:

- [ ] **P2 + all:** Assign human owners, deadline, separate clones/worktrees, and file boundaries; verify each contributor's human Git identity and remote access.
- [ ] **P2:** Merge the skeleton and v1 schemas/examples. All four contributors confirm field names, module signatures, error shape, and time/money conventions. Example payloads pass schema validation.
- [ ] **P1/P2:** Frontend starts and renders its shell; backend starts and responds to `/api/health`; setup commands are recorded.
- [ ] **P4:** Create the team Hindsight Cloud account, apply the promo credit, and share the API key privately (never in Git). Retain a uniquely identified synthetic fact in a development bank and recall it in a separate request. Record the bank identifier and result without secrets. Also record which text-generation model Hindsight Cloud reports using (check the console and the Cloud docs at docs.hindsight.vectorize.io), or note that it is not visible.
- [ ] **P2 + all:** Add local configuration and runtime exclusions to Git before scaffolding grows. (Band AI desktop and content deliverables are deferred; see the Event Requirements and Release Checklist.)

**Advance when:** Shared interfaces are frozen and external memory access is proven. A simulated Hindsight response does not pass G1.

### Phase 2 — Independently Working Modules (0:45-2:00)

**Objective:** Complete each owned module against the same contracts. **Coordinator:** P2; each person owns their module evidence. **Entry:** G1 passed.

Exit checkpoints — **G2**:

- [ ] **P1:** Overview and investigation screens render frozen contract fixtures; loading, empty, and error states work; frontend build/type checks pass.
- [ ] **P2:** Policy listing, fixture loading, and investigation routes validate requests and return contract-valid responses. Loading the same batch twice does not duplicate records; API tests pass with clearly labeled module stubs where needed.
- [ ] **P3:** Risk, outage, and sparse-data fixtures validate and use consistent source links. Pure analysis returns expected counts/rates for a hand-calculated case; its unit tests pass.
- [ ] **P4:** Adapter performs actual Retain, Recall, and Reflect operations; Reflect is called with the agreed `response_schema`, and the returned `structured_output` is validated against the explanation contract with only retrieved memory IDs cited. Tests cover unavailable service and malformed output, distinguishing stubbed tests from live checks.
- [ ] **P2 + owners:** Module PRs are reviewed and merged sequentially; contract compatibility checks pass on `main`; all four handoffs identify their commits and next tasks.

**Advance when:** Each module works independently and its interface is verified. Internal stubs allowed here must be removed from the live demo path at G3.

### Phase 3 — First Integrated Investigation (2:00-3:30)

**Objective:** Prove the core product works from the browser. **Coordinator:** P2; P1/P3/P4 verify their outputs. **Entry:** G2 passed.

Exit checkpoints — **G3**:

- [ ] **P1/P2:** From the UI, load the risk scenario, select a policy, run an investigation, and reopen its saved detail through the API without editing code or database rows.
- [ ] **P3:** Displayed values match fixture expectations, including cohort membership, denominators, observation dates, and source IDs; no future evidence appears.
- [ ] **P4:** The integrated request uses live Hindsight, recalls the seeded relevant incident, and returns an evidence-backed explanation with alternatives and a specific next action.
- [ ] **P1/P4:** Every displayed evidence reference resolves to a supplied record or retained incident; synthetic data and memory status are visible. No causal-certainty claim or invented citation appears.
- [ ] **P2:** Save a reproducible smoke-test result and run ID for the merged commit; freeze breaking contract changes.

**Advance when:** A real browser-to-analysis-to-memory investigation succeeds. A screenshot of fixture-only UI does not pass G3.

### Phase 4 — Persistent Learning Loop (3:30-5:00)

**Objective:** Demonstrate that remembered outcomes change later advice. **Coordinator:** P4, with P2 responsible for persistence. **Entry:** G3 passed.

Exit checkpoints — **G4**:

- [ ] **P1/P2/P4:** Submit a management decision and then a measured outcome through the UI/API. Both are stored distinctly, with confirmed memory retention status.
- [ ] **P2/P4:** Restart the application; verify the saved investigation and outcome remain accessible and a later investigation recalls the outcome from Hindsight.
- [ ] **P3/P4:** Compare the same current evidence with empty versus relevant history (`memory_mode` `off` versus `live`): numerical results stay identical, shown by equal `analysis_digest` values, while the explanation cites history and makes an identifiable, justified change to its recommendation.
- [ ] **P2/P4:** Repeat outcome submission with the same idempotency key; no duplicate application event or duplicate logical memory record is created. A failed retention attempt is visible and succeeds on retry through `POST /api/outcomes/{outcome_id}/retention`.
- [ ] **P3/P4:** Historical replay excludes future outcomes from both analysis and recall; rejected past hypotheses remain labeled as rejected.

**Advance when:** Save, restart, recall, and changed advice are demonstrated on the merged commit. Merely storing text or promising future learning does not pass G4.

### Phase 5 — Correctness and Resilience (5:00-6:00)

**Objective:** Make the accepted demo reliable. **Coordinator:** P2; each owner fixes their module. **Entry:** G4 passed.

Exit checkpoints — **G5**:

- [ ] **P3:** Risk scenario is flagged with supporting evidence; outage scenario presents the alternative explanation without an incentive accusation; sparse data returns insufficient evidence. Duplicate, missing-link, zero-denominator, and immature-cohort tests pass.
- [ ] **P4:** Missing credentials, timeout, malformed model output, and invalid references produce honest failure/partial-result states. Previously generated text is never silently presented as a fresh live result.
- [ ] **P1:** Loading, empty, error, and retry flows are usable; a user can inspect evidence and save an outcome without a broken screen.
- [ ] **P2 + a second contributor:** A clean checkout installs and runs using the README, with only documented external configuration. Frontend build/lint/tests, backend lint/tests, and the full-flow smoke check pass.
- [ ] **All:** No unresolved issue blocks launching, evidence inspection, correct metrics, or the live memory loop. Record deferred cosmetic issues, update handoffs, and freeze features.

**Advance when:** Required correctness checks pass and another person can reproduce the demo setup.

### Phase 6 — Release Candidate and Demo Rehearsal (6:00-7:00)

**Objective:** Turn the verified application into a clear presentation. **Coordinator:** P4; P2 owns the release candidate. **Entry:** G5 passed.

Exit checkpoints — **G6**:

- [ ] **P4 + all:** Rehearse the complete story: policy, warning, source evidence, prior memory, recorded outcome, and improved later recommendation. Show the business value within the first minute.
- [ ] **P2/P4:** Validate the demo's initial dataset and isolated memory state so a previous rehearsal cannot contaminate the comparison. Reset only designated demo state with `POST /api/demo/reset`; preserve saved evidence needed for the presentation.
- [ ] **P4:** Record a playable demo video from the release candidate and verify that the memory operations and outcome loop are visible. Label any fallback recording accurately.
- [ ] **P2:** Record the release-candidate commit, launch instructions, test evidence, known limits, and recording location. Inspect commit attribution and tracked files for unintended local data or credentials.
- [ ] **All:** Draft the individual article and social post, plus the team video, required by the content guide; list remaining submission tasks with owners.

**Advance when:** The release candidate and presentation are reproducible, and the recording can be opened by another team member.

### Phase 7 — Final Submission and Handoff (7:00-8:00)

**Objective:** Deliver a complete, accessible submission. **Coordinator:** P2; every person owns their required content. **Entry:** G6 passed.

Exit checkpoints — **G7**:

- [ ] **P2:** Merge only reviewed release fixes. Rerun affected checks and the final full-flow smoke test on the exact submitted commit; record the final commit ID.
- [ ] **P2/P4:** Verify repository and video links are accessible as required by the event; have the documented launch procedure ready for the live demonstration.
- [ ] **All:** Complete required individual content and record its links/status against the official content guide.
- [ ] **P2:** Submit the required materials and save confirmation or receipt details; do not mark a merely prepared submission as delivered.
- [ ] **All:** Complete a final live rehearsal and update handoffs with outstanding limitations, release links, and recovery instructions.

**Complete when:** G1-G7 are all passed with evidence, the submitted commit is verified, and delivery is confirmed. If the deadline arrives with a failed gate, report the incomplete checkpoint explicitly rather than marking the project complete.

## Analysis and Memory Rules

P3 compares matched segment/channel cohorts using the same observation window. Show discount changes, complaint rates, and 30-day cancellation rates only for customers with at least 30 days of observable history. Define month-end consistently (last five calendar days). Report excluded records and denominators.

Predefine a small set of comparisons to avoid searching for arbitrary coincidences. Initial demo screening rules: at least 20 eligible deals per cohort, a 10-percentage-point cancellation-rate increase or discount increase, plus corroboration from at least two distinct customers. These are transparent demo heuristics, not validated business thresholds or proof of statistical significance. Show rate uncertainty, such as Wilson intervals, where implemented; do not claim causality. Sparse data returns an insufficient-evidence result.

Include early onboarding complaints as leading signals; later cancellations are follow-up evidence. Deduplicate tickets by source ID and avoid counting several tickets from one customer as independent corroboration. The outage scenario should produce a business-risk observation with an alternative explanation, not an incentive-specific accusation.

P4 retains facts, hypotheses, decisions, and measured outcomes as separate categories with timestamps and source IDs. Recall only context available by the run's `as_of` time. Seed one relevant prior incident and one rejected incentive hypothesis. Use a separate bank/namespace per developer and demo scenario to prevent cross-test contamination; P4 confirms the supported isolation mechanism.

Demonstrate identical current evidence with an empty memory and with relevant history, then save a new outcome and show that it influences a later run. Keep calculations unchanged between comparisons. Verify returned references against stored evidence. Untrusted ticket text is data, never an instruction to the application. A stub or recording must be labeled; it cannot count as successful live Hindsight integration.

## Git Workflow and Conflict Prevention

1. P2 establishes a human Git author identity, makes the initial reviewed baseline commit, configures the team remote, and merges bootstrap contracts before others branch. Do not commit credentials, local databases, `reference/`, or assistant workspace files. Extend ignore rules before staging new tooling files.
2. Use separate clones or worktrees; never run four assistants in the same checkout. After the baseline exists, each person branches from current `main`:

   ```powershell
   git switch main
   git pull --ff-only origin main
   git switch -c feat/p1-frontend
   ```

   Use `feat/p2-api`, `feat/p3-analysis`, and `feat/p4-memory` for the other roles. Make small task branches from current `main` after each squash merge; do not continue an already squash-merged branch.
3. Stage explicit owned paths, inspect `git diff --cached`, then commit. Example subjects: `feat: add cohort evidence view`, `fix: handle missing policy dates`, `docs: update analysis handoff`. Commit subjects, bodies, and trailers must not mention coding assistants, agent names, model names, or generated-by/co-author bot attribution. Use the human contributor's identity. Inspect and remove automatically inserted attribution before committing.
4. P1 owns the frontend dependency manifest/lockfile; P2 owns backend dependencies. P3/P4 request dependency additions through P2. No whole-repository formatting, lockfile regeneration outside ownership, or unrelated cleanup.
5. Push feature branches and open focused PRs with changed behavior, validation commands/results, contract impact, and screenshots for visible UI changes. P2 merges one PR at a time after checks; target merge gates at hours 2, 3.5, 5, and 6.
6. Before merging, fetch and merge current `origin/main` into the feature branch, rerun affected checks, and push. This avoids rewriting shared history. Resolve any conflict with its file owner; never blindly choose all of one side. Do not force-push `main`.
7. Treat `progress.md` as a serialized shared file. Each person edits only their fixed section. Before a progress-only merge, P2 grants a short merge slot; refresh from `origin/main`, apply the update, and merge before the next person proceeds. Keep handoff text available locally while waiting. Do not regenerate or reformat the entire file.
8. Shared contract changes go through P2, who records the change and alerts all consumers. Prefer additive fields after hour 0:45; no breaking changes after hour 3:30 without a team decision. Shared documentation edits also go through P2.

Exclusive path ownership prevents most code conflicts; the serialized merge queue handles shared files. Git cannot guarantee zero conflicts if these boundaries are ignored.

## Validation and Completion

P1 adds frontend `npm run dev`, `npm run build`, `npm run lint`, and `npm test` scripts. P2 documents backend setup plus `python -m uvicorn app.main:app --reload`, `python -m pytest`, and `python -m ruff check .` from `backend/`. These are target commands, not currently runnable commands. Pin backend dependencies and keep secrets server-side; a browser-prefixed environment variable must never contain an API key.

- P1: build/type checks; evidence rendering, API error, and outcome-submission UI checks.
- P3: exact fixture metrics; missing links; zero denominators; duplicate records; immature cohorts; future-data exclusion; outage and insufficient-data scenarios.
- P4: adapter tests for missing credentials, timeout, malformed output, invalid evidence references, and future-memory exclusion; one real persistence/recall smoke test, separately labeled from mocked tests.
- P2: full load-investigate-outcome-reinvestigate flow; replay idempotency; persistence after restart; readable failure states; clean-checkout launch.

Done means a fresh checkout can run from documented commands, the UI shows traceable numerical and textual evidence, real memory affects a later recommendation, tests/checks have recorded outcomes, and the team can complete the live demo without editing code.

If behind: cut extra charts, styling, hosting, and extra scenarios beyond the required risk/control pair. Preserve source evidence, honest uncertainty, a working outcome loop, and real Hindsight integration. External service failure remains an explicit blocker, even if a labeled recording supports the presentation.

## Event Requirements and Release Checklist

The reference PDFs in `reference/` (the problem statement and the content guide; ignored by Git, so teammates need copies) require Hindsight, Band AI desktop use, a documented GitHub repository, a demo video, a live demonstration, an explanation of memory use, and content deliverables. Judging weights: innovation 30%, Hindsight memory 25%, implementation 20%, user experience 15%, real-world impact 10%.

Content deliverables are done in Phases 6-7, after the skeleton works, not at kickoff:

- **Each member:** one public article (1,200-1,500 words; the guide's contest table says 800-1,500 and its sample prompt says 1,200-2,000) on Medium, Dev.to/Hashnode, Substack, or as a LinkedIn article; one LinkedIn post that links the repository, with the article URL as the first comment and the Hindsight repository (<https://github.com/vectorize-io/hindsight>) as a second comment; and the article shared as a Reddit link post in r/llmdevs, r/sideproject, r/aiagents, or r/aimemory.
- **Team:** one video, 2-5 minutes, 1080p minimum, screen recording with voiceover, hosted on a public site rather than shared as a drive link. **Open question:** the problem statement says every member completes a video, while the content guide lists one per team; confirm with the organizers.
- **Banned word:** articles and social posts that contain the word "hackathon" in the title or body, hashtags included, are disqualified. As a precaution, keep it out of the README and the repository description as well. P4's `docs/demo/submission-checklist.md` includes a scrub check for every article and post.
- **Band AI desktop:** a required tool, but not set up at kickoff. After G3 passes and the skeleton works, use it for final polish and keep a screenshot or clip showing its use for the video.
- **Honesty:** articles describe only implemented behavior and label synthetic data. Ignore the guide's sample-prompt instruction to describe a future, fully implemented system.

Before release: verify human-only commit attribution, scan staged files for secrets, label synthetic data, check the README launch instructions, scan articles and posts for the banned word, save demo links, and update all four handoffs.
