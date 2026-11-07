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

### Draft — P3 to P2 — Slice A example corrections and Slice B fixture review

- Status: DRAFT
- Context: P3 Slice A review at `2dde205`; scenario drafts merged on `main` at `c992776`; `progress/p3.md`.
- Message: P3 confirmed the Slice A shapes. In `contracts/examples/investigation-response.json`, metric citations `DEAL-0188`, `DEAL-0191`, and `CANCEL-0071` are missing from `analysis.evidence`; the `cancel_30d` gap of `.07` is labeled `watch` despite the plan's `no_signal` rule. The risk, outage, and sparse fixtures validate against the Dataset loader and need Slice B review.
- Requested next action: P2 corrects or resolves the example issues, reviews the fixtures with P4, collects all Slice A reviews, and records the freeze decision in `progress.md` with a reviewed commit.
- Reply: Pending.
