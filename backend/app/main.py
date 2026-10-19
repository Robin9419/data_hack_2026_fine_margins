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
    """One random base card. It can be a duplicate: a second copy is kept and can be traded in."""
    content = get_content()
    base_ids = [cid for cid, card in content.cards.items() if card["type"] == "base"]
    drawn = random.choice(base_ids)
    new_ids = db.grant_cards(user_id, [drawn])
    return [{**content.cards[drawn], "owned": True, "is_new": drawn in new_ids}]


def with_rewards(owned: dict[str, str]) -> dict[str, str]:
    """The owned cards plus the reward cards they earn (collector and context cards)."""
    return owned | get_content().earned_cards(owned)


# Trade-in: give up TRADE_COST base cards (any mix, duplicates or not) for one random card. With a favorite team the
# roll is 50% a base card from another team, 25% a base card from the favorite team and 25% a special card; without
# one it is 75% any base card and 25% a special card.
TRADE_COST = 3


def trade_odds(favorite_team: str | None) -> list[dict]:
    special = {"id": "special", "label": "Special card", "chance": 0.25}
    if not favorite_team:
        return [{"id": "base", "label": "Base card, any team", "chance": 0.75}, special]
    return [
        {"id": "other", "label": "Base card, another team", "chance": 0.5},
        {"id": "favorite", "label": f"Base card, {favorite_team}", "chance": 0.25},
        special,
    ]


def tradeable_cards(user: dict, traded_ids: list[str]) -> list[str]:
    """Card ids a trade may give: base and special cards that exist at the user's stage of the tournament, which the
    user does not hold and is not trading in. A trade never returns a duplicate, so this is the only pool it draws
    from. Legends are only earned (see award_legends)."""
    excluded = set(db.owned_cards(user["id"])) | set(traded_ids)
    available = available_for(user)
    return [cid for cid, c in get_content().cards.items()
            if c["type"] in ("base", "special") and cid not in excluded and cid in available]


def roll_trade(user: dict, traded_ids: list[str]) -> tuple[str, dict]:
    """Rolls the trade-in outcome and grants the card. Returns (outcome id, card as a pack entry). The card is always
    one the user doesn't own. If the rolled pool has nothing left, the card comes from the next best pool (a special
    falls back to a base card, a favorite-team card to any base card), and the outcome reflects what was drawn."""
    content = get_content()
    user_id, favorite_team = user["id"], user["favorite_team"]
    odds = trade_odds(favorite_team)
    rolled = random.choices([o["id"] for o in odds], weights=[o["chance"] for o in odds])[0]
    available = set(tradeable_cards(user, traded_ids))
    base = [cid for cid in available if content.cards[cid]["type"] == "base"]
    specials = [cid for cid in available if content.cards[cid]["type"] == "special"]
    pools = {
        "special": specials,
        "base": base,
        "favorite": [cid for cid in base if content.cards[cid]["player"]["team"] == favorite_team],
        "other": [cid for cid in base if content.cards[cid]["player"]["team"] != favorite_team],
    }
    drawn = random.choice(pools[rolled] or base or specials)
    card = content.cards[drawn]
    if card["type"] == "special":
        db.grant_card(user_id, drawn, "standard")
        return "special", {**card, "owned": True, "edition": "standard", "is_new": True}
    db.grant_cards(user_id, [drawn])
    outcome = "base" if not favorite_team else ("favorite" if card["player"]["team"] == favorite_team else "other")
    return outcome, {**card, "owned": True, "is_new": True}


def award_legends(user: dict) -> list[dict]:
    """Club legends are earned, not drawn: one random legend of a club for each of 50%, 75% and 100% of the club's
    cards collected (thresholds in legends.json), so a complete club holds all its legends. The club's cards are the
    ones that exist so far in the tournament. Legends are kept if the collection later shrinks through a trade or the
    club gets new cards from its next game. Grants the legends now due and returns them as pack entries."""
    content = get_content()
    user_id, available = user["id"], available_for(user)
    owned = db.owned_cards(user_id)
    granted = []
    for team in {c["player"]["team"] for c in content.cards.values() if c["type"] == "legend"}:
        legends = [cid for cid, c in content.cards.items() if c["type"] == "legend" and c["player"]["team"] == team]
        missing = [cid for cid in legends if cid not in owned]
        due = content.legends_due(team, owned, available) - (len(legends) - len(missing))
        for cid in random.sample(missing, max(0, min(due, len(missing)))):
            db.grant_card(user_id, cid, "legend")
            granted.append({**content.cards[cid], "owned": True, "is_new": True})
    return granted


