---
lab3_slo:
  service: svcdesk
  route: /kb/search
  window: 28d
  slis:
    availability:
      objective: 0.99
      good: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search", http_response_status_code!~"5.."}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 403.2}
    latency:
      objective: 0.99
      threshold_seconds: 0.3
      good: 'sum(rate(http_server_request_duration_seconds_bucket{job="svcdesk", http_route="/kb/search", le="0.3"}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 403.2}
  alerts:
    - {alert: KbSearchErrorsBurnFast, sli: availability, burn_rate: 14.4, long_window: 1h, short_window: 5m}
    - {alert: KbSearchErrorsBurnSlow, sli: availability, burn_rate: 6, long_window: 6h, short_window: 30m}
---
<!-- ai-generated: 70% - Claude Code drafted the front matter and the prose from my load 3 measurements; I chose the objectives and reviewed every number -->

# SLO for `GET /kb/search`

The numbers below come from two runs of `itsmlab load 3` on my own login's kb-index profile (bloczektv), the
measurement the grader repeats: 60 s open-loop at 40 requests per second, latency-corrected. Run 1: p50 38.1 ms,
p95 69.3 ms, p99 216.2 ms, p99.9 243.8 ms, p99.99 266.2 ms, 5 of 2,399 answers were 502. Run 2: p99 214.6 ms,
p99.99 256.9 ms, again 5 of 2,399 were 502. The window is 28 days (40,320 minutes): four whole weeks, so every
window holds the same number of Mondays and weekends.

## Availability

A `/kb/search` request is good when svcdesk answers it with anything other than a 5xx; a 400 for a bad `q` is the
client's mistake and stays good. Objective 99 %: an error budget of 1 %, 403.2 minutes of full outage in 28 days.

Why not 99.9 %: svcdesk's own failures on this route are almost only kb-index's, which I pass on as 502 and cannot
fix in svcdesk. kb-index failed 0.21 % of the searches in both runs. Against 99.9 % that is a permanent burn rate
of 2.1, so the budget would be exhausted in about 13 days with nothing broken, and the slow-burn alert would be
noise. Against 99 % the same 0.21 % is a burn rate of 0.21: a fifth of the budget goes to the dependency's normal
behaviour, and four fifths remain for real incidents (a kb-index outage, a deploy of svcdesk that breaks the call).
Lab 6 uses this objective as a canary gate; 99 % leaves enough room that an honest release, which still sees
kb-index's 0.21 %, is not rolled back for it.

## Latency

A `/kb/search` request is good when it is answered within 0.3 s, counted directly from the `le="0.3"` bucket, one
of my boundaries (no interpolation). Objective 99 %: a budget of 1 %, 403.2 minutes in 28 days.

Why 0.3 s: the measured distribution has a fast mode (p95 69 ms) and a narrow slow mode, about 2 % of requests
between 0.19 and 0.27 s, where my p99 of 0.216 s sits. That slow mode is how kb-index behaves on a healthy day. A
threshold inside it (0.2 or 0.25 s) would make a fixed share of normal requests "bad" and spend the budget on the
dependency's shape instead of on regressions; 0.1 s would count the whole slow mode, 2.2 % of requests, against a
budget that cannot be smaller than that. At 0.3 s the slowest request I measured (p99.99 266 ms) is still good, so
the healthy service burns close to nothing, and the SLI turns bad exactly when something new happens: the slow mode
gets slower, kb-index degrades as a whole, or svcdesk itself adds latency. 0.3 s is also still a usable answer
for a search box, and it stays under the 1 s Lab 6 allows. The objective 99 % rather than 99.9 % because the gap
between my slowest request and the threshold is only 34 ms; on a slower machine (the grader's, or Lab 6's canary)
the slow mode's tail can cross 0.3 s for a few requests in a thousand, and I do not want that to page.

## Alerts

Both alerts are on availability: that is where kb-index's failures show, and a 1 % budget at 10 requests per
second is spent in hours by a real outage.

| alert | SLI | burn rate | long / short window | budget spent when it fires | severity: page or chat |
|---|---|---|---|---|---|
| KbSearchErrorsBurnFast | availability | 14.4 (error ratio > 14.4 %) | 1h / 5m, `for: 2m` | 2 % of the 28-day budget in the hour; all of it in under 2 days | P1, page |
| KbSearchErrorsBurnSlow | availability | 6 (error ratio > 6 %) | 6h / 30m, `for: 5m` | 5 % of the budget in 6 hours; all of it in under 5 days | P2, chat |

**The fast alert pages.** At 14.4 times the sustainable rate, one in seven searches fails, and the whole month's
budget is gone in under two days; if it starts at 2 a.m., by 8 a.m. 13 % of the budget is spent and the
help desk starts its day with a search that fails one in seven times. Waking someone for that is worth it: the
usual causes (kb-index down, a bad svcdesk deploy, a broken `KB_INDEX_URL`) are fixed in minutes by a rollback or
a restart, and each hour of waiting costs another 2 % of the budget. Its 5-minute short window means it stops
paging within minutes of the fix, and the long window means a single bad minute (kb-index's normal 0.21 % never
gets near 14.4 %) does not wake anyone.

**The slow alert goes to chat.** At 6 times the rate the budget lasts almost five days. That is a leak, not an
outage: a person can look at it in working hours, and waiting through an 8-hour night costs about 7 % of the
budget (8 x 6 / 672 hours), which the remaining budget absorbs. Paging for it would teach the on-call person to ignore pages.

Latency has no alert yet: its budget is protected by the threshold choice above, and a latency regression that
comes from kb-index usually shows as errors (timeouts become 502) before it shows as a slow 200.

## Buckets

My ladder has 28 finite boundaries, in seconds:
`0.005, 0.01, 0.02, 0.03, 0.04, 0.05, 0.075, 0.1, 0.15, 0.16, 0.17, ..., 0.27, 0.28, 0.3, 0.4, 0.5, 1, 2, 5`.

My p99 (0.2162 s in the first run, 0.2146 s in the second) falls in (0.21, 0.22], 10 ms wide: 4.6 % of the p99,
well under the 20 % that M-11 allows; the histogram's own p99 in the second run was 0.2107 s, 2 % from oha's.
The grader's q will differ from mine by a few per cent, and my own runs already show it: the
measurement inside `itsmlab verify 3` gave q = 0.2012 s, 7 % below the first run, in the bucket (0.2, 0.21]. So I
resolved a band, not a point: 14 boundaries at 10 ms
steps from 0.15 to 0.28 s and a 20 ms step to 0.3 s. Every q between 0.15 and 0.30 s, that is from 30 % below to
39 % above my measurement, lands in a bucket at most 20 ms wide, at most 13 % of the q it holds. I made the band
that wide because the whole slow mode (0.19 to 0.27 s) should be resolved, not only the p99: if the slow mode
shifts, the dashboard should show by how much.

The rest of the boundaries: eight below 0.15 s (5 ms to 100 ms) give the fast mode a usable p50 and p95 on the
dashboard; 0.3 s is the latency SLI threshold; 0.4, 0.5, 1, 2 and 5 s show how far a degradation goes, up to the
5 s upstream timeout.
