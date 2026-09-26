# ai-generated: 85% - Claude Code drafted, reviewed by the author

"""GET /dora/ticket-events."""

import requests

from ._client import BASE_URL


def test_ticket_events_includes_created_ticket_in_order():
    created = requests.post(
        f"{BASE_URL}/tickets",
        json={
            "title": "ticket-events probe",
            "reporter": {"name": "Grace", "vip": False},
            "impact": 3,
            "urgency": 3,
        },
        timeout=10,
    ).json()

    resp = requests.get(f"{BASE_URL}/dora/ticket-events", timeout=10)
    assert resp.status_code == 200
    events = resp.json()

    mine = [e for e in events if e["ticket_id"] == created["id"]]
    assert mine == [{
        "ticket_id": created["id"], "at": created["created_at"],
        "phase": "created", "priority": created["priority"], "state": "new",
    }]

    keys = [(e["at"], e["ticket_id"]) for e in events]
    assert keys == sorted(keys)
