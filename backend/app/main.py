"""Hockey Performance Cards API.

Run from the backend folder:  uvicorn app.main:app --reload
"""

import random

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Literal

from pydantic import BaseModel, Field

from . import db
from .content import MEDIA_DIR, get_content
from .tournament import OUTLOOK, PACK_CARDS, SPECIAL_CHANCE

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


def road_cards_for(user: dict) -> dict[str, dict]:
    """The Road to Final cards a pack can give: one per star whose team has played at the user's stage, by card id."""
    return {c["id"]: c for c in get_content().road_to_final.cards_for(played_for(user))}


def trivia_reserved(user: dict) -> set[str]:
    """The special cards the gameday's trivia is about: those of the latest games played at the user's stage. They are
    for the trivia to give, so packs leave them out until the user has played the trivia of this stage."""
    content = get_content()
    played = played_for(user)
    if not played or db.trivia_played(user["id"], user["stage"]):
        return set()
    games = content.tournament.by_id
    latest = max(games[gid]["date"] for gid in played)
    return {cid for gid in played if games[gid]["date"] == latest for cid in content.game_cards(gid)}


def special_pool(user: dict, roads: dict[str, dict]) -> list[str]:
    """The special cards a base-only pack can give: the Road to Final cards (Ones to Watch) and the special cards of
    played games (impact players) the user does not own yet, except those the gameday's trivia is about."""
    owned = db.owned_cards(user["id"])
    available, reserved = available_for(user), trivia_reserved(user)
    specials = [cid for cid, c in get_content().cards.items()
                if c["type"] == "special" and cid in available and cid not in owned and cid not in reserved]
    return specials + [cid for cid in roads if cid not in owned]


def with_special_card(user: dict, roads: dict[str, dict], drawn: list[str]) -> list[str]:
    """Base-only packs: SPECIAL_CHANCE that the last card is a special card from special_pool."""
    pool = special_pool(user, roads)
    if pool and random.random() < SPECIAL_CHANCE:
        drawn[-1] = random.choice(pool)
    return drawn


def pack_entries(user: dict, drawn: list[str], roads: dict[str, dict]) -> list[dict]:
    """Grants the drawn cards and returns them in full. Special cards come in the standard edition. A repeat within
    the pack is not new."""
    content, user_id = get_content(), user["id"]
    entries = []
    for cid in drawn:
        if cid in roads:
            entries.append({**roads[cid], "owned": True, "is_new": bool(db.grant_cards(user_id, [cid]))})
        elif content.cards[cid]["type"] == "special":
            db.grant_card(user_id, cid, "standard")
            entries.append({**content.cards[cid], "owned": True, "edition": "standard", "is_new": True})
        else:
            entries.append({**content.cards[cid], "owned": True, "is_new": bool(db.grant_cards(user_id, [cid]))})
    return entries


def open_pack(user: dict) -> list[dict]:
    """Draws distinct random base cards, adds them to the collection and returns them in full. If the user has a
    favorite team with base cards in the set, one of the cards is guaranteed to be from that team."""
    content = get_content()
    base_ids = [cid for cid, card in content.cards.items() if card["type"] == "base"]
    size = min(content.pack_size, len(base_ids))
    favorites = [cid for cid in base_ids if content.cards[cid]["player"]["team"] == user["favorite_team"]]
    drawn = [random.choice(favorites)] if favorites else []
    rest = [cid for cid in base_ids if cid not in drawn]
    drawn += random.sample(rest, size - len(drawn))
    roads = road_cards_for(user)
    drawn = with_special_card(user, roads, drawn)
    random.shuffle(drawn)
    return pack_entries(user, drawn, roads)


DAILY_CARDS = 5


def open_daily_card(user: dict) -> list[dict]:
    """Random base cards. They can be duplicates: a second copy is kept and can be traded in."""
    return open_random_base_cards(user, DAILY_CARDS)


def open_random_base_cards(user: dict, count: int, packs: int = 1) -> list[dict]:
    """Random base cards, one draw each, so duplicates are possible. Each of the packs holds count cards and has its
    own SPECIAL_CHANCE roll for the last card to be a special card."""
    content = get_content()
    base_ids = [cid for cid, card in content.cards.items() if card["type"] == "base"]
    roads = road_cards_for(user)
    entries = []
    for _ in range(packs):
        drawn = with_special_card(user, roads, [random.choice(base_ids) for _ in range(count)])
        entries += pack_entries(user, drawn, roads)
    return entries


