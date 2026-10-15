"""Hockey Performance Cards API.

Run from the backend folder:  uvicorn app.main:app --reload
"""

import os
import random
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Literal

from pydantic import BaseModel, Field

from . import db
from .content import MEDIA_DIR, get_content

app = FastAPI(title="Hockey Performance Cards")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
# Clips cut from the match recording (scripts/cut_clips.py). Supports range requests, so videos can seek.
app.mount("/api/media", StaticFiles(directory=MEDIA_DIR, check_dir=False), name="media")


@app.on_event("startup")
def startup():
    db.init_db()
    get_content()  # fail fast if the content or CSV is broken


def _token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not signed in")
    return authorization.removeprefix("Bearer ")


def current_user(authorization: str | None = Header(default=None)) -> dict:
    user = db.user_for_token(_token(authorization))
    if not user:
        raise HTTPException(401, "Session expired")
    return user


TEAMS = [
    "HIFK",
    "Team Canada",
    "HC Davos",
    "HC Sparta Praha",
    "HC Fribourg-Gottéron",
    "U.S. Collegiate Selects",
]


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=40)
    favorite_team: Literal[tuple(TEAMS)] | None = None


def open_pack(user_id: int, favorite_team: str | None = None) -> list[dict]:
    """Draws distinct random base cards, adds them to the collection and returns them in full. If the user has a
    favorite team with base cards in the set, one of the cards is guaranteed to be from that team."""
    content = get_content()
    base_ids = [cid for cid, card in content.cards.items() if card["type"] == "base"]
    size = min(content.pack_size, len(base_ids))
    favorites = [cid for cid in base_ids if content.cards[cid]["player"]["team"] == favorite_team]
    drawn = [random.choice(favorites)] if favorites else []
    rest = [cid for cid in base_ids if cid not in drawn]
    drawn += random.sample(rest, size - len(drawn))
    random.shuffle(drawn)
    new_ids = db.grant_cards(user_id, drawn)
    return [{**content.cards[cid], "owned": True, "is_new": cid in new_ids} for cid in drawn]


# The product rule is one daily card per day. It is off by default so the demo can claim as often as it likes;
# start the server with ENFORCE_DAILY_LIMIT=1 to turn the rule on.
ENFORCE_DAILY_LIMIT = os.environ.get("ENFORCE_DAILY_LIMIT") == "1"


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def open_daily_card(user_id: int) -> list[dict]:
    """One base card, preferring one the user doesn't own yet (a duplicate only once they own all of them)."""
    content = get_content()
    base_ids = [cid for cid, card in content.cards.items() if card["type"] == "base"]
    owned = db.owned_cards(user_id)
    candidates = [cid for cid in base_ids if cid not in owned] or base_ids
    drawn = random.choice(candidates)
    new_ids = db.grant_cards(user_id, [drawn])
    return [{**content.cards[drawn], "owned": True, "is_new": drawn in new_ids}]


def progress_for(user_id: int) -> dict:
    return get_content().progress(db.owned_cards(user_id))


@app.post("/api/login")
def login(body: LoginRequest):
    """Dummy sign-in: any username works. Only a brand new account gets a starter pack."""
    user, created = db.get_or_create_user(body.username.strip(), body.favorite_team)
    token = db.create_session(user["id"])
    pack = open_pack(user["id"], user["favorite_team"]) if created else None
    return {"token": token, "user": user, "new_user": created, "pack": pack}


@app.get("/api/daily")
def daily_status(user: dict = Depends(current_user)):
    return {"available": not ENFORCE_DAILY_LIMIT or db.last_daily_claim(user["id"]) != _today()}


@app.post("/api/daily/claim")
def daily_claim(user: dict = Depends(current_user)):
    """One free base card per (UTC) day, unless the limit is switched off for the demo."""
    if ENFORCE_DAILY_LIMIT and not db.claim_daily(user["id"], _today()):
        raise HTTPException(409, "You already claimed today's card. Come back tomorrow!")
    return {"pack": open_daily_card(user["id"]), "progress": progress_for(user["id"])}


@app.get("/api/teams")
def list_teams():
    """The selectable favorite teams and how many cards the set has for each."""
    cards = get_content().cards.values()
    return {"teams": [{"name": t, "cards": sum(c["player"]["team"] == t for c in cards)} for t in TEAMS]}


@app.post("/api/logout")
def logout(authorization: str | None = Header(default=None)):
    db.delete_session(_token(authorization))
    return {"ok": True}