def played_for(user: dict) -> set[str]:
    """The games already played at the user's stage of the tournament timeline."""
    return get_content().tournament.played(user["stage"])


def available_for(user: dict) -> set[str]:
    """The cards that exist at the user's stage: a game's cards only once the game is played."""
    return get_content().available(played_for(user))


def owned_now(user: dict) -> dict[str, str]:
    """The user's cards (card id -> edition) that exist at their stage, plus the reward cards these earn. Going back
    in the timeline hides the cards of the games not played yet; they come back when the games are played again."""
    available = available_for(user)
    owned = {cid: e for cid, e in db.owned_cards(user["id"]).items() if cid in available}
    return {cid: e for cid, e in with_rewards(owned).items() if cid in available}


def progress_for(user: dict) -> dict:
    return get_content().progress(owned_now(user), available_for(user))


@app.post("/api/login")
def login(body: LoginRequest):
    """Dummy sign-in: any username works. Only a brand new account gets a starter pack."""
    user, created = db.get_or_create_user(body.username.strip(), body.favorite_team)
    token = db.create_session(user["id"])
    pack = open_pack(user["id"], user["favorite_team"]) + award_legends(user) if created else None
    return {"token": token, "user": user, "new_user": created, "pack": pack}


@app.get("/api/daily")
def daily_status(user: dict = Depends(current_user)):
    return {"available": not ENFORCE_DAILY_LIMIT or db.last_daily_claim(user["id"]) != _today()}


@app.post("/api/daily/claim")
def daily_claim(user: dict = Depends(current_user)):
    """One free base card per (UTC) day, unless the limit is switched off for the demo."""
    if ENFORCE_DAILY_LIMIT and not db.claim_daily(user["id"], _today()):
        raise HTTPException(409, "You already claimed today's card. Come back tomorrow!")
    return {"pack": open_daily_card(user["id"]) + award_legends(user), "progress": progress_for(user)}


class TradeRequest(BaseModel):
    # One entry per copy given up, so the same card id can appear more than once.
    card_ids: list[str] = Field(min_length=TRADE_COST, max_length=TRADE_COST)


@app.get("/api/trade")
def trade_info(user: dict = Depends(current_user)):
    return {"cost": TRADE_COST, "odds": trade_odds(user["favorite_team"])}


@app.post("/api/trade")
def trade(body: TradeRequest, user: dict = Depends(current_user)):
    """Trade in three base card copies for one random card (see trade_odds)."""
    content = get_content()
    if any(content.cards.get(cid, {}).get("type") != "base" for cid in body.card_ids):
        raise HTTPException(400, "Only base cards can be traded in")
    if not tradeable_cards(user, body.card_ids):
        raise HTTPException(409, "You already own every card, so there is nothing to trade for")
    if not db.remove_copies(user["id"], body.card_ids):
        raise HTTPException(409, "You don't have those cards to trade")
    outcome, card = roll_trade(user, body.card_ids)
    return {"outcome": outcome, "pack": [card] + award_legends(user), "progress": progress_for(user)}


@app.get("/api/teams")
def list_teams():
    """The selectable favorite teams and how many collectable cards (not legends or rewards) the set has for each."""
    cards = [c for c in get_content().cards.values() if c["type"] not in ("legend", "reward")]
    return {"teams": [{"name": t, "cards": sum(c["player"]["team"] == t for c in cards)} for t in TEAMS]}


@app.post("/api/logout")
def logout(authorization: str | None = Header(default=None)):
    db.delete_session(_token(authorization))
    return {"ok": True}


@app.get("/api/me")
def me(user: dict = Depends(current_user)):
    return {"user": user, "progress": progress_for(user)}


