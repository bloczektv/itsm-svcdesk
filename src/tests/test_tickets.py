# ai-generated: 85% - Claude Code drafted, reviewed by the author

"""Regression coverage for the Lab 1 ticket endpoints, so Lab 2 cannot silently break them."""

import requests

from ._client import BASE_URL


def _create_ticket(**overrides):
    body = {
        "title": "printer on fire",
        "description": "smoke coming from the third floor printer",
        "reporter": {"name": "Ada", "email": "ada@example.com", "vip": False},
        "impact": 2,
        "urgency": 2,
    }
    body.update(overrides)
    resp = requests.post(f"{BASE_URL}/tickets", json=body, timeout=10)
    assert resp.status_code == 201
    return resp.json()


def test_create_ticket_returns_expected_shape():
    ticket = _create_ticket()
    assert ticket["state"] == "new"
    assert ticket["priority"] in ("P1", "P2", "P3", "P4")
    assert ticket["created_at"]


def test_get_ticket_roundtrip():
    created = _create_ticket()
    resp = requests.get(f"{BASE_URL}/tickets/{created['id']}", timeout=10)
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_list_tickets_filters_by_state():
    _create_ticket()
    resp = requests.get(f"{BASE_URL}/tickets", params={"state": "new"}, timeout=10)
    assert resp.status_code == 200
    assert all(t["state"] == "new" for t in resp.json())


def test_ticket_lifecycle_ack_resolve_close():
    ticket = _create_ticket()
    ticket_id = ticket["id"]
    ack = requests.post(f"{BASE_URL}/tickets/{ticket_id}/ack", timeout=10)
    assert ack.status_code == 200
    assert ack.json()["state"] == "acknowledged"
    start = requests.post(f"{BASE_URL}/tickets/{ticket_id}/start", timeout=10)
    assert start.status_code == 200
    resolve = requests.post(f"{BASE_URL}/tickets/{ticket_id}/resolve", timeout=10)
    assert resolve.status_code == 200
    assert resolve.json()["resolved_at"]
    close = requests.post(f"{BASE_URL}/tickets/{ticket_id}/close", timeout=10)
    assert close.status_code == 200
    assert close.json()["state"] == "closed"
