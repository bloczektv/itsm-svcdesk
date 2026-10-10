# ai-generated: 85% - Claude Code drafted the ASGI middleware against MONITORING-SPEC.md M-03 to M-07; reviewed by the author

"""The RED histogram of svcdesk (MONITORING-SPEC.md M-03 to M-07) and its /metrics exposition.

One pure ASGI middleware observes every answered request exactly once, so no route needs a decorator: the
timer starts before the app sees the request and stops after the last body chunk is sent. The route label is the
template FastAPI matched (the router writes it into the shared ASGI scope), never the raw path.
"""

import time

from prometheus_client import REGISTRY, Histogram, generate_latest

# Seconds, 28 finite boundaries (M-06 allows 30). Designed from `itsmlab load 3` on login bloczektv: q = 0.216 s
# sits in kb-index's slow mode (about 2 % of requests between 0.19 and 0.27 s). Steps of 10 ms from 0.15 to 0.28 s
# resolve any q from 0.15 to 0.30 s (M-11: bucket width <= 20 % of q); 0.3 s is the latency SLI threshold (M-13).
LADDER: tuple[float, ...] | None = (
    0.005, 0.01, 0.02, 0.03, 0.04, 0.05, 0.075, 0.1, 0.15,
    0.16, 0.17, 0.18, 0.19, 0.2, 0.21, 0.22, 0.23, 0.24, 0.25, 0.26, 0.27, 0.28,
    0.3, 0.4, 0.5, 1.0, 2.0, 5.0,
)

UNMATCHED_ROUTE = "unmatched"
METRICS_PATH = "/metrics"
CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"
_KNOWN_METHODS = {"GET", "HEAD", "POST", "PUT", "DELETE", "CONNECT", "OPTIONS", "TRACE", "PATCH"}

_histogram_kwargs = {"buckets": LADDER} if LADDER else {}
REQUEST_DURATION = Histogram(
    "http_server_request_duration_seconds",
    "Duration of HTTP server requests, from the first byte received to the last byte sent.",
    ["http_request_method", "http_route", "http_response_status_code"],
    **_histogram_kwargs,
)


def render_metrics() -> bytes:
    return generate_latest(REGISTRY)


class RequestMetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] == METRICS_PATH:
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status = {"code": 500}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            route = scope.get("route")
            template = getattr(route, "path", None) or UNMATCHED_ROUTE
            method = scope["method"] if scope["method"] in _KNOWN_METHODS else "_OTHER"
            REQUEST_DURATION.labels(method, template, str(status["code"])).observe(time.perf_counter() - start)
