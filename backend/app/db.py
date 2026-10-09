"""Tiny SQLite store for dummy users, sessions and owned cards."""

import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "hockey_cards.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS owned_cards (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    card_id TEXT NOT NULL,
    edition TEXT NOT NULL DEFAULT 'standard',
    acquired_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, card_id)
);
"""


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)


def get_or_create_user(username: str, starter_card_ids: list[str]) -> tuple[dict, bool]:
    """Returns (user, created). New users receive the starter cards."""
    with connect() as conn:
        row = conn.execute("SELECT id, username FROM users WHERE username = ?", (username,)).fetchone()
        if row:
            return dict(row), False
        cur = conn.execute("INSERT INTO users (username) VALUES (?)", (username,))
        user_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO owned_cards (user_id, card_id) VALUES (?, ?)",
            [(user_id, cid) for cid in starter_card_ids],
        )
        return {"id": user_id, "username": username}, True


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(24)
    with connect() as conn:
        conn.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
    return token


def delete_session(token: str):
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def user_for_token(token: str) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT u.id, u.username FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?",
            (token,),
        ).fetchone()
        return dict(row) if row else None


def owned_cards(user_id: int) -> dict[str, str]:
    """card_id -> edition"""
    with connect() as conn:
        rows = conn.execute("SELECT card_id, edition FROM owned_cards WHERE user_id = ?", (user_id,)).fetchall()
        return {r["card_id"]: r["edition"] for r in rows}


def reset_cards(user_id: int, starter_card_ids: list[str]):
    with connect() as conn:
        conn.execute("DELETE FROM owned_cards WHERE user_id = ?", (user_id,))
        conn.executemany(
            "INSERT INTO owned_cards (user_id, card_id) VALUES (?, ?)",
            [(user_id, cid) for cid in starter_card_ids],
        )
