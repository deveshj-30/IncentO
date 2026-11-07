# IncentO — 60-Second Hackathon Live Demo Script

## Hook (0:00 - 0:15) — The Problem
> *"Every SaaS company incentives sales reps with acquisition bonuses. But what happens when reps start heavily discounting month-end deals to hit quota, bringing in bad-fit customers who complain and churn within 60 days?*  
> *Right now, RevOps managers rely on gut feel or static spreadsheets. But worse, companies repeat the exact same policy mistakes year after year because they lack institutional memory.*  
> *Meet **IncentO**—powered by Vectorize Hindsight."*

---

## Act 1: The Cold Investigation (0:15 - 0:30)
1. Navigate to **Overview**.
2. Select Policy: `POL-RISK-001` on the `risk` scenario.
3. Click **"Investigate with Memory: OFF"**.
4. Show the result:
   * Point to the metrics: *"Discount gap is flagged at +14.6%, and 30-day customer complaints are flagged at +12.3%."*
   * Point to the recommendation: *"Without memory, the recommendation is a blunt `revert_change` policy suspension."*

---

## Act 2: Turning on Hindsight Memory (0:30 - 0:45)
1. Switch to **"Investigate with Memory: LIVE"**.
2. Point to the **Recalled Memories** panel:
   * *"Notice what just happened. Hindsight recalled a past incident (`HIST-RISK-RESULT`) where abruptly suspending the acquisition bonus caused seller departures and pipeline disruption without fixing onboarding."*
   * Point to the shifted recommendation: *"Instead of an abrupt cancellation, Hindsight shifts advice to `pilot_guardrail` (discount approval threshold pilot) with clear guardrails, citing past seller attrition."*

---

## Act 3: The Learning Loop in Action (0:45 - 1:00)
1. Scroll down to the **Management Response / Incident Outcome** form.
2. Enter a decision:
   * Note: *"Approved 1-quarter discount approval threshold pilot."*
   * Click **"Save Decision & Retain in Memory"**.
   * Show the confirmation: **Retained in Hindsight Memory Bank**.
3. Re-run an investigation at a later `as_of` date:
   * Show that the agent now recalls *this exact decision*, closing the persistent learning loop.
4. **Closing statement**:
   > *"IncentO turns sales commission governance from static spreadsheets into an evolving, self-learning memory system. Powered by Vectorize Hindsight."*
