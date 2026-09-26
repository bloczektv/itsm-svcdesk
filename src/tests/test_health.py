# ai-generated: 85% - Claude Code drafted, reviewed by the author

"""GET /health."""

import requests

from ._client import BASE_URL


def test_health_returns_ok():
    resp = requests.get(f"{BASE_URL}/health", timeout=10)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