@app.get("/api/cards")
def list_cards(user: dict = Depends(current_user)):
    """The cards that exist at the user's stage of the tournament. Owned cards are full; locked cards only show a
    teaser. The Road to Final cards of the stars of the teams that have played are added as owned cards; they change
    with every game and never count in the progress."""
    content = get_content()
    available = available_for(user)
    owned = owned_now(user)
    copies = db.card_copies(user["id"])
    result = []
    for card_id, card in content.cards.items():
        if card_id not in available:
            continue
        if card_id in owned:
            result.append({**card, "owned": True, "edition": owned[card_id], "copies": copies.get(card_id, 1)})
        else:
            result.append({**content.card_summary(card), "owned": False})
    road = [{**card, "owned": True} for card in content.road_to_final.cards_for(played_for(user))]
    return {"cards": result + road, "progress": content.progress(owned, available)}


@app.get("/api/admin/cards")
def admin_cards(user: dict = Depends(current_user)):
    """Every card that exists after the whole tournament, owned or not, plus the Road to Final cards in their final
    stage. The demo has no roles, so any signed-in user may open this."""
    content = get_content()
    road = content.road_to_final.cards_for(content.tournament.played("post"))
    return {"cards": [{**c, "owned": True} for c in [*content.cards.values(), *road]]}


@app.get("/api/cards/{card_id}")
def get_card(card_id: str, user: dict = Depends(current_user)):
    content = get_content()
    if card_id.startswith("test-road-"):
        road = {c["id"]: c for c in content.road_to_final.cards_for(played_for(user))}
        if card_id in road:
            return {**road[card_id], "owned": True}
        raise HTTPException(404, "This player's team has not played yet")
    card = content.cards.get(card_id)
    if not card:
        raise HTTPException(404, "Card not found")
    if card_id not in available_for(user):
        raise HTTPException(404, "This card's game has not been played yet")
    owned = owned_now(user)
    if card_id not in owned:
        raise HTTPException(403, "You don't own this card yet")
    return {**card, "owned": True, "edition": owned[card_id]}


@app.get("/api/metrics")
def list_metrics():
    return {"metrics": list(get_content().metrics.values())}


@app.post("/api/reset")
def reset(user: dict = Depends(current_user)):
    """Empty the user's collection and open a fresh starter pack (for demos/testing)."""
    db.clear_cards(user["id"])  # also clears the predictions and goes back to before the tournament
    user = {**user, "stage": "pre"}
    pack = open_pack(user["id"], user["favorite_team"]) + award_legends(user)
    return {"pack": pack, "progress": progress_for(user)}


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
    """Three questions (three options each), each about one special card of a game already played that the user can
    still win. At home that is a special card they don't own; at the stadium it is also one they own only as the home
    edition. The questions start with the most recent games. Base cards are not won through trivia."""
    content = get_content()
    owned = db.owned_cards(user["id"])
    available = available_for(user)
    stadium = body.venue == "stadium"
    eligible = [
        cid
        for cid, card in content.cards.items()
        if card["type"] == "special" and cid in available and (cid not in owned or (stadium and owned[cid] != "stadium"))
    ]
    random.shuffle(eligible)
    games = content.tournament.by_id
    eligible.sort(key=lambda cid: games[content.card_game[cid]]["date"], reverse=True)
    picks = eligible[:QUESTIONS_PER_ROUND]
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
    return {"venue": body.venue, "questions": questions, "games_played": len(played_for(user))}


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
    legends = award_legends(user)
    return {"correct": True, "result": result, "card": card, "legends": legends, "progress": progress_for(user)}


class StageRequest(BaseModel):
    stage: str


class PredictionRequest(BaseModel):
    game_id: str
    question_id: str
    option_id: str


