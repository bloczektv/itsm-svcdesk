---
lab4_postmortem:
  ticket: "1224ad8d-06a8-4ae3-865a-da2015a4ddb5"
  detecting_alert: ShopCheckoutErrors
  onset: 2026-10-12T07:05:45Z
  detection: 2026-10-12T07:09:19Z
  acknowledgement: 2026-10-12T07:10:07Z
  recovery: 2026-10-12T07:12:19Z
  mttd_seconds: 214
  mtta_seconds: 48
  mttr_seconds: 394
  identified_flags: [productCatalogFailure, adManualGc, recommendationCacheFailure]
---
<!-- ai-generated: 70% - Claude Code drafted the prose from my investigation of the recording and ran every query; I chose the flags, the action items and reviewed the text -->

# Postmortem: some orders and product pages failed, and the shop became slow, for seven minutes

## Date

The incident happened on Monday 12 October 2026 between 07:05:45Z and 07:13:20Z (UTC). This postmortem was written
on 25 October 2026 from the recorded incident `lab4-rec-3`, its Prometheus snapshot and its P1 ticket.

## Authors

bloczektv, analysing the recorded incident as the on-call engineer would have. The page, the ticket and its
acknowledgement were made at the time by the lecturer, who was on call during the recording.

## Status

Complete for the incident: service was restored at 07:12:19Z and the incident ticket can close. The problem record
below stays open, and the action items are not started.

## Summary

At 07:05:45Z three feature flags started failing at once in the shop. For about seven minutes product-catalog failed
one GetProduct call in thirteen, which made some orders and product pages fail, and the ad service stalled in garbage
collection, which made the storefront slow. A P1 alert on checkout errors paged the on-call after 3.5 minutes, and
switching the flags off restored service by 07:12:19Z.

## Impact

Measured over the fault window 07:05:45Z-07:13:20Z with 9-minute `increase()` at 07:14:46Z; the span metrics are
pushed once a minute, so counts are approximate to one sample.

- **Orders.** About 2 of 63 orders failed (3 %), each a PlaceOrder that could not read a product:
  `sum(increase(traces_span_metrics_calls_total{service_name="checkout",span_kind="SPAN_KIND_SERVER",span_name="oteldemo.CheckoutService/PlaceOrder",status_code="STATUS_CODE_ERROR"}[9m]))`
  = 2.1 against 62.9 for the same query without the status filter. Over the 5-minute window at 07:09 the failure
  ratio peaked at 9.8 %.
- **Storefront errors.** About 80 of 2,100 frontend requests failed (4 %): 49 product pages, 28 recommendation panels
  and 4 checkouts, from
  `sum by (span_name) (increase(traces_span_metrics_calls_total{service_name="frontend",span_kind="SPAN_KIND_SERVER",status_code="STATUS_CODE_ERROR"}[9m]))`.
  None failed in the ten minutes before the onset.
- **Storefront latency.** The frontend's p99 rose from 47 ms to 700-920 ms from 07:08 to the end of the snapshot:
  `histogram_quantile(0.99, sum by (le) (rate(traces_span_metrics_duration_milliseconds_bucket{service_name="frontend",span_kind="SPAN_KIND_SERVER"}[5m])))`.
  The median stayed at 4 ms, so the slow tail was the pages that show ads: ad's GetAds median went from 4 ms to
  about 600 ms and its p99 to 918 ms (the same query with `service_name="ad"`).
- **Recommendations** kept working (no errors, latency unchanged), but recommendation stopped asking product-catalog
  for the product list on every request: the ratio of its ListProducts calls to ListRecommendations requests fell
  from 1.00 to 0.49 by 07:12. No user saw this; it is a memory leak waiting to happen.

Nobody lost data, and payment, cart, shipping and email worked normally throughout.

## Root Causes

Three feature flags were switched on in production at the same instant, with no change record and no telemetry
that names a flag:

- `productCatalogFailure` made product-catalog fail GetProduct for one product in ten. The failure propagates
  unchanged to every caller: checkout aborts the whole order, and the frontend fails the product page and the
  recommendation panel that lists that product.
- `adManualGc` made the ad service trigger full garbage collections: ad's JVM went from no measurable GC time to
  0.116 s of GC per second (`sum(rate(jvm_gc_duration_seconds_sum{service_name="ad"}[5m]))`), and every GetAds call
  waited for it.
