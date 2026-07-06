"""
storage.py — persistent state for AutoDev Agent.

Replaces the old in-memory `pending_sandbox: dict` in main.py.

Why this exists:
  - In-memory dicts are wiped on every server restart / reload (uvicorn --reload
    restarts the whole process), silently losing any sandbox the user was
    reviewing and the entire run history.
  - There was no persisted history at all — the frontend kept it in React state,
    so a page refresh lost it too.

This module uses SQLite (stdlib, zero new dependencies) as a lightweight
embedded store. It's a single file on disk (AUTODEV_DB_PATH, defaults to
./autodev_state.db) so it survives restarts and is trivial to back up,
inspect (`sqlite3 autodev_state.db`), or swap out later for Postgres if the
project grows multi-instance.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from typing import Optional

DB_PATH = os.getenv(
    "AUTODEV_DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "autodev_state.db")
)

# How long a pending (never applied/rejected) sandbox is kept before it's
# considered abandoned and eligible for cleanup.
SANDBOX_TTL_SECONDS = int(os.getenv("SANDBOX_TTL_SECONDS", str(6 * 60 * 60)))  # 6h

# How many history rows we return by default.
DEFAULT_HISTORY_LIMIT = 200


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they don't exist yet. Safe to call on every startup."""
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sandboxes (
                id           TEXT PRIMARY KEY,
                task         TEXT NOT NULL,
                plan_summary TEXT,
                changes_json TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'pending',
                created_at   REAL NOT NULL,
                updated_at   REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id            TEXT PRIMARY KEY,
                sandbox_id    TEXT,
                ticket        TEXT NOT NULL,
                files_changed INTEGER NOT NULL,
                status        TEXT NOT NULL,
                result_json   TEXT,
                created_at    REAL NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_created_at ON history (created_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sandboxes_status ON sandboxes (status, created_at)"
        )


# ── Sandboxes ────────────────────────────────────────────────────────────────

def save_sandbox(task: str, plan_summary: str, changes: list) -> str:
    """Persist a freshly generated (not-yet-applied) sandbox. Returns its id."""
    sandbox_id = str(uuid.uuid4())
    now = time.time()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO sandboxes (id, task, plan_summary, changes_json, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """,
            (sandbox_id, task, plan_summary, json.dumps(changes), now, now),
        )
    return sandbox_id


def get_sandbox(sandbox_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM sandboxes WHERE id = ?", (sandbox_id,)).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "task": row["task"],
        "plan_summary": row["plan_summary"],
        "changes": json.loads(row["changes_json"]),
        "status": row["status"],
        "created_at": row["created_at"],
    }


def mark_sandbox(sandbox_id: str, status: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE sandboxes SET status = ?, updated_at = ? WHERE id = ?",
            (status, time.time(), sandbox_id),
        )


def delete_sandbox(sandbox_id: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM sandboxes WHERE id = ?", (sandbox_id,))


def cleanup_expired_sandboxes(ttl_seconds: int = SANDBOX_TTL_SECONDS) -> int:
    """Drop pending sandboxes older than the TTL. Returns rows deleted."""
    cutoff = time.time() - ttl_seconds
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM sandboxes WHERE status = 'pending' AND created_at < ?", (cutoff,)
        )
        return cur.rowcount


# ── History ──────────────────────────────────────────────────────────────────

def add_history_entry(
    ticket: str,
    files_changed: int,
    status: str,
    result: dict,
    sandbox_id: Optional[str] = None,
) -> dict:
    entry_id = str(uuid.uuid4())
    created_at = time.time()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO history (id, sandbox_id, ticket, files_changed, status, result_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (entry_id, sandbox_id, ticket, files_changed, status, json.dumps(result), created_at),
        )
    return {
        "id": entry_id,
        "sandbox_id": sandbox_id,
        "ticket": ticket,
        "filesChanged": files_changed,
        "status": status,
        "result": result,
        "timestamp": created_at,
    }


def get_history(limit: int = DEFAULT_HISTORY_LIMIT) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM history ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [
        {
            "id": r["id"],
            "sandbox_id": r["sandbox_id"],
            "ticket": r["ticket"],
            "filesChanged": r["files_changed"],
            "status": r["status"],
            "result": json.loads(r["result_json"]) if r["result_json"] else None,
            "timestamp": r["created_at"],
        }
        for r in rows
    ]


def clear_history() -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM history")