# Free cards: following a Spengler Cup social channel and buying match tickets (per ticket). Every stage of the
# timeline promotes another channel, and each one pays out once. Neither is verified against the platform or a ticket
# shop yet, so for the demo the claim is taken on trust.
SOCIALS = [("instagram", "Instagram"), ("facebook", "Facebook"), ("tiktok", "TikTok"), ("youtube", "YouTube"),
           ("x", "X"), ("threads", "Threads"), ("whatsapp", "WhatsApp"), ("linkedin", "LinkedIn")]
SOCIAL_CARDS = 5
CARDS_PER_TICKET = 5  # cards in one pack
PACKS_PER_TICKET = 2


class TicketBonusRequest(BaseModel):
    tickets: int = Field(ge=1)


def social_for(stage: str) -> tuple[str, str]:
    """(id, name) of the channel the stage promotes."""
    return SOCIALS[get_content().tournament.stages.index(stage) % len(SOCIALS)]


@app.post("/api/bonus/social")
def bonus_social(user: dict = Depends(current_user)):
    platform, name = social_for(user["stage"])
    if not db.follow_social(user["id"], platform):
        raise HTTPException(409, f"You already follow Spengler Cup on {name}")
    pack = open_random_base_cards(user, SOCIAL_CARDS)
    return {"pack": pack + award_earned(user), "progress": progress_for(user), "title": f"Thanks for following on {name}!"}


