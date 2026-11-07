# Synthetic scenarios

Run `python data/generate/build_scenarios.py` from the repository root to recreate
`data/scenarios/*.json`. The generator uses only the Python standard library and
fixed seeds. Customer and event excerpts are labeled placeholders pending the
separate surface-text pass.
Run `python -m unittest discover -s backend/tests/analysis -p test_scenarios.py -v`
from the repository root to verify the committed batches, exact counts, links,
and event cutoffs.

All comparisons use `as_of = 2026-11-01T00:00:00Z`, policy effective date
`2026-04-01T00:00:00Z`, segment `mid-market`, channel `direct`, and one customer
per deal. The pre-policy period is January through March 2026 and the
post-policy period is April through September 2026. Every deal has a complete
30-day observation window at this `as_of` time. Month-end means a close in the
last five UTC calendar days of its month.

| Scenario | Period | Month-end deals | Other deals | Month-end complaints / cancellations | Other complaints / cancellations | Mean discounts (month-end / other) |
| --- | --- | ---: | ---: | --- | --- | --- |
| risk | before | 60 | 440 | 9 / 6 | 66 / 44 | .12 / .10 |
| risk | after | 120 | 880 | 36 / 30 | 132 / 88 | .25 / .10 |
| outage | before | 60 | 440 | 9 / 6 | 66 / 44 | .12 / .10 |
| outage | after | 120 | 880 | 36 / 12 | 264 / 88 | .12 / .10 |
| sparse | before | 12 | 120 | 2 / 1 | 18 / 12 | .12 / .10 |
| sparse | after | 18 | 120 | 6 / 4 | 18 / 12 | .25 / .10 |

The risk case has post-policy complaint rates .30 versus .15, cancellation
rates .25 versus .10, and a discount gap of .15. Its pre-policy complaint and
cancellation gaps are 0, and its discount gap is .02. These inputs are meant
to produce a flagged finding once the confidence intervals and corroboration
rules are applied. The outage case has an equal .30 complaint rate in both
groups and equal .10 cancellation rates; its outage-themed tickets attach to
deals closed in July and August, giving the alternative explanation a specific
time window. The sparse case has only 18 post-policy month-end
deals, below the 30-deal threshold, so each metric should report insufficient
data. These outcomes are checked by the P3 analysis tests.

Every ticket and cancellation links to an actual deal and the same customer;
their source IDs can be used directly as `Evidence.id`. Seeded history uses
incident IDs as evidence sources. Event timestamps are generated within 30
days of their deals and before the stated `as_of` time.

The risk history incident `INC-RISK-PRIOR` also contains `HIST-RISK-DECISION`
(an abrupt bonus suspension) and `HIST-RISK-RESULT` (seller departures and
pipeline disruption without improved onboarding complaints). These synthetic
records predate the policy. P4 uses the measured result to test a
content-driven change from `revert_change` with memory off to
`pilot_guardrail` with memory live; the analytical metrics must remain the same.
