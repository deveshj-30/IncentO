# Memory & Explanations Module (P4)

This module integrates the backend with **Hindsight Cloud** (Vectorize) to provide persistent, cross-session memory for AI-assisted sales commission investigation.

## Responsibilities

* Provide durable, cross-session recall of past commission policy incidents and management outcomes.
* Enforce strict temporal boundaries: never retrieve or reflect on memories dated after `context.as_of`.
* Ground all recommendations in real evidence IDs and remembered outcomes without hallucinated citations.
* Degrade gracefully to deterministic templates if the external memory service is unavailable or times out.

## Structure

* `service.py`: Public entry points called by the core orchestrator (`explain`, `retain_outcome`, `seed_history`, `reset_demo_bank`).
* `hindsight_adapter.py`: Direct interface with Hindsight Cloud REST API, handling bank names, prefixes, authentication, and offline simulation.
* `prompts.py`: Tokenized explanation templates for hypothesis and recommendation formatting.
* `validation.py`: Token resolution (`{{m:...}}`, `{{t:...}}`), citation sanitization, and chronology filters.

## Bank Naming & Isolation

Per the project agreement, memory banks follow strict naming prefixes:
* **Demo banks**: `incento-demo-<scenario>` (e.g. `incento-demo-main`)
* **Development banks**: `incento-dev-<scenario>`

`reset_demo_bank` explicitly refuses to reset any bank that does not start with `incento-demo-`.

## Configuration

Set the following environment variables in `.env` (or via environment):
* `HINDSIGHT_API_KEY`: API key for Hindsight Cloud (obtained using promo code `MEMHACK99`).
* `HINDSIGHT_BASE_URL`: Defaults to `https://api.hindsight.vectorize.io`.

When `HINDSIGHT_API_KEY` is not set, the adapter transparently runs an in-memory simulation, allowing offline development and test execution without external network access.

## Testing

Run unit tests from the repository root:
```bash
backend/.venv/bin/pytest backend/tests/memory/ -v
```
