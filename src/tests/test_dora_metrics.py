# ai-generated: 85% - Claude Code drafted, reviewed by the author

"""POST /dora/metrics: a small self-contained log whose expected metrics are computed by hand,
plus the contract properties METRIC-SPEC.md requires (purity, order independence, R-05 dedup,
rejections)."""

import requests

from ._client import BASE_URL

WINDOW = {"from": "2026-01-01T00:00:00Z", "to": "2026-01-08T00:00:00Z"}

EVENTS = [
    {"event_id": "c-1", "type": "commit", "at": "2026-01-01T10:00:00Z",
     "sha": "s-1", "branch": "main", "change_id": "CHG-1", "reverts": None},
    {"event_id": "c-2", "type": "commit", "at": "2026-01-02T10:00:00Z",
     "sha": "s-2", "branch": "main", "change_id": "CHG-2", "reverts": None},
    {"event_id": "d-1", "type": "deployment", "at": "2026-01-01T12:00:00Z",
     "deployment_id": "DEP-1", "environment": "production", "outcome": "success",
     "commits": ["s-1"], "unplanned": False, "caused_by": None},
    {"event_id": "d-2", "type": "deployment", "at": "2026-01-03T09:00:00Z",
     "deployment_id": "DEP-2", "environment": "production", "outcome": "failure",
     "commits": ["s-2"], "unplanned": False, "caused_by": None},
    {"event_id": "i-1", "type": "incident", "at": "2026-01-03T09:05:00Z",
     "incident_id": "INC-1", "phase": "opened", "deployments": ["DEP-2"]},
    {"event_id": "i-2", "type": "incident", "at": "2026-01-03T11:05:00Z",
     "incident_id": "INC-1", "phase": "resolved", "deployments": []},
]


def _post(events):
    resp = requests.post(f"{BASE_URL}/dora/metrics", json={"window": WINDOW, "events": events}, timeout=10)
    return resp


def test_metrics_matches_hand_computed_values():
    body = _post(EVENTS).json()
    assert body["deployment_frequency_per_day"] == 0.285714
    assert body["change_lead_time_seconds_p50"] == 7200
    assert body["failed_deployment_recovery_time_seconds_p50"] == 7500
    assert body["change_fail_rate"] == 0.5
    assert body["deployment_rework_rate"] == 0.0
    assert body["counts"]["deployments"] == 2
    assert body["ground_truth"]["changes_delivered"] == 1
    assert body["ground_truth"]["true_change_lead_time_seconds_p50"] == 7200


def test_metrics_is_a_pure_function():
    first = _post(EVENTS).json()
    second = _post(EVENTS).json()
    assert first == second


def test_metrics_is_order_independent():
    forward = _post(EVENTS).json()
    reversed_result = _post(list(reversed(EVENTS))).json()
    assert forward == reversed_result


def test_duplicate_events_are_ingested_once():
    once = _post(EVENTS).json()
    doubled = _post(EVENTS + EVENTS).json()
    assert once == doubled


def test_empty_log_returns_zeroed_metrics():
    body = _post([]).json()
    assert body["deployment_frequency_per_day"] == 0.0
    assert body["change_lead_time_seconds_p50"] is None
    assert body["change_fail_rate"] is None
    assert body["deployment_rework_rate"] is None
    assert body["counts"]["deployments"] == 0


def test_missing_window_is_rejected():
    resp = requests.post(f"{BASE_URL}/dora/metrics", json={"events": []}, timeout=10)
    assert resp.status_code in (400, 422)
    assert "error" in resp.json()


def test_empty_window_is_rejected():
    resp = requests.post(
        f"{BASE_URL}/dora/metrics",
        json={"window": {"from": "2026-01-08T00:00:00Z", "to": "2026-01-01T00:00:00Z"}, "events": []},
        timeout=10,
    )
    assert resp.status_code in (400, 422)


def test_malformed_revert_reference_is_rejected():
    bad_events = [
        {"event_id": "c-9", "type": "commit", "at": "2026-01-01T10:00:00Z",
         "sha": "s-9", "branch": "main", "change_id": None, "reverts": "s-does-not-exist"},
    ]
    resp = _post(bad_events)
    assert resp.status_code in (400, 422)