@app.get("/api/me")
def me(user: dict = Depends(current_user)):
    return {"user": user, "progress": progress_for(user["id"])}


@app.get("/api/cards")
def list_cards(user: dict = Depends(current_user)):
    """All cards in the set. Owned cards are full; locked cards only show a teaser."""
    content = get_content()
    owned = db.owned_cards(user["id"])
    result = []
    for card_id, card in content.cards.items():
        if card_id in owned:
            result.append({**card, "owned": True, "edition": owned[card_id]})
        else:
            result.append({**content.card_summary(card), "owned": False})
    return {"cards": result, "progress": content.progress(owned)}


@app.get("/api/cards/{card_id}")
def get_card(card_id: str, user: dict = Depends(current_user)):
    content = get_content()
    card = content.cards.get(card_id)
    if not card:
        raise HTTPException(404, "Card not found")
    owned = db.owned_cards(user["id"])
    if card_id not in owned:
        raise HTTPException(403, "You don't own this card yet")
    return {**card, "owned": True, "edition": owned[card_id]}


@app.get("/api/metrics")
def list_metrics():
    return {"metrics": list(get_content().metrics.values())}


@app.post("/api/reset")
def reset(user: dict = Depends(current_user)):
    """Empty the user's collection and open a fresh starter pack (for demos/testing)."""
    db.clear_cards(user["id"])
    return {"pack": open_pack(user["id"], user["favorite_team"]), "progress": progress_for(user["id"])}


QUESTIONS_PER_ROUND = 3


class QuizStart(BaseModel):
    # Self-reported in this demo. A real product would verify it (ticket scan, geofence, in-arena Wi-Fi).
    venue: Literal["home", "stadium"]


class QuizAnswer(BaseModel):
    option_id: str


def _edition(venue: str) -> str:
    return "stadium" if venue == "stadium" else "standard"


@app.post("/api/quiz/start")
def quiz_start(body: QuizStart, user: dict = Depends(current_user)):
    """Three questions (three options each), each about one special card the user can still win. At home that is a
    special card they don't own; at the stadium it is also one they own only as the home edition. Base cards are
    not won through trivia."""
    content = get_content()
    owned = db.owned_cards(user["id"])
    stadium = body.venue == "stadium"
    eligible = [
        cid
        for cid, card in content.cards.items()
        if card["type"] == "special" and (cid not in owned or (stadium and owned[cid] != "stadium"))
    ]
    picks = random.sample(eligible, min(QUESTIONS_PER_ROUND, len(eligible)))
    built = [(cid, content.build_question(cid, random)) for cid in picks]
    ids = db.create_quiz(user["id"], body.venue, [(cid, q["option_ids"]) for cid, q in built])

    def option(card_id: str) -> dict:
        player = content.cards[card_id]["player"]
        return {"id": card_id, "name": f'{player["first_name"]} {player["last_name"]}', "team": player["team"]}

    questions = [
        {
            "id": qid,
            "prompt": q["prompt"],
            "clue": q["clue"],
            "match": q["match"],
            "reward": "upgrade" if cid in owned else "new",
            "options": [option(oid) for oid in q["option_ids"]],
        }
        for qid, (cid, q) in zip(ids, built)
    ]
    return {"venue": body.venue, "questions": questions}


@app.post("/api/quiz/{question_id}/answer")
def quiz_answer(question_id: int, body: QuizAnswer, user: dict = Depends(current_user)):
    """One attempt per question. A right answer unlocks the card in the quiz's edition."""
    question = db.get_question(user["id"], question_id)
    if not question:
        raise HTTPException(404, "Question not found")
    if question["answered"]:
        raise HTTPException(409, "Already answered")
    if body.option_id not in question["option_ids"]:
        raise HTTPException(400, "Not one of the options")
    db.mark_answered(question_id)
    if body.option_id != question["card_id"]:
        content = get_content()
        player = content.cards[question["card_id"]]["player"]
        return {"correct": False, "answer": f'{player["first_name"]} {player["last_name"]}'}

    edition = _edition(question["venue"])
    result = db.grant_card(user["id"], question["card_id"], edition)
    card = {**get_content().cards[question["card_id"]], "owned": True, "edition": edition}
    return {"correct": True, "result": result, "card": card, "progress": progress_for(user["id"])}


@app.get('/api/analysis/pass-body-pressure')
def pass_pressure_analysis(user: dict = Depends(current_user)):
    """Event results, exclusions, coverage and aggregates for every passer."""
    return get_content().derived_kpis['pass_body_pressure']