- `recommendationCacheFailure` switched recommendation to its product cache, which on this flag grows without bound
  instead of refreshing; it showed only as the halved ListProducts ratio and a slow memory growth (recommendation
  RSS 72.97 MB to 73.86 MB in the window).

The deeper cause is the same for all three: a flag change is a production change, but it was neither reviewed,
announced nor visible in the metrics, and product-catalog's callers have no fallback for a single failed product.

## Trigger

The flags switched on at 07:05:45Z, the first sample of the injector's `seeded_fault_active` (armed at 07:03:30Z).
The first symptoms reached the span metrics with the next pushes: ad's latency and GC at 07:07, product-catalog's and
the frontend's errors at 07:08.

## Resolution

The workaround was to switch the three flags off through the flag service. The on-call acknowledged the page at
07:10:07Z and rolled the failing flags back. Checkout's error ratio fell below the alert's threshold and the P1
resolved at 07:12:19Z; by 07:13:20Z all three flags were off (`seeded_fault_active` fell to 0). The snapshot does not record the order in which the three were switched off. No code was deployed and nothing
was restarted.

## Detection

`ShopCheckoutErrors` (P1, checkout's PlaceOrder error ratio) detected the fault at 07:09:19Z, 214 s after the onset
(MTTD), and its page reached the pager at 07:09:34Z
(`itsm_pager_notifications_total{receiver="pager",status="firing"}` rose from 0 to 1). The ticket was opened at
07:09:37Z and acknowledged at 07:10:07Z, 48 s after the alert (MTTA). `ShopServiceErrors` (P2) followed for
product-catalog at 07:09:39Z and the frontend at 07:09:49Z; the inhibition held them back from chat while the P1
fired, so chat heard of them only at 07:12:54Z, after the P1 resolved.

Most of the 214 s is the metrics' own delay: span metrics arrive once a minute and the rule needs a 5-minute rate
and its `for:`. The ad fault was never detected by any alert: no rule watched latency outside checkout. Without the
page, the first to notice would have been shoppers on slow product pages (frontend p99 near 900 ms from 07:08), and
the recommendation fault would have been noticed only when the service ran out of memory.

## Action Items

| Action Item | Type | Owner | Bug |
|---|---|---|---|
| Treat feature-flag changes as production changes: a change record and a canary rollout that rolls back on the checkout SLO | prevent | platform team | ITSM-42 |
| Export every flag change as a metric or Grafana annotation, so on-call and AI investigators can answer "what changed?" from telemetry | other | observability team | ITSM-43 |
| Alert on latency per downstream service (ad GetAds p95, frontend p99 > 500 ms) to chat, so latency-only faults are detected | prevent | on-call rotation | ITSM-44 |
| product-catalog callers degrade instead of failing: checkout and frontend skip or retry one unreadable product | mitigate | shop developers | ITSM-45 |
| Runbook: "switch off recently changed flags" as the first mitigation, and ask AI investigators about errors, latency and resources with 5-minute windows | process | on-call rotation | ITSM-46 |

## Lessons Learned

### What went well

The paging alert was a symptom alert on checkout and it fired on the error part of the fault within 3.5 minutes;
the page reached the phone in 15 s and the ticket was acknowledged 48 s after the alert. The inhibition kept chat
quiet while the on-call worked the P1. Switching flags off restored service without a deploy.

### What went wrong

Two of the three faults raised no alert at all, because they caused latency and changed behaviour without errors.
Both AI investigators followed the errors and missed them too (ledger H1-H4 in both files). The P1 resolved at
07:12:19Z while a flag was still failing until 07:13:20Z, so the alert's recovery understates how long the fault
lasted.

### Where we got lucky

Only one product in ten failed, so most orders still went through, and payment was not among the flags. The
recommendation cache leak was switched off after seven minutes, long before it could exhaust memory; left on, it
would have crashed recommendation hours later with no link to this change.

## Timeline

All times UTC, Monday 12 October 2026.

- 06:53:15 - the injector starts; the shop is healthy, no alert fires in the ten minutes before the onset.
- 07:03:30 - the injector is armed.
- 07:04:45 - last quiet minute: no shop service answers with errors, frontend p99 47 ms.
- 07:05:45 - **onset**: the three flags switch on.
- 07:07 - ad's p99 jumps from 5 ms to 918 ms and its GC time appears; no alert watches it.
- 07:08 - product-catalog GetProduct errors (0.085/s) and frontend errors appear in the span metrics.
- 07:09:19 - **detection**: `ShopCheckoutErrors` (P1) fires on checkout's PlaceOrder error ratio.
- 07:09:34 - the page reaches the on-call's phone.
- 07:09:37 - P1 ticket `1224ad8d-06a8-4ae3-865a-da2015a4ddb5` opened.
- 07:09:39 and 07:09:49 - `ShopServiceErrors` (P2) fires for product-catalog and frontend, muted by the inhibition.
- 07:10:07 - **acknowledgement** of the ticket; the on-call starts rolling back the failing flags.
- 07:12:19 - **recovery**: `ShopCheckoutErrors` resolves; the pager gets the resolved
  notification at 07:12:34.
- 07:13:20 - all three flags are off (`seeded_fault_active` = 0).
- 07:13:09-07:14 - the remaining P2 alerts resolve; chat gets one firing and one resolved notification.
- 2026-10-25, analysis of the recording: the Gemini investigator's H2 (ledger `ai-rca-eval.json`) blamed
  product-catalog's GetProduct; query
  `sum(rate(traces_span_metrics_calls_total{service_name="product-catalog",span_name="oteldemo.ProductCatalogService/GetProduct",span_kind="SPAN_KIND_SERVER",status_code="STATUS_CODE_ERROR"}[5m])) > 0.02`
  returned 0.149 at 07:11:00 and nothing at 07:00:45, which confirmed the errors flag. Its H4 ("error rate ...
  essentially zero" before 07:05) was refuted by
  `sum(rate(traces_span_metrics_calls_total{status_code="STATUS_CODE_ERROR"}[5m] offset 7m)) < 0.01` (nothing; the
  baseline is 0.158/s of load-generator noise). Neither AI hypothesis pointed at ad or recommendation; those two flags
  were identified from the queries in Root Causes.

## Supporting information

- `itsmlab incident 4` on `incident/tsdb-snapshot.tar.gz`: run `fe6ecd21acce7a08`, onset 07:05:45Z, detection
  07:09:19Z by `ShopCheckoutErrors`, acknowledgement 07:10:07Z, recovery 07:12:19Z, MTTD 214 s, MTTA 48 s, MTTR 394 s.
- The P1 ticket as svcdesk returned it: `incident/ticket.json`.
- The AI ledgers and transcripts: `ai-rca-eval.json` with `ai-rca/transcript.md` (gemini-3.5-flash-lite), and
  `ai-rca-eval-2.json` with `ai-rca/second/transcript.md` (qwen3:4b-instruct); `ai-rca/COMPARISON.md` compares them.
- The flags were identified against INCIDENT-SPEC.md section 2.2 with these queries on the snapshot (served on port
  19090): product-catalog server errors by span; `histogram_quantile(0.99, ...)` per service for ad's latency;
  `sum(rate(jvm_gc_duration_seconds_sum{service_name="ad"}[5m]))`; the ratio of recommendation's ListProducts to
  ListRecommendations calls; and, for the flags ruled out, payment's server errors (none), shipping's and
  product-catalog's p99 (unchanged), frontend traffic (flat) and email's memory and uptime (flat, no restart).
- The alerting rules and routing tree written for the next incident: `prometheus/demo-alerts.yml`,
  `alertmanager/alertmanager.yml`, `alertmanager/routing-tests.yml`. The regulators' clocks: `comms-log.md`.

## Problem record

- Incident record: 1224ad8d-06a8-4ae3-865a-da2015a4ddb5, the P1 ticket, acknowledged at 07:10:07Z; it closes because service was restored at 07:12:19Z.
- Root cause: three feature flags switched on in production without a change record: productCatalogFailure (GetProduct fails for one product in ten, propagated to checkout and the frontend), adManualGc (forced garbage collection stalls ad) and recommendationCacheFailure (an unbounded cache in recommendation).
- Known error: flag changes are invisible in telemetry and unreviewed, and product-catalog's callers fail hard on one unreadable product; until ITSM-42, ITSM-43 and ITSM-45 are done the same change can recur and be found only by its symptoms.
- Workaround: switch the failing flags off in the flag service (all three were off by 07:13:20Z); when the flag is unknown, compare the current flag document with the last known good one and turn off what differs.
