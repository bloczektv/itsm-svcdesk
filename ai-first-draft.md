---
lab3_first_draft:
  source: ai
  tool: "ChatGPT (free plan, model not shown in the UI), chatgpt.com, 10 October 2026"
  ladder: [0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
  verdict: refuted
  evidence: {p99_seconds: 0.2162, bucket: [0.2, 0.3], relative_width: 0.463}
lab3_flawed_ladder:
  verdict: refuted
  evidence: {p99_seconds: 0.2162, bucket: [0.04, 0.5], relative_width: 2.128}
---
<!-- ai-generated: 80% - the Prompt and Answer are ChatGPT's verbatim; Claude Code drafted the verdicts from my load 3 measurement, I checked the arithmetic -->

# The assistant's first draft, and two verdicts

## Prompt

I have a Python (FastAPI) service called svcdesk with an endpoint GET /kb/search?q=<text>. On every request it calls an upstream knowledge-base search service and returns its hits. I want to instrument it with a Prometheus histogram named http_server_request_duration_seconds (seconds; labels http_request_method, http_route, http_response_status_code).

Please give me:
1. The histogram bucket boundaries (in seconds) you recommend for this endpoint, as a plain list of numbers.
2. A Prometheus alerting rule (PromQL, in YAML) for this endpoint that pages when it is burning its error budget too fast.

Answer as you normally would.

## Answer

> 1. Recommended histogram bucket boundaries
> For a FastAPI endpoint that calls an upstream knowledge-base search service on every request, I recommend these buckets:
>
> [0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
>
> These boundaries provide good resolution for subsecond responses while capturing slower requests caused by upstream latency. Adjust them based on observed latency and your service's latency SLO.
>
> 2. Prometheus alerting rule: fast error-budget burn
> Assume the endpoint has a 99.9% availability SLO, meaning an error budget of 0.1%, and that HTTP 5xx responses count as errors.
>
> The following rule uses the multi-window, multi-burn-rate approach. It pages when the error budget is burning at more than 14.4 times the sustainable rate over both a 5-minute and a 1-hour window.
>
> ```yaml
> groups:
>   - name: svcdesk-alerts
>     rules:
>       - alert: SvcdeskKBSearchHighErrorBudgetBurn
>         expr: |
>           (
>             (
>               sum(rate(http_server_request_duration_seconds_count{
>                 job="svcdesk",
>                 http_route="/kb/search",
>                 http_response_status_code=~"5.."
>               }[5m]))
>               /
>               sum(rate(http_server_request_duration_seconds_count{
>                 job="svcdesk",
>                 http_route="/kb/search"
>               }[5m]))
>             ) > (14.4 * 0.001)
>           )
>           and
>           (
>             (
>               sum(rate(http_server_request_duration_seconds_count{
>                 job="svcdesk",
>                 http_route="/kb/search",
>                 http_response_status_code=~"5.."
>               }[1h]))
>               /
>               sum(rate(http_server_request_duration_seconds_count{
>                 job="svcdesk",
>                 http_route="/kb/search"
>               }[1h]))
>             ) > (14.4 * 0.001)
>           )
>         for: 2m
>         labels:
>           severity: page
>           service: svcdesk
>         annotations:
>           summary: "svcdesk KB search is burning its error budget too quickly"
>           description: >-
>             The /kb/search endpoint is experiencing an elevated HTTP 5xx
>             error rate over both short and long windows. Investigate upstream
>             knowledge-base availability, timeouts, and svcdesk errors.
> ```
>
> Important implementation notes
> Metric compatibility: This rule assumes the histogram exposes the standard _count series and that your instrumentation attaches the specified labels. Confirm that job="svcdesk" matches your Prometheus scrape configuration.
>
> Route labels: Use the normalized route /kb/search, not the raw URL containing ?q=.... Otherwise, each query could create a distinct time series.
>
> Error definition: HTTP 5xx responses are a reasonable starting point, but include upstream failures that are returned as HTTP 4xx or other statuses if your SLO defines them as errors.
>
> Burn-rate threshold: For a 99.9% SLO, a 14.4× burn rate corresponds to an error ratio of 1.44%. The paired windows reduce paging on isolated spikes. The for: 2m adds a short persistence requirement.
>
> Traffic volume: Consider a minimum-request-volume condition if the endpoint receives very little traffic; ratios can be noisy with few requests.
>
> One caveat: This is an availability error-budget alert, not a latency alert. Although the histogram measures duration, the rule uses the histogram's request counts to measure failures. If your SLO also treats responses slower than a threshold (for example, 1 second) as bad events, you should add a separate latency-based SLO alert.

## Verdict on the draft ladder

I measured after committing the draft, with `itsmlab load 3` on my own login (bloczektv): 60 s open-loop at
40 requests per second, latency-corrected. The p99 was 0.2162 s (p50 38.1 ms, p95 69.3 ms, p99.9 243.8 ms). The
distribution has two modes: almost everything answers between 13 and 115 ms, and about 2 % of the requests fall
in a narrow slow mode between roughly 0.19 and 0.27 s. The p99 lands inside that slow mode.

In ChatGPT's ladder the bucket that holds 0.2162 s is (0.2, 0.3]. It is 0.1 s wide, and 0.1 / 0.2162 = 0.463, so
46.3 % of the p99, more than twice the 20 % that M-11 allows. The result does not depend on the exact draw: 0.95q
= 0.205 s and 1.05q = 0.227 s fall into the same bucket. `histogram_quantile(0.99, ...)` assumes the requests in
that bucket are spread evenly between 0.2 and 0.3 s, so it can report any value in that range, a 100 ms error on a
216 ms number, and it would hide the slow mode moving from 0.21 to 0.29 s completely. The ladder is not bad in
general (0.2 and 0.3 are reasonable round numbers), but it was chosen without the distribution, and between
0.1 and 0.5 s it has only three buckets. Verdict: **refuted**.

## The draft alert rule

ChatGPT's rule is the right shape: the SRE Workbook's fast-burn pair, 14.4 times the budget rate over 1 h and
5 m, the ratio of 5xx `_count` rates filtered on `job="svcdesk"` and the route template. I kept that shape for my
P1 alert. What I changed, and why:

- **The objective.** It assumed 99.9 % availability, a 0.1 % budget. My kb-index alone fails about 0.21 % of
  searches (5 of 2,399 in the run, all answered 502 by svcdesk), errors I cannot fix in svcdesk. Against a 99.9 %
  objective that is a permanent burn rate of 2.1: the 28-day budget would be gone in about 13 days of perfectly
  normal operation, and the slow-burn alert would ring all the time. I use 99 %, where the same 0.21 % is a burn
  rate of 0.21 (see `slo.md`).
- **The labels.** `severity: page` is not one of the course's severities and the `slo` label was missing; my rule
  has `service: svcdesk`, `slo: availability`, `severity: P1`.
- **A second alert.** A single fast-burn rule misses a slower leak that empties the budget in days. I added the
  6x, 6 h / 30 m alert at P2, as the multi-burn-rate approach the answer itself names.
- `for: 2m` I kept on the fast alert: with the 5 m short window it only delays a page by two minutes, and my
  tests pin it.

## Verdict on the instructor's flawed ladder

The flawed ladder spends twelve of its fourteen boundaries between 1 and 40 ms, where my median (38 ms) and the
fast mode live, and then jumps from 0.04 to 0.5 s. My p99 of 0.2162 s falls into (0.04, 0.5], a bucket 0.46 s wide:
0.46 / 0.2162 = 2.128, so 212.8 % of the p99, more than ten times the 20 % limit. `histogram_quantile` could
report anything between 40 and 500 ms for the p99, and because the whole slow mode sits inside that one bucket,
the dashboard could not tell a healthy 216 ms tail from a 480 ms one. It fails M-11 for every profile of this lab
and for mine. Verdict: **refuted**.

My own ladder (28 boundaries, in `src/svcdesk/metrics.py` and explained in `slo.md`) puts the same p99 in
(0.21, 0.22], 0.01 / 0.2162 = 4.6 % of it; a re-measurement gave q = 0.2146 s in the same bucket and a histogram
p99 of 0.2107 s.
