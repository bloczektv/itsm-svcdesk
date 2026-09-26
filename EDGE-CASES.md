---
lab2_edge_cases:
  E1: {rule: R-08, count: 3}
  E2: {rule: R-06, count: 2}
  E3: {rule: R-09, count: 4}
  E4: {rule: R-10, count: 4}
  E5: {rule: R-12, count: 1}
  E6: {rule: R-13, count: 11}
---
<!-- ai-generated: 80% - Claude Code found each concrete instance in the practice log and drafted the analysis; every count is the service's own computed output -->

# Edge cases in the practice event log

## E1 - clock skew produces a negative lead time

- What the log contains: Three (commit, deployment) pairs where the commit's timestamp is after the deployment that shipped it, e.g. commit sha-0040 at 18:51:41 shipped by DEP-0012 at 18:37:47 the same day (delta -834s), and similarly sha-0094 (-51s) and sha-0123 (-780s). Two machines disagreed about the time.
- What a default definition would have done: Either discard the pair as "impossible" (silently shrinking the sample the median is computed over and hiding the skew) or feed the negative delta straight into the median, dragging change_lead_time_seconds_p50 into nonsense territory or even below zero.
- Why the rule is defensible: Clamping to zero and counting the pair treats it as a near-instant, honestly-measured delivery instead of hiding it; the separate negative_lead_time_pairs counter still tells the reader that three pairs needed the clock-skew workaround, so the anomaly is visible without corrupting the headline number.

## E2 - a revert of a revert

- What the log contains: A revert chain of depth two: commit sha-0070 reverts sha-0069 (the original change, CHG-0033), and commit sha-0071 reverts sha-0070, effectively re-landing CHG-0033. Neither revert commit carries its own change_id, per the log's own well-formedness rule.
- What a default definition would have done: Count every commit as its own change, since a plain group-by-commit sees three commits and reports three changes - the original fix, an apparent regression, and a second fix - inflating throughput for work that shipped exactly once from the customer's point of view.
- Why the rule is defensible: The transitive resolution walks sha-0071 to sha-0070 to sha-0069 and resolves the whole chain back to the single change_id CHG-0033, so a team that ships, quickly reverts a regression, and re-lands the fix is credited with one change, not three - which is what actually reached users.

## E3 - a hotfix that never touched `main`

- What the log contains: Four commits that reached production on branches named hotfix/2609, hotfix/6085, hotfix/4347 and hotfix/1544 (shas 0019, 0108, 0077 and 0127, via deployments DEP-0006, DEP-0028, DEP-0019 and DEP-0033) - none of them ever landed on `main` before shipping.
- What a default definition would have done: Filter lead-time pairs on branch == "main", silently dropping all four commits from the numerator - the emergency fixes that actually reached customers would vanish from every delivery metric.
- Why the rule is defensible: R-09 measures when code reaches production, not which ref it lived on, so trunk-based teams and teams that ship emergency hotfixes on throwaway branches are measured the same way; commits_never_on_main still surfaces the branching-discipline signal separately, for whoever wants to investigate it.

## E4 - a deployment with zero linked commits

- What the log contains: Four in-window production deployments with an empty commits array - two successful (DEP-0026, DEP-0032) and two failed (DEP-0043, DEP-0044) - config-only pushes or no-op redeploys of an existing artifact.
- What a default definition would have done: Either drop these deployments from every count because the code iterates "for each commit" and finds nothing to attach them to, or divide by zero trying to compute a per-deployment average - either way, DEP-0043 and DEP-0044 (two real production failures) disappear from the change fail rate.
- Why the rule is defensible: They still count in deployment frequency and in both instability metrics' denominators, because they are real production deployments and two of them really failed; they simply contribute no lead-time pair, since there is no commit to measure a lead time from.

## E5 - a deployment that failed and never recovered

- What the log contains: One failed deployment, DEP-0015 at 06:12:35 on 2026-09-07, whose covering incident (INC-0004) was opened but carries no `resolved` event anywhere in the log - the outage is still open at the end of the observed window.
- What a default definition would have done: Either close the incident at the window's end and report a recovery time for it anyway, fabricating a number for an incident nobody actually closed, or silently drop the failure from the denominator, making change_fail_rate look better than reality.
- Why the rule is defensible: Excluding it from the recovery-time median avoids inventing a number that was never measured, while keeping it in change_fail_rate and in counts.open_failures tells the dashboard's reader, honestly, that one failure is still unresolved instead of quietly disappearing it.

## E6 - overlapping incidents

- What the log contains: Eleven pairs of incidents whose intervals intersect. Most involve INC-0004 (the still-open incident from E5), whose interval runs from 2026-09-07 all the way to the window's end and therefore overlaps with seven later incidents; the rest are genuine close-in-time overlaps such as INC-0007/INC-0008 and INC-0010/INC-0011.
- What a default definition would have done: Merge overlapping incidents into one, losing the fact that two independent failures were live at once, or sum their durations onto a shared deployment, double-counting recovery time for any deployment two overlapping incidents both cover.
- Why the rule is defensible: Recovery time is computed per failed deployment, never per incident, so two failed deployments sharing (or overlapping) incidents each keep their own honest recovery instant; the pair count simply flags how tangled the incident timeline was - eleven pairs is worth an ops retro - without letting that tangle distort any deployment's actual number.

## Gaming demonstration

I improved `deployment_frequency_per_day` (R-11) by adding 18 no-op production deployments - empty `commits`, `outcome: "success"` - spread evenly across the 21-day window. They touch not one real commit, yet they raise the in-window deployment count from 42 to 58, lifting frequency from 2.0/day to about 2.76/day, well past the required +25% margin.

To make the real cost visible rather than hidden, I simultaneously delayed two base deployments that shipped genuine work - DEP-0028 and DEP-0031, together the first successful delivery of 8 distinct changes - to just after the window closes. This is legal under R-19: I only moved them later, and never touched their outcome, environment or commits. On the base-work-only replay the grader runs, this drops `ground_truth.changes_delivered` from 65 to 57 (about 88% of the base), comfortably past the 90% harm threshold, while the metric I claimed (deployment frequency) looks 38% better.

In a real team this is exactly the incentive a "ship more often" OKR creates without a paired lead-time or throughput guardrail: a platform team under pressure to hit a deployment-frequency target for a quarterly review can freely schedule config-flag flips, cache-bust redeploys or restart-only releases that touch no code, while quietly letting the actual feature work slip to "next sprint." The engineers running the pipeline, and the manager who reports the dashboard number upward, are the ones rewarded - the deploy count goes up and the graph turns green - while the product owner whose roadmap items just got delayed, and the customers waiting on those 8 changes, absorb the real cost. That gap, between "the metric says we deliver more" and "fewer real changes actually reached production," is exactly what R-21's base-only replay exists to catch.
