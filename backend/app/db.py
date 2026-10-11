"""Tiny SQLite store for dummy users, sessions, owned cards and quiz questions."""

import json
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
CREATE TABLE IF NOT EXISTS quiz_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    card_id TEXT NOT NULL,
    venue TEXT NOT NULL,
    option_ids TEXT NOT NULL,
    answered INTEGER NOT NULL DEFAULT 0
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


def get_or_create_user(username: str) -> tuple[dict, bool]:
    """Returns (user, created)."""
    with connect() as conn:
        row = conn.execute("SELECT id, username FROM users WHERE username = ?", (username,)).fetchone()
        if row:
            return dict(row), False
        cur = conn.execute("INSERT INTO users (username) VALUES (?)", (username,))
        return {"id": cur.lastrowid, "username": username}, True


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


def grant_cards(user_id: int, card_ids: list[str]) -> set[str]:
    """Adds free starter-pack cards (edition 'starter', worth no reward points). Returns the ids
    the user did not own before."""
    with connect() as conn:
        new_ids = set()
        for cid in card_ids:
            cur = conn.execute(
                "INSERT OR IGNORE INTO owned_cards (user_id, card_id, edition) VALUES (?, ?, 'starter')",
                (user_id, cid),
            )
            if cur.rowcount:
                new_ids.add(cid)
        return new_ids


def grant_card(user_id: int, card_id: str, edition: str) -> str | None:
    """Gives the card in the given edition. 'new' if it was not owned, 'upgraded' if an owned
    standard card became a stadium edition, None if nothing changed."""
    with connect() as conn:
        row = conn.execute(
            "SELECT edition FROM owned_cards WHERE user_id = ? AND card_id = ?", (user_id, card_id)
        ).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO owned_cards (user_id, card_id, edition) VALUES (?, ?, ?)", (user_id, card_id, edition)
            )
            return "new"
        if row["edition"] != "stadium" and edition == "stadium":
            conn.execute(
                "UPDATE owned_cards SET edition = 'stadium' WHERE user_id = ? AND card_id = ?", (user_id, card_id)
            )
            return "upgraded"
        return None


def clear_cards(user_id: int):
    with connect() as conn:
        conn.execute("DELETE FROM owned_cards WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM quiz_questions WHERE user_id = ?", (user_id,))


def create_quiz(user_id: int, venue: str, questions: list[tuple[str, list[str]]]) -> list[int]:
    """Replaces the user's open questions with new ones. questions: (card_id, option_ids). Returns ids."""
    with connect() as conn:
        conn.execute("DELETE FROM quiz_questions WHERE user_id = ? AND answered = 0", (user_id,))
        ids = []
        for card_id, option_ids in questions:
            cur = conn.execute(
                "INSERT INTO quiz_questions (user_id, card_id, venue, option_ids) VALUES (?, ?, ?, ?)",
                (user_id, card_id, venue, json.dumps(option_ids)),
            )
            ids.append(cur.lastrowid)
        return ids


def get_question(user_id: int, question_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM quiz_questions WHERE id = ? AND user_id = ?", (question_id, user_id)
        ).fetchone()
        return {**dict(row), "option_ids": json.loads(row["option_ids"])} if row else None


def mark_answered(question_id: int):
    with connect() as conn:
        conn.execute("UPDATE quiz_questions SET answered = 1 WHERE id = ?", (question_id,))
