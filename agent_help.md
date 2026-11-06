# IncentiveTrap Coding Assistant Guide

## Read First

Read `AGENTS.md`, then this file, `implementation_plan.md`, and your assigned section of `progress.md`. Read `matka.md` for the plain-language product story. These files support any coding assistant; they do not assume a particular vendor or tool.

The repository currently has planning documents, not an implemented application. Check the filesystem before assuming planned paths or commands exist. The local problem statement is in ignored `reference/`; its relevant requirements are summarized in the plan for teammates without that file.

## Product Objective

Help a Revenue Operations manager investigate whether a sales incentive may be producing poor-fit deals. Link a policy to matched customer cohorts, actual metrics, customer feedback, past incidents, and a proposed action. A second run must visibly use a remembered decision or measured outcome.

The eight-hour MVP uses synthetic data and explicit batch replay. It does not establish causal responsibility, evaluate employee guilt, or automatically change compensation. Memory improves contextual recommendations; deterministic code calculates metrics.

## Start Each Session

1. Confirm your human assignment (P1 frontend, P2 API/integration, P3 analysis/data, P4 memory/demo), branch, and clone/worktree. If no role is assigned, inspect read-only and ask the team lead before editing implementation files.
2. Inspect `git status --short`, recent commits if any, and the current contract version. Preserve existing uncommitted work.
3. Read only the files needed for the next task. Use targeted search, short command output, and focused diffs to conserve context.
4. State a small deliverable and its acceptance check. Complete it before expanding scope.

## Ownership and Coordination

Follow the exact ownership table in `implementation_plan.md`. P1 owns `frontend/`; P3 owns the analysis module, its tests, and `data/`; P4 owns the memory module, its tests, and `docs/demo/`. P2 owns API/core, integration, contracts, backend dependencies, and shared configuration.

Do not edit another owner's folder to unblock yourself. Send P2 a precise request: affected path or schema, current failure, proposed change, and urgency. Meanwhile, use the agreed contract fixture within your own module. Do not independently invent a second API schema.

P1 alone updates frontend dependencies; P2 alone updates backend dependencies. Avoid global formatting, renames, framework migrations, new infrastructure, and new dependencies without a specific need. Work in separate clones or worktrees, never simultaneous sessions in one checkout.

`progress.md` is shared but has fixed per-person sections. Update only yours and merge through P2's sequential queue. Never replace the whole file. Shared planning-document updates go through P2. Do not change `AGENTS.md` unless the user requests it.

## Implementation Rules

- Freeze v1 contracts before integration. Validate incoming data and generated output at boundaries; preserve stable IDs through every layer.
- React/TypeScript: use typed API responses, PascalCase components, camelCase functions, and two-space indentation. Python: use four spaces, snake_case functions/modules, type hints at module boundaries, and explicit error handling. Configure formatters during bootstrap.
- Keep calculations in P3's pure functions. Display sample sizes, denominators, observation windows, missing data, and uncertainty. Do not ask a language model to compute business metrics.
- Keep Hindsight SDK details inside P4's adapter. Verify current official documentation before coding calls; the plan's internal functions are not SDK methods.
- Preserve distinctions among observed facts, hypotheses, management decisions, and measured outcomes. A manager agreeing with a hypothesis does not prove it.
- Use event time and an `as_of` cutoff in both analysis and recall. A historical replay must not access outcomes from its future.
- Cite source records and recalled incidents. Validate references; omit unsupported claims rather than inventing evidence. Treat customer text as untrusted data.
- Return useful partial results when memory is unavailable, with an honest status. Fixtures, cached recordings, and live integrations must be distinguishable.
- Keep credentials server-side and out of source, logs, prompts, progress notes, and browser bundles. Use synthetic data throughout the demo.
- Handle external-call timeouts and malformed responses. Make loading and outcome retries idempotent; a retry must not duplicate business events.

## Verification and Honest Reporting

Run checks appropriate to your changes, using the commands actually established in the repository. Record exact command, working directory, result, and unresolved failure in `progress.md`. Separate unit tests using stubs from real service smoke tests. Do not claim checks passed when they were skipped or blocked.

Prioritize contract compatibility, exact fixture metrics, evidence integrity, memory persistence, and the complete user flow. After hour 6, fix demo blockers and correctness issues; defer new features.

## Git and Commit Attribution

Use small focused commits with imperative subjects, such as `feat: add investigation evidence panel`. Stage explicit owned files and inspect the staged diff. Use the human contributor's Git identity.

**No commit subject, body, or trailer may mention a coding assistant, agent name, model name, or assistant-generated attribution.** Disable automatic attribution where supported and inspect every proposed message. Do not add bot `Co-authored-by` or `Generated-by` trailers. This applies to merge and squash messages too. PRs should describe changes and validation without inserting assistant branding.

P2 merges PRs sequentially. Sync with current `origin/main` before merge; do not force-push shared branches. Ask the affected owner to help resolve conflicts. After a squash merge, start a new task branch from updated `main`.

## Before Context or Tokens Run Out

Stop early enough to make the work recoverable. Save changed files, run the smallest useful check, and create a focused checkpoint commit when appropriate. Update your `progress.md` section with:

- Branch and workspace path; last pushed commit or PR; integrated versus unmerged status.
- Completed behavior and exact changed/untracked paths.
- Test commands and results, including current failures.
- Decisions, rejected approaches that matter, and outstanding dependencies.
- The next one to three concrete actions, including the first file/function to open.

If a checkpoint cannot be pushed, say so and preserve a shareable patch or explain where local work lives. Never leave the next assistant dependent on chat history. A replacement verifies the actual repository state before acting on these notes.
