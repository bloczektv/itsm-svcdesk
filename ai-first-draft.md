---
lab3_first_draft:
  source: ai
  tool: "ChatGPT (free plan, model not shown in the UI), chatgpt.com, 10 October 2026"
  ladder: [0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
  verdict: TODO
  evidence: {p99_seconds: TODO, bucket: [TODO, TODO], relative_width: TODO}
lab3_flawed_ladder:
  verdict: refuted
  evidence: {p99_seconds: TODO, bucket: [TODO, TODO], relative_width: TODO}
---
<!-- ai-generated: ??% - TODO -->

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

TODO after the measurement.

## The draft alert rule

TODO after the measurement.

## Verdict on the instructor's flawed ladder

TODO after the measurement.
