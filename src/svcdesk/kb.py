# ai-generated: 85% - Claude Code drafted against MONITORING-SPEC.md M-02 and HANDOUT.md "The dependency: kb-index"; reviewed by the author

"""GET /kb/search: one call to kb-index per request, no cache, no retry (MONITORING-SPEC.md M-02)."""

import os

import httpx

from .exceptions import ApiError

KB_INDEX_URL = os.environ.get("KB_INDEX_URL", "http://kb-index:8080").rstrip("/")
UPSTREAM_TIMEOUT_SECONDS = 5.0  # M-02 wants at least 2 s; the slowest seeded latency is far below this
MAX_QUERY_LENGTH = 200

# One pooled client for the process. httpx never retries on its own (transport retries default to 0).
_client = httpx.AsyncClient(
    timeout=UPSTREAM_TIMEOUT_SECONDS,
    limits=httpx.Limits(max_connections=128, max_keepalive_connections=64),
)


class UpstreamUnavailable(ApiError):
    def __init__(self, message: str):
        super().__init__(502, "upstream_unavailable", message)


def validate_query(q: str | None) -> str:
    if q is None or len(q) == 0:
        raise ApiError(400, "validation", "q is required (1 to 200 characters)")
    if len(q) > MAX_QUERY_LENGTH:
        raise ApiError(400, "validation", f"q is longer than {MAX_QUERY_LENGTH} characters")
    return q


async def search(q: str) -> dict:
    try:
        upstream = await _client.get(f"{KB_INDEX_URL}/search", params={"q": q})
    except httpx.HTTPError as exc:
        raise UpstreamUnavailable(f"kb-index did not answer: {type(exc).__name__}") from exc
    if upstream.status_code != 200:
        raise UpstreamUnavailable(f"kb-index answered {upstream.status_code}")
    try:
        hits = upstream.json()["hits"]
    except (ValueError, KeyError, TypeError) as exc:
        raise UpstreamUnavailable("kb-index answered without hits") from exc
    return {"query": q, "hits": hits}


async def close() -> None:
    await _client.aclose()
