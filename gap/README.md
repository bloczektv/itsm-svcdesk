<!-- ai-generated: 60% - Claude Code ran the measurement through Toxiproxy and drafted the explanation; I checked the numbers against the run -->

# The client-server latency gap (Stretch 2, M-30)

**Setup.** Toxiproxy 2.12.0 next to svcdesk on the compose network, a proxy `svcdesk` listening on 8666 with
upstream `svcdesk:8080`, and one toxic: `latency`, stream `downstream`, toxicity 1, latency 100 ms, jitter 10 ms.
Measured with `itsmlab load 3 --base-url http://host.docker.internal:8666` (the published M-08 load: 60 s open-loop,
40 requests per second, latency-corrected), against my own login's kb-index profile.

| | p99 |
|---|---|
| client (oha, through the proxy) | 0.3209 s |
| server (`histogram_quantile(0.99)` over the run's increments of my `/kb/search` histogram) | 0.2086 s |
| gap | 0.1123 s |

**Why the gap exists.** svcdesk's histogram starts its timer when the request reaches the ASGI app and stops it
when the last byte of the answer leaves it. Everything that happens outside that interval is invisible to it: the
network between the client and the service, any proxy or load balancer, and here the toxic, which holds every
answer for 100 ms (plus or minus 10 ms of jitter) on its way back to the client. The server therefore still reports
its own distribution, p99 0.209 s, which is the same as without the proxy (0.20 to 0.22 s in my runs, kb-index's
slow mode), while the client sees every request shifted by about 100 ms: its p50 went from 38 ms to 145 ms and its
p99 from about 0.21 s to 0.32 s.

**Why the gap is about 112 ms and not exactly 100 ms.** The jitter adds up to 10 ms on top of the 100 ms for some
requests, and the client's p99 is drawn from the tail of that sum: the slowest server answers that also got the
largest delay. A little comes from queueing in the proxy and from the extra hop through Docker's network. The gap is
not a constant added to every percentile, but close to the toxic's latency because the toxic is the same for every
request.

**What it means for the SLO.** My latency SLI is measured on the server, so it would stay green while users behind a
slow network or a misbehaving proxy wait 100 ms longer on every search. That is the right choice for an SLO that
svcdesk's team owns (they cannot fix the network), but a user-facing promise needs the client's view too, from a
synthetic probe or from the load balancer's own histogram, and the two should not be confused on one dashboard.