def tournament_view(user: dict) -> dict:
    """The timeline, the gameday's games with the user's predictions, and the results of the games played so far
    (most recent first) with the packs they earned."""
    t = get_content().tournament
    stage = user["stage"]
    played = t.played(stage)
    predictions = db.predictions(user["id"])
    packs = db.game_packs(user["id"])
    index = t.stages.index(stage)
    timeline = [{**stop, "state": "current" if i == index else ("past" if i < index else "future")}
                for i, stop in enumerate(t.timeline())]
    today = [t.game_view(g, False, predictions.get(g["id"], {}), packs.get(g["id"])) for g in t.today(stage)]
    results = [t.game_view(g, True, predictions.get(g["id"], {}), packs.get(g["id"]))
               for g in reversed(t.games) if g["id"] in played]
    final = t.final
    champion = None
    if final["id"] in played:
        champion = final["home_team"] if final["home_score"] > final["away_score"] else final["away_team"]
    return {
        "stage": stage, "timeline": timeline, "today": today, "results": results, "champion": champion,
        "packs_waiting": sum(r["packs"] for r in results if not r["packs_claimed"]),
    }


@app.get("/api/tournament")
def tournament(user: dict = Depends(current_user)):
    return tournament_view(user)


@app.post("/api/tournament/stage")
def set_stage(body: StageRequest, user: dict = Depends(current_user)):
    """Moves the user to a stage of the timeline. The games played by then are resolved: their predictions lock and
    each correct one earns a pack. Going back is allowed; games already resolved stay resolved."""
    t = get_content().tournament
    if body.stage not in t.stages:
        raise HTTPException(400, "Unknown stage")
    db.set_stage(user["id"], body.stage)
    user = {**user, "stage": body.stage}
    predictions = db.predictions(user["id"])
    for game_id in t.played(body.stage):
        db.resolve_game(user["id"], game_id, t.correct_count(game_id, predictions.get(game_id, {})))
    return {"tournament": tournament_view(user), "progress": progress_for(user)}


@app.post("/api/tournament/predict")
def predict(body: PredictionRequest, user: dict = Depends(current_user)):
    """Saves a prediction for a game of the current gameday. It can change until the game is played."""
    t = get_content().tournament
    game = t.by_id.get(body.game_id)
    if not game or game["date"] != user["stage"]:
        raise HTTPException(409, "Predictions are only open for today's games")
    question = next((q for q in t.questions[game["id"]] if q["id"] == body.question_id), None)
    if not question or body.option_id not in {o["id"] for o in question["options"]}:
        raise HTTPException(400, "Not one of the options")
    if not db.save_prediction(user["id"], game["id"], question["id"], body.option_id):
        raise HTTPException(409, "This game has already been played")
    return tournament_view(user)


@app.post("/api/tournament/packs/{game_id}")
def open_game_packs(game_id: str, user: dict = Depends(current_user)):
    """Opens the packs a played game earned (one per correct prediction, see Tournament.pack_cards)."""
    content = get_content()
    t = content.tournament
    if game_id not in played_for(user):
        raise HTTPException(409, "This game has not been played yet")
    packs = db.claim_game_packs(user["id"], game_id)
    if not packs:
        raise HTTPException(409, "No packs to open for this game")
    game = t.by_id[game_id]
    teams = (game["home_team"], game["away_team"])
    base_ids = [cid for cid, c in content.cards.items() if c["type"] == "base" and c["player"]["team"] in teams]
    owned = db.owned_cards(user["id"])
    game_ids = [cid for cid in content.game_cards(game_id) if cid not in owned]
    pack = []
    for cid in t.pack_cards(packs, base_ids, game_ids, random):
        card = content.cards[cid]
        if card["type"] == "special":
            db.grant_card(user["id"], cid, "standard")
            pack.append({**card, "owned": True, "edition": "standard", "is_new": True})
        else:
            pack.append({**card, "owned": True, "is_new": bool(db.grant_cards(user["id"], [cid]))})
    return {"pack": pack + award_legends(user), "progress": progress_for(user),
            "title": f'{packs} {"pack" if packs == 1 else "packs"} from {game["home_team"]} – {game["away_team"]}'}


@app.get('/api/analysis/pass-body-pressure')
def pass_pressure_analysis(user: dict = Depends(current_user)):
    """Event results, exclusions, coverage and aggregates for every passer."""
    return get_content().derived_kpis['pass_body_pressure']


@app.get('/api/analysis/pass-packing')
def packing_analysis(user: dict = Depends(current_user)):
    return get_content().derived_kpis['pass_packing']


@app.get('/api/analysis/expected-assists')
def xa_analysis(user: dict = Depends(current_user)):
    return get_content().derived_kpis['expected_assists']
