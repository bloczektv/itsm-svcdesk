---
actual_minutes: 15
ratio: 0.47
---

# METR n=1 - self-replication outcome

Predicted 32 minutes for `POST /dora/metrics` (parsing, validation, the five DORA metrics and the six
edge-case rules). Actual time from the receipted prediction to a service that passes every practice-fixture
check on the first real run was about 15 minutes: ratio actual/predicted = 15/32 = 0.47.

The prediction was set against the handout's own budget for a person writing this by hand (30 minutes for
the metrics endpoint, 25 for the edge cases, so 55 total for both items; I predicted 32 for the metrics
endpoint alone, expecting AI assistance to help but not to remove the risk that edge cases E1-E6 usually
overrun). That risk did not materialize this time: METRIC-SPEC.md states every rule precisely enough (R-06
through R-13, with worked examples for each edge case) that translating it into code was close to
mechanical rather than exploratory, and Lab 1's existing modules (`exceptions.py`, `timeutil.py`) already
supplied the error and instant-parsing conventions to reuse, so there was very little design left to
improvise. The whole function came out correct against `metrics-practice.json` on the first attempt: the
checker's observation line (`E1=3 E2=2 E3=4 E4=4 E5=1 E6=11`) matched the published fixture exactly, with
no debugging iterations needed.

Had any of the six edge cases been genuinely ambiguous - say, if the tie-break rule for overlapping
incidents or the transitive revert resolution had been underspecified rather than pinned down by the
rulebook - the actual time would likely have landed much closer to, or above, the 32-minute prediction,
since that is where the iteration would have happened. The low ratio here says more about how completely
`METRIC-SPEC.md` removes ambiguity than about raw coding speed: a well-specified rulebook plus AI assistance
compounds into a large speedup, but a same-sized task with a vaguer spec would not show the same number.