@app.post("/api/bonus/tickets")
def bonus_tickets(body: TicketBonusRequest, user: dict = Depends(current_user)):
    pack = open_random_base_cards(user, CARDS_PER_TICKET, body.tickets * PACKS_PER_TICKET)
    packs = body.tickets * PACKS_PER_TICKET
    title = f'{body.tickets} {"ticket" if body.tickets == 1 else "tickets"}, {packs} free packs'
    return {"pack": pack + award_earned(user), "progress": progress_for(user), "title": title}


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
    from. Road to Final cards the user does not own count as special cards. Legends are only earned (see
    award_legends)."""
    excluded = set(db.owned_cards(user["id"])) | set(traded_ids)
    available = available_for(user)
    cards = [cid for cid, c in get_content().cards.items()
             if c["type"] in ("base", "special") and cid not in excluded and cid in available]
    return cards + [cid for cid in road_cards_for(user) if cid not in excluded]


def roll_trade(user: dict, traded_ids: list[str], teams: tuple[str, ...] | None = None) -> tuple[str, dict]:
    """Rolls the trade-in outcome and grants the card. Returns (outcome id, card as a pack entry). The card is always
    one the user doesn't own. If the rolled pool has nothing left, the card comes from the next best pool (a special
    falls back to a base card, a favorite-team card to any base card), and the outcome reflects what was drawn. With
    teams, the base cards are limited to those clubs (prediction packs); the caller makes sure something is left."""
    content = get_content()
    user_id, favorite_team = user["id"], user["favorite_team"]
    odds = trade_odds(favorite_team)
    rolled = random.choices([o["id"] for o in odds], weights=[o["chance"] for o in odds])[0]
    available = set(tradeable_cards(user, traded_ids))
    roads = road_cards_for(user)
    base = [cid for cid in available if cid not in roads and content.cards[cid]["type"] == "base"
            and (teams is None or content.cards[cid]["player"]["team"] in teams)]
    specials = [cid for cid in available if cid in roads or content.cards[cid]["type"] == "special"]
    pools = {
        "special": specials,
        "base": base,
        "favorite": [cid for cid in base if content.cards[cid]["player"]["team"] == favorite_team],
        "other": [cid for cid in base if content.cards[cid]["player"]["team"] != favorite_team],
    }
    drawn = random.choice(pools[rolled] or base or specials or sorted(available))
    if drawn in roads:
        db.grant_cards(user_id, [drawn])
        return "special", {**roads[drawn], "owned": True, "is_new": True}
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


def award_collectors(user: dict) -> list[dict]:
    """Reward cards (a club's collector card, the final goal, the stadium and the trophy) are earned by what the user
    owns (see content._add_reward_cards). Returns the ones the user has not been shown the unlock of yet, and marks
    them as shown."""
    content = get_content()
    announced = db.announced_collectors(user["id"])
    now = owned_now(user)
    new = [cid for cid, c in content.cards.items()
           if c["type"] == "reward" and cid in now and cid not in announced]
    db.add_announced_collectors(user["id"], new)
    return [{**content.cards[cid], "owned": True, "is_new": True} for cid in new]


def award_earned(user: dict) -> list[dict]:
    """The earned cards (legends, then collectors) a pack response adds after its drawn cards."""
    return award_legends(user) + award_collectors(user)


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
    pack = open_pack(user) + award_earned(user) if created else None
    return {"token": token, "user": user, "new_user": created, "pack": pack}


@app.post("/api/daily/claim")
def daily_claim(user: dict = Depends(current_user)):
    """Three free base cards per day, where a day is a stage of the simulated tournament timeline."""
    if not db.claim_daily(user["id"], user["stage"]):
        raise HTTPException(409, "You already claimed today's card. Come back tomorrow!")
    return {"pack": open_daily_card(user) + award_earned(user), "progress": progress_for(user),
            "title": "Your daily pack"}


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
    return {"outcome": outcome, "pack": [card] + award_earned(user), "progress": progress_for(user)}


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
    teaser. The Road to Final cards are collected from packs like any card, so the ones not owned yet show a teaser
    too. They only exist once their team has played, change with every game and never count in the progress."""
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
    road = [{**card, "owned": True} if card["id"] in copies else {**content.card_summary(card), "owned": False}
            for card in content.road_to_final.cards_for(played_for(user))]
    return {"cards": result + road, "progress": content.progress(owned, available)}


@app.get("/api/admin/cards")
def admin_cards(user: dict = Depends(current_user)):
    """Every card that exists after the whole tournament, owned or not, plus the Road to Final cards in their final
    stage. The demo has no roles, so any signed-in user may open this."""
    content = get_content()
    road = content.road_to_final.cards_for(content.tournament.played("post"))
    return {"cards": [{**c, "owned": True} for c in [*content.cards.values(), *road]]}


@app.get("/api/cards/{card_id}/player-cards")
def player_cards(card_id: str, user: dict = Depends(current_user)):
    """Every card of the same player that exists at the user's stage: the ones owned in full, the locked ones as a
    teaser (names are blanked, so the match has to be made here)."""
    content = get_content()
    card = content.cards.get(card_id)
    if not card or not card.get("player"):
        return {"cards": []}
    player = card["player"]
    who = (player.get("first_name"), player.get("last_name"), player.get("team"))
    available = available_for(user)
    owned = owned_now(user)
    copies = db.card_copies(user["id"])
    result = []
    for other_id, other in content.cards.items():
        p = other.get("player")
        if other["type"] == "reward" or not p or other_id not in available:
            continue
        if (p.get("first_name"), p.get("last_name"), p.get("team")) != who:
            continue
        if other_id in owned:
            result.append({**other, "owned": True, "edition": owned[other_id], "copies": copies.get(other_id, 1)})
        else:
            result.append({**content.card_summary(other), "owned": False})
    return {"cards": result}


@app.get("/api/cards/{card_id}")
def get_card(card_id: str, user: dict = Depends(current_user)):
    content = get_content()
    if card_id.startswith("test-road-"):
        road = road_cards_for(user)
        if card_id not in road:
            raise HTTPException(404, "This player's team has not played yet")
        if card_id not in db.owned_cards(user["id"]):
            raise HTTPException(403, "You don't own this card yet")
        return {**road[card_id], "owned": True}
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
    pack = open_pack(user) + award_earned(user)
    return {"pack": pack, "progress": progress_for(user)}


QUESTIONS_PER_ROUND = 3


class QuizStart(BaseModel):
    # Self-reported in this demo. A real product would verify it (ticket scan, geofence, in-arena Wi-Fi).
    venue: Literal["home", "stadium"]


class QuizAnswer(BaseModel):
    option_id: str


def _edition(venue: str) -> str:
    return "stadium" if venue == "stadium" else "standard"


def trivia_cards(user: dict, venue: str) -> list[str]:
    """The special cards the trivia can still give: of games already played and not owned yet (at the stadium, also
    the ones owned only as the home edition)."""
    owned = db.owned_cards(user["id"])
    available = available_for(user)
    return [cid for cid, card in get_content().cards.items()
            if card["type"] == "special" and cid in available
            and (cid not in owned or (venue == "stadium" and owned[cid] != "stadium"))]


@app.post("/api/quiz/start")
def quiz_start(body: QuizStart, user: dict = Depends(current_user)):
    """Three questions (three options each), each about one special card of a game already played that the user can
    still win. At home that is a special card they don't own; at the stadium it is also one they own only as the home
    edition. The questions start with the most recent games. Base cards are not won through trivia."""
    content = get_content()
    owned = db.owned_cards(user["id"])
    eligible = trivia_cards(user, body.venue)
    random.shuffle(eligible)
    games = content.tournament.by_id
    eligible.sort(key=lambda cid: games[content.card_game[cid]]["date"], reverse=True)
    picks = eligible[:QUESTIONS_PER_ROUND]
    built = [(cid, content.build_question(cid, random)) for cid in picks]
    ids = db.create_quiz(user["id"], body.venue, [(cid, q["option_ids"]) for cid, q in built])
    if built:
        db.mark_trivia_played(user["id"], user["stage"])  # the gameday's round is used up, see activities

    def option(card_id: str) -> dict:
        player = content.cards[card_id]["player"]
        return {"id": card_id, "name": f'{player["first_name"]} {player["last_name"]}', "team": player["team"]}

    questions = [
        {
            "id": qid,
            "prompt": q["prompt"],
            "hint": q["hint"],
            "eliminate": q["eliminate"],
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
        return {"correct": False, "answer_id": question["card_id"], "answer": f'{player["first_name"]} {player["last_name"]}',
                "explanation": content.explain_answer(question["card_id"])}

    edition = _edition(question["venue"])
    result = db.grant_card(user["id"], question["card_id"], edition)
    card = {**get_content().cards[question["card_id"]], "owned": True, "edition": edition}
    legends = award_legends(user)
    collectors = award_collectors(user)
    return {"correct": True, "result": result, "card": card, "legends": legends, "collectors": collectors,
            "progress": progress_for(user)}


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
    resolved = t.resolved(stage)
    predictions = db.predictions(user["id"])
    packs = db.game_packs(user["id"])
    index = t.stages.index(stage)
    timeline = [{**stop, "state": "current" if i == index else ("past" if i < index else "future")}
                for i, stop in enumerate(t.timeline())]
    watch = db.watch_packs(user["id"])
    today = [t.game_view(g, False, predictions.get(g["id"], {}), packs.get(g["id"])) for g in t.rounds(stage)]
    # Most recent first: the tournament predictions, once resolved, come before the final.
    results = [{**t.game_view(g, True, predictions.get(g["id"], {}), packs.get(g["id"])),
                "watch_packs": watch_packs_of(g["id"], watch)}
               for g in [t.outlook, *reversed(t.games)] if g["id"] in resolved]
    final = t.final
    champion = None
    if final["id"] in played:
        champion = final["home_team"] if final["home_score"] > final["away_score"] else final["away_team"]
    return {
        "stage": stage, "timeline": timeline, "today": today, "results": results, "champion": champion,
        "packs_waiting": sum(r["packs"] for r in results if not r["packs_claimed"])
                         + sum(w["packs"] for r in results for w in r["watch_packs"] if not w["claimed"]),
    }


# Ones to Watch packs: owning a Road to Final card pays out a pack for each goal or assist its player has in a game.
# The packs are drawn like the base-only packs (see open_random_base_cards).
WATCH_PACK_CARDS = 5


def watch_packs_of(game_id: str, watch: dict[str, dict[str, dict]]) -> list[dict]:
    """The Ones to Watch packs a played game earned (see db.watch_packs): the player, his points, how many packs and if
    they are opened."""
    earned = watch.get(game_id, {})
    return [{**p, **earned[p["card_id"]]}
            for p in get_content().road_to_final.pointed(game_id) if p["card_id"] in earned]


def record_watch_packs(user: dict, game_ids: set[str]):
    """When games are played: a pack for each goal or assist of an owned Road to Final card's player."""
    owned = db.owned_cards(user["id"])
    road = get_content().road_to_final
    for game_id in game_ids:
        db.add_watch_packs(user["id"], game_id,
                           [(p["card_id"], p["goals"] + p["assists"]) for p in road.pointed(game_id)
                            if p["card_id"] in owned])


def open_watch_packs(user: dict, packs: int) -> list[dict]:
    return [card for _ in range(packs) for card in open_random_base_cards(user, WATCH_PACK_CARDS)]


@app.get("/api/tournament")
def tournament(user: dict = Depends(current_user)):
    return tournament_view(user)


@app.post("/api/tournament/stage")
def set_stage(body: StageRequest, user: dict = Depends(current_user)):
    """Moves the user to a stage of the timeline. The games played by then are resolved: their predictions lock and
    each correct one earns a pack. Going back is allowed; games already resolved stay resolved. just_played lists the
    games this move resolved, in order of play, for the results pop-up."""
    t = get_content().tournament
    if body.stage not in t.stages:
        raise HTTPException(400, "Unknown stage")
    db.set_stage(user["id"], body.stage)
    user = {**user, "stage": body.stage}
    predictions = db.predictions(user["id"])
    resolved = {game_id for game_id in t.resolved(body.stage)
                if db.resolve_game(user["id"], game_id, t.correct_count(game_id, predictions.get(game_id, {})))}
    record_watch_packs(user, resolved - {OUTLOOK})
    packs, watch = db.game_packs(user["id"]), db.watch_packs(user["id"])
    just_played = [{**t.game_view(g, True, predictions.get(g["id"], {}), packs.get(g["id"])),
                    "watch_packs": watch_packs_of(g["id"], watch)}
                   for g in [*t.games, t.outlook] if g["id"] in resolved]
    return {"tournament": tournament_view(user), "progress": progress_for(user), "just_played": just_played}


@app.post("/api/tournament/predict")
def predict(body: PredictionRequest, user: dict = Depends(current_user)):
    """Saves a prediction for a game of the current gameday, or a tournament prediction before the tournament. It can
    change until the game is played (the tournament predictions: until the first gameday)."""
    t = get_content().tournament
    game = t.round_by_id(body.game_id)
    if not game or game["id"] not in {g["id"] for g in t.rounds(user["stage"])}:
        raise HTTPException(409, "Predictions are only open for today's games"
                            if body.game_id != OUTLOOK else "Tournament predictions close when the tournament starts")
    question = next((q for q in t.questions[game["id"]] if q["id"] == body.question_id), None)
    if not question or body.option_id not in {o["id"] for o in question["options"]}:
        raise HTTPException(400, "Not one of the options")
    if not db.save_prediction(user["id"], game["id"], question["id"], body.option_id):
        raise HTTPException(409, "This game has already been played")
    return tournament_view(user)


def open_packs_of(user: dict, game_id: str, packs: int) -> list[dict]:
    """Draws and grants the packs a game earned, one per correct prediction: PACK_CARDS cards, each rolled like a
    trade-in (see trade_odds), with the base cards limited to the two teams that played (any team for the tournament
    predictions)."""
    content = get_content()
    game = content.tournament.round_by_id(game_id)
    teams = (game["home_team"], game["away_team"]) if game_id != OUTLOOK else None
    base_ids = [cid for cid, c in content.cards.items()
                if c["type"] == "base" and (teams is None or c["player"]["team"] in teams)]
    pack = []
    for _ in range(packs * PACK_CARDS):
        if tradeable_cards(user, []):
            pack.append(roll_trade(user, [], teams)[1])
        else:  # the user owns every card, so the card is a base card copy
            pack += pack_entries(user, [random.choice(base_ids)], {})
    return pack


@app.post("/api/tournament/packs/{game_id}")
def open_game_packs(game_id: str, user: dict = Depends(current_user)):
    """Opens the packs a played game earned: the prediction packs and the Ones to Watch packs."""
    t = get_content().tournament
    if game_id not in t.resolved(user["stage"]):
        raise HTTPException(409, "This game has not been played yet")
    packs = db.claim_game_packs(user["id"], game_id) or 0
    watch = db.claim_watch_packs(user["id"], game_id)
    if not packs and not watch:
        raise HTTPException(409, "No packs to open for this game")
    game = t.round_by_id(game_id)
    pack = (open_packs_of(user, game_id, packs) if packs else []) + open_watch_packs(user, watch)
    total = packs + watch
    source = "your tournament predictions" if game_id == OUTLOOK else f'{game["home_team"]} – {game["away_team"]}'
    return {"pack": pack + award_earned(user), "progress": progress_for(user),
            "title": f'{total} {"pack" if total == 1 else "packs"} from {source}'}


@app.post("/api/tournament/packs")
def open_all_packs(user: dict = Depends(current_user)):
    """Opens, in one go, every pack the played games earned that the user has not opened yet: the prediction packs
    and the Ones to Watch packs."""
    played = played_for(user)
    resolved = get_content().tournament.resolved(user["stage"])
    pack, total = [], 0
    for game_id, info in db.game_packs(user["id"]).items():
        if game_id in resolved and info["correct"] and not info["claimed"]:
            packs = db.claim_game_packs(user["id"], game_id)
            if packs:
                pack += open_packs_of(user, game_id, packs)
                total += packs
    watch_total = 0
    for game_id in db.watch_packs(user["id"]):
        if game_id in played:
            watch_total += db.claim_watch_packs(user["id"], game_id)
    pack += open_watch_packs(user, watch_total)
    if not total and not watch_total:
        raise HTTPException(409, "No packs to open")
    kind = "prediction " if not watch_total else "Ones to Watch " if not total else ""
    count = total + watch_total
    return {"pack": pack + award_earned(user), "progress": progress_for(user),
            "title": f'Your {count} {kind}{"pack" if count == 1 else "packs"}'}


@app.get("/api/activities")
def activities(user: dict = Depends(current_user)):
    """What the user can do right now at their stage of the timeline. Done activities drop out (null or 0): the
    stage's daily card once claimed, its social channel once followed, the predictions once every question of today's
    games has a pick, the packs once opened and the trivia once played on this gameday. Trade and tickets stay."""
    content = get_content()
    t = content.tournament
    stage = user["stage"]
    predictions = db.predictions(user["id"])
    packs = db.game_packs(user["id"])
    resolved = t.resolved(stage)
    open_games = [g for g in t.rounds(stage) if g["id"] not in packs]
    picks = sum(len(predictions.get(g["id"], {})) for g in open_games)
    questions = sum(len(t.questions[g["id"]]) for g in open_games)
    platform, name = social_for(stage)
    available = available_for(user)
    base_copies = sum(n for cid, n in db.card_copies(user["id"]).items()
                      if cid in available and content.cards.get(cid, {}).get("type") == "base")
    return {
        "daily": db.last_daily_claim(user["id"]) != stage,
        "social": None if platform in db.followed_socials(user["id"])
                  else {"id": platform, "name": name, "cards": SOCIAL_CARDS},
        "predictions": {"games": sum(g["id"] != OUTLOOK for g in open_games), "picks": picks, "questions": questions,
                        "tournament": any(g["id"] == OUTLOOK for g in open_games)} if picks < questions else None,
        "packs_waiting": sum(p["correct"] for gid, p in packs.items() if gid in resolved and not p["claimed"])
                         + sum(c["packs"] for gid, cards in db.watch_packs(user["id"]).items() if gid in resolved
                               for c in cards.values() if not c["claimed"]),
        "trivia": 0 if db.trivia_played(user["id"], stage) else len(trivia_cards(user, "home")),
        "trade": {"cost": TRADE_COST, "base_copies": base_copies},
        "tickets": {"cards_per_ticket": CARDS_PER_TICKET, "packs_per_ticket": PACKS_PER_TICKET},
    }


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


@app.get('/api/analysis/blc-xg')
def blc_xg_analysis(user: dict = Depends(current_user)):
    return get_content().derived_kpis['blc_xg']


@app.get('/api/analysis/controlled-zone-exits')
def zone_exit_analysis(user: dict = Depends(current_user)):
    return get_content().derived_kpis['controlled_zone_exits']


@app.get('/api/award-categories')
def award_categories(user: dict = Depends(current_user)):
    return {'categories': get_content().award_categories, 'selection_policy': 'independent_awards'}


@app.get('/api/analysis/interceptions')
def interception_analysis(user: dict = Depends(current_user)):
    return get_content().derived_kpis['interceptions']
