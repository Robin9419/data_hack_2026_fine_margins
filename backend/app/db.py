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
    copies INTEGER NOT NULL DEFAULT 1,
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
        columns = [r["name"] for r in conn.execute("PRAGMA table_info(users)")]
        if "favorite_team" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN favorite_team TEXT")
        if "last_daily_claim" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN last_daily_claim TEXT")
        card_columns = [r["name"] for r in conn.execute("PRAGMA table_info(owned_cards)")]
        if "copies" not in card_columns:
            conn.execute("ALTER TABLE owned_cards ADD COLUMN copies INTEGER NOT NULL DEFAULT 1")


def last_daily_claim(user_id: int) -> str | None:
    with connect() as conn:
        row = conn.execute("SELECT last_daily_claim FROM users WHERE id = ?", (user_id,)).fetchone()
        return row["last_daily_claim"] if row else None


def claim_daily(user_id: int, today: str) -> bool:
    """Marks today's daily card as claimed. False if it already was (atomic, so double clicks can't claim twice)."""
    with connect() as conn:
        cur = conn.execute(
            "UPDATE users SET last_daily_claim = ? WHERE id = ? AND (last_daily_claim IS NULL OR last_daily_claim <> ?)",
            (today, user_id, today),
        )
        return cur.rowcount > 0


def get_or_create_user(username: str, favorite_team: str | None = None) -> tuple[dict, bool]:
    """Returns (user, created). The favorite team is only stored for a new account."""
    with connect() as conn:
        row = conn.execute(
            "SELECT id, username, favorite_team FROM users WHERE username = ?", (username,)
        ).fetchone()
        if row:
            return dict(row), False
        cur = conn.execute("INSERT INTO users (username, favorite_team) VALUES (?, ?)", (username, favorite_team))
        return {"id": cur.lastrowid, "username": username, "favorite_team": favorite_team}, True


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
            "SELECT u.id, u.username, u.favorite_team FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?",
            (token,),
        ).fetchone()
        return dict(row) if row else None


def owned_cards(user_id: int) -> dict[str, str]:
    """card_id -> edition"""
    with connect() as conn:
        rows = conn.execute("SELECT card_id, edition FROM owned_cards WHERE user_id = ?", (user_id,)).fetchall()
        return {r["card_id"]: r["edition"] for r in rows}


def card_copies(user_id: int) -> dict[str, int]:
    """card_id -> how many copies the user holds (more than 1 only for duplicate base cards)."""
    with connect() as conn:
        rows = conn.execute("SELECT card_id, copies FROM owned_cards WHERE user_id = ?", (user_id,)).fetchall()
        return {r["card_id"]: r["copies"] for r in rows}


def grant_cards(user_id: int, card_ids: list[str]) -> set[str]:
    """Adds free base cards (edition 'starter', worth no reward points). A card the user already owns becomes one
    more copy, which can be traded in later. Returns the ids the user did not own before."""
    with connect() as conn:
        new_ids = set()
        for cid in card_ids:
            cur = conn.execute(
                "INSERT OR IGNORE INTO owned_cards (user_id, card_id, edition) VALUES (?, ?, 'starter')",
                (user_id, cid),
            )
            if cur.rowcount:
                new_ids.add(cid)
            else:
                conn.execute(
                    "UPDATE owned_cards SET copies = copies + 1 WHERE user_id = ? AND card_id = ?", (user_id, cid)
                )
        return new_ids


def remove_copies(user_id: int, card_ids: list[str]) -> bool:
    """Takes one copy per id in card_ids (an id may repeat to take several copies of the same card). A card whose
    last copy goes leaves the collection. All or nothing: False, and nothing changes, if the user is short of any."""
    wanted = {cid: card_ids.count(cid) for cid in set(card_ids)}
    with connect() as conn:
        for cid, n in wanted.items():
            cur = conn.execute(
                "UPDATE owned_cards SET copies = copies - ? WHERE user_id = ? AND card_id = ? AND copies >= ?",
                (n, user_id, cid, n),
            )
            if not cur.rowcount:
                conn.rollback()
                return False
        conn.execute("DELETE FROM owned_cards WHERE user_id = ? AND copies <= 0", (user_id,))
        return True


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
