# ai-generated: 85% - Claude Code drafted, reviewed by the author

"""SQLite-backed persistence (R-23): tickets survive a restart of the svcdesk container. Standard
library only, so the image needs nothing beyond FastAPI and Uvicorn at build time."""

import os
import sqlite3
import threading
from typing import Optional

from .models import Ticket

DB_PATH = os.environ.get("SVCDESK_DB", "/data/svcdesk.db")

_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None

_COLUMNS = (
    "id", "title", "description", "reporter_name", "reporter_email", "reporter_vip",
    "impact", "urgency", "priority", "state", "related_to", "created_at",
    "ack_due_at", "resolve_due_at", "acknowledged_at", "resolved_at", "closed_at",
)


def init_db() -> None:
    global _conn
    directory = os.path.dirname(DB_PATH)
    if directory:
        os.makedirs(directory, exist_ok=True)
    _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            reporter_name TEXT NOT NULL,
            reporter_email TEXT,
            reporter_vip INTEGER NOT NULL,
            impact INTEGER NOT NULL,
            urgency INTEGER NOT NULL,
            priority TEXT NOT NULL,
            state TEXT NOT NULL,
            related_to TEXT,
            created_at TEXT NOT NULL,
            ack_due_at TEXT NOT NULL,
            resolve_due_at TEXT NOT NULL,
            acknowledged_at TEXT,
            resolved_at TEXT,
            closed_at TEXT
        )
        """
    )
    _conn.commit()


def _row_to_ticket(row: sqlite3.Row) -> Ticket:
    return Ticket(
        id=row["id"], title=row["title"], description=row["description"],
        reporter_name=row["reporter_name"], reporter_email=row["reporter_email"],
        reporter_vip=bool(row["reporter_vip"]), impact=row["impact"], urgency=row["urgency"],
        priority=row["priority"], state=row["state"], related_to=row["related_to"],
        created_at=row["created_at"], ack_due_at=row["ack_due_at"], resolve_due_at=row["resolve_due_at"],
        acknowledged_at=row["acknowledged_at"], resolved_at=row["resolved_at"], closed_at=row["closed_at"],
    )


def save(ticket: Ticket) -> None:
    values = tuple(getattr(ticket, c) if c != "reporter_vip" else int(ticket.reporter_vip) for c in _COLUMNS)
    placeholders = ",".join("?" for _ in _COLUMNS)
    updates = ",".join(f"{c}=excluded.{c}" for c in _COLUMNS if c != "id")
    with _lock:
        _conn.execute(
            f"INSERT INTO tickets ({','.join(_COLUMNS)}) VALUES ({placeholders}) "
            f"ON CONFLICT(id) DO UPDATE SET {updates}",
            values,
        )
        _conn.commit()


def get(ticket_id: str) -> Optional[Ticket]:
    with _lock:
        row = _conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    return _row_to_ticket(row) if row else None


def list_all(state: Optional[str] = None, priority: Optional[str] = None) -> list[Ticket]:
    query = "SELECT * FROM tickets WHERE 1=1"
    params: list[str] = []
    if state:
        query += " AND state = ?"
        params.append(state)
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    with _lock:
        rows = _conn.execute(query, params).fetchall()
    return [_row_to_ticket(r) for r in rows]
