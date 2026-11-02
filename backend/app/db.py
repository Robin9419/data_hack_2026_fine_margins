"""Tiny SQLite store for dummy users, sessions, owned cards, quiz questions and tournament predictions."""

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
CREATE TABLE IF NOT EXISTS predictions (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    game_id TEXT NOT NULL,
    question TEXT NOT NULL,
    option_id TEXT NOT NULL,
    PRIMARY KEY (user_id, game_id, question)
);
-- A row once the game is played on the user's timeline: the predictions are locked and `correct` packs are earned.
CREATE TABLE IF NOT EXISTS game_packs (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    game_id TEXT NOT NULL,
    correct INTEGER NOT NULL,
    claimed INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, game_id)
);
-- Ones to Watch packs: one per goal or assist of an owned Road to Final card's player in a game (packs = points),
-- recorded when the game is played on the user's timeline.
CREATE TABLE IF NOT EXISTS watch_packs (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    game_id TEXT NOT NULL,
    card_id TEXT NOT NULL,
    packs INTEGER NOT NULL DEFAULT 1,
    claimed INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, game_id, card_id)
);
-- The collector cards the user has been shown the unlock of. A collector is earned by owning all base cards of a club
-- and stays earned, so each is announced once.
CREATE TABLE IF NOT EXISTS announced_collectors (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    card_id TEXT NOT NULL,
    PRIMARY KEY (user_id, card_id)
);
-- The trivia rounds the user played, one per gameday: they watched those games live or in the stadium, so the round is
-- offered once per stage of the timeline.
CREATE TABLE IF NOT EXISTS trivia_rounds (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    PRIMARY KEY (user_id, stage)
);
-- The social channels the user followed for free cards (one channel per stage of the timeline, see main.SOCIALS).
CREATE TABLE IF NOT EXISTS social_follows (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    PRIMARY KEY (user_id, platform)
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
        if "stage" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN stage TEXT NOT NULL DEFAULT 'pre'")
        card_columns = [r["name"] for r in conn.execute("PRAGMA table_info(owned_cards)")]
        if "copies" not in card_columns:
            conn.execute("ALTER TABLE owned_cards ADD COLUMN copies INTEGER NOT NULL DEFAULT 1")
        watch_columns = [r["name"] for r in conn.execute("PRAGMA table_info(watch_packs)")]
        if "packs" not in watch_columns:
            conn.execute("ALTER TABLE watch_packs ADD COLUMN packs INTEGER NOT NULL DEFAULT 1")


def last_daily_claim(user_id: int) -> str | None:
    """The timeline stage of the last daily card claimed."""
    with connect() as conn:
        row = conn.execute("SELECT last_daily_claim FROM users WHERE id = ?", (user_id,)).fetchone()
        return row["last_daily_claim"] if row else None


def claim_daily(user_id: int, stage: str) -> bool:
    """Marks the daily card of this stage as claimed. False if it already was (atomic, so double clicks can't claim
    twice)."""
    with connect() as conn:
        cur = conn.execute(
            "UPDATE users SET last_daily_claim = ? WHERE id = ? AND (last_daily_claim IS NULL OR last_daily_claim <> ?)",
            (stage, user_id, stage),
        )
        return cur.rowcount > 0


def trivia_played(user_id: int, stage: str) -> bool:
    with connect() as conn:
        return conn.execute("SELECT 1 FROM trivia_rounds WHERE user_id = ? AND stage = ?", (user_id, stage)).fetchone() is not None


def mark_trivia_played(user_id: int, stage: str):
    with connect() as conn:
        conn.execute("INSERT OR IGNORE INTO trivia_rounds (user_id, stage) VALUES (?, ?)", (user_id, stage))


def followed_socials(user_id: int) -> set[str]:
    with connect() as conn:
        rows = conn.execute("SELECT platform FROM social_follows WHERE user_id = ?", (user_id,)).fetchall()
        return {r["platform"] for r in rows}


def follow_social(user_id: int, platform: str) -> bool:
    """Records the follow. False if the user already follows this channel (atomic, so it pays out once)."""
    with connect() as conn:
        cur = conn.execute("INSERT OR IGNORE INTO social_follows (user_id, platform) VALUES (?, ?)", (user_id, platform))
        return cur.rowcount > 0


def get_or_create_user(username: str, favorite_team: str | None = None) -> tuple[dict, bool]:
    """Returns (user, created). The favorite team is only stored for a new account."""
    with connect() as conn:
        row = conn.execute(
            "SELECT id, username, favorite_team, stage FROM users WHERE username = ?", (username,)
        ).fetchone()
        if row:
            return dict(row), False
        cur = conn.execute("INSERT INTO users (username, favorite_team) VALUES (?, ?)", (username, favorite_team))
        return {"id": cur.lastrowid, "username": username, "favorite_team": favorite_team, "stage": "pre"}, True


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
            "SELECT u.id, u.username, u.favorite_team, u.stage FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?",
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
        conn.execute("DELETE FROM predictions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM game_packs WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM watch_packs WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM social_follows WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM trivia_rounds WHERE user_id = ?", (user_id,))
        conn.execute("UPDATE users SET stage = 'pre', last_daily_claim = NULL WHERE id = ?", (user_id,))


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


def set_stage(user_id: int, stage: str):
    with connect() as conn:
        conn.execute("UPDATE users SET stage = ? WHERE id = ?", (stage, user_id))


def predictions(user_id: int) -> dict[str, dict[str, str]]:
    """game_id -> {question id -> option id}"""
    with connect() as conn:
        rows = conn.execute("SELECT game_id, question, option_id FROM predictions WHERE user_id = ?", (user_id,)).fetchall()
    result: dict[str, dict[str, str]] = {}
    for r in rows:
        result.setdefault(r["game_id"], {})[r["question"]] = r["option_id"]
    return result


def save_prediction(user_id: int, game_id: str, question: str, option_id: str) -> bool:
    """Stores or changes a prediction. False if the game was already played (its predictions are locked)."""
    with connect() as conn:
        if conn.execute("SELECT 1 FROM game_packs WHERE user_id = ? AND game_id = ?", (user_id, game_id)).fetchone():
            return False
        conn.execute(
            "INSERT INTO predictions (user_id, game_id, question, option_id) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (user_id, game_id, question) DO UPDATE SET option_id = excluded.option_id",
            (user_id, game_id, question, option_id),
        )
        return True


def game_packs(user_id: int) -> dict[str, dict]:
    """game_id -> {correct, claimed} for the games already played on the user's timeline."""
    with connect() as conn:
        rows = conn.execute("SELECT game_id, correct, claimed FROM game_packs WHERE user_id = ?", (user_id,)).fetchall()
        return {r["game_id"]: {"correct": r["correct"], "claimed": bool(r["claimed"])} for r in rows}


def resolve_game(user_id: int, game_id: str, correct: int) -> bool:
    """Locks the game's predictions and records the packs they earned. Only the first time the game is played: True
    then, False if it already was."""
    with connect() as conn:
        return conn.execute("INSERT OR IGNORE INTO game_packs (user_id, game_id, correct) VALUES (?, ?, ?)",
                            (user_id, game_id, correct)).rowcount > 0


def claim_game_packs(user_id: int, game_id: str) -> int | None:
    """Marks the game's packs as opened and returns how many there are. None if there is nothing to open (atomic, so
    a double click can't open them twice)."""
    with connect() as conn:
        cur = conn.execute(
            "UPDATE game_packs SET claimed = 1 WHERE user_id = ? AND game_id = ? AND claimed = 0 AND correct > 0",
            (user_id, game_id),
        )
        if not cur.rowcount:
            return None
        return conn.execute("SELECT correct FROM game_packs WHERE user_id = ? AND game_id = ?",
                            (user_id, game_id)).fetchone()["correct"]


def add_watch_packs(user_id: int, game_id: str, cards: list[tuple[str, int]]):
    """cards: (card id, packs) pairs"""
    with connect() as conn:
        conn.executemany("INSERT OR IGNORE INTO watch_packs (user_id, game_id, card_id, packs) VALUES (?, ?, ?, ?)",
                         [(user_id, game_id, cid, packs) for cid, packs in cards])


def watch_packs(user_id: int) -> dict[str, dict[str, dict]]:
    """game_id -> {card id -> {"packs": how many, "claimed": if opened}}"""
    with connect() as conn:
        rows = conn.execute("SELECT game_id, card_id, packs, claimed FROM watch_packs WHERE user_id = ?",
                            (user_id,)).fetchall()
    result: dict[str, dict[str, dict]] = {}
    for r in rows:
        result.setdefault(r["game_id"], {})[r["card_id"]] = {"packs": r["packs"], "claimed": bool(r["claimed"])}
    return result


def announced_collectors(user_id: int) -> set[str]:
    with connect() as conn:
        return {r["card_id"] for r in conn.execute("SELECT card_id FROM announced_collectors WHERE user_id = ?",
                                                   (user_id,)).fetchall()}


def add_announced_collectors(user_id: int, card_ids: list[str]):
    with connect() as conn:
        conn.executemany("INSERT OR IGNORE INTO announced_collectors (user_id, card_id) VALUES (?, ?)",
                         [(user_id, cid) for cid in card_ids])


def claim_watch_packs(user_id: int, game_id: str) -> int:
    """Marks the game's Ones to Watch packs as opened and returns how many packs were waiting (atomic, like
    claim_game_packs)."""
    with connect() as conn:
        rows = conn.execute("UPDATE watch_packs SET claimed = 1 WHERE user_id = ? AND game_id = ? AND claimed = 0 "
                            "RETURNING packs", (user_id, game_id)).fetchall()
    return sum(r["packs"] for r in rows)
