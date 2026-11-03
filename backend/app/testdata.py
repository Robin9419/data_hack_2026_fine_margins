"""Test data: extra cards for the other games of the 2025 Spengler Cup.

Only the final has Wisehockey data. The other ten games come from the official game pages (see
scripts/fetch_testdata.py) and give goals, assists, penalties, time on ice, shots, hardest shot and goalkeeper saves.
From these the module builds the performance specials (Player of the Match, Game Winner, Brick Wall, Record Breaker)
per game. They join the card set once their game is played on the user's tournament timeline (see tournament.py).
Match ratings are made up from a simple formula, so every card is flagged `test`."""

import json
import random
import re
from pathlib import Path

from .ratings import tier_of

TESTDATA_FILE = Path(__file__).resolve().parents[1] / "content" / "testdata.json"
HIGHLIGHTS_FILE = Path(__file__).resolve().parents[1] / "content" / "game_highlights.json"  # official video per game
SOURCE = "Official game statistics, spenglercup.ch (test data)"
# The official statistics have no expected goals, so Brick Wall counts all saves here.
TEST_RULES = {"wall": "The goalkeeper who made the most saves in the game, even if his team lost."}
# metric id -> key in the player's official stats
STAT_OF = {
    "goals": "goals", "assists": "assists", "points": "points", "shots": "shots", "toi": "toi",
    "shot_top_speed": "shot_top_speed", "saves": "saves", "save_pct": "save_pct",
    "shots_on_goal_against": "shots_against",
}
MOMENT_KINDS = {"goals": ("goal",), "assists": ("assist",), "points": ("goal", "assist")}
ORDINALS = {1: "1st", 2: "2nd", 3: "3rd"}
# The only Game Winner and Brick Wall cards kept from the games without data (first and last name).
KEPT_SPECIALS = {("Niko", "Hovinen"), ("Alex", "Tracy"), ("Mason", "Shaw")}
AWARDS_PER_TEAM = 3  # per game and team, besides Man of the Match; the kept cards count as awards of their team
# Without Wisehockey data the awards are handed out freely. award title -> (positions that fit it, the official
# statistic the winner is picked from, the KPIs on the card back). Forwards and defenders by the club rosters;
# a player without a known position only gets the awards open to everyone (None).
FWD, DEF = "Forward", "Defender"
SKATER_AWARDS = {
    "Sniper": ({FWD}, "goals", ["goals", "shots", "points"]),
    "Playmaker": ({FWD, DEF}, "assists", ["assists", "points", "toi"]),
    "Volume Shooter": ({FWD}, "shots", ["shots", "goals", "shot_top_speed"]),
    "Chance Creator": ({FWD}, "shots", ["shots", "goals", "points"]),
    "Go-To Scorer": ({FWD}, "points", ["points", "goals", "shots"]),
    "Shot Blocker": ({DEF}, "toi", ["toi", "shots", "points"]),
    "Workhorse": ({FWD, DEF, None}, "toi", ["toi", "shots", "points"]),
    "Speedster": ({FWD}, "shot_top_speed", ["shot_top_speed", "shots", "toi"]),
    "Pressure Breaker": ({DEF, FWD}, "assists", ["assists", "points", "toi"]),
    "Progression Master": ({DEF}, "points", ["points", "assists", "toi"]),
    "Chance Architect": ({FWD}, "assists", ["assists", "points", "shots"]),
    "Attack Launcher": ({FWD}, "shots", ["shots", "points", "shot_top_speed"]),
    "Escape Artist": ({DEF}, "toi", ["toi", "assists", "points"]),
    "Puck Hunter": ({FWD, DEF, None}, "toi", ["toi", "shots", "goals"]),
    "Pass Thief": ({DEF, FWD}, "toi", ["toi", "assists", "shots"]),
}
GOALIE_AWARDS = {"Shot Stopper": ["saves", "save_pct", "shots_on_goal_against"]}  # and Brick Wall, a performance card
CANDIDATES = 6  # the winner is picked among the players with the best statistic for the award
AWARD_SEED = 2025
STRENGTH = {"PP1": "Power play", "PP2": "Power play", "SH1": "Short-handed", "SH2": "Short-handed", "EN": "Empty net"}


def with_card_image(player: dict, entry, full_art: bool = False) -> dict:
    """The player block with the card's own image from card_images.json (a URL, or {"image_url", "position"}), so
    no two cards share a photo. On a full art card (performance, and road once it turns into the champion card) the
    image also replaces the action media, which is what the dark card shows."""
    if not entry:
        return player
    if isinstance(entry, str):
        entry = {"image_url": entry}
    image = {"image_url": entry["image_url"], "image_position": entry.get("position")}
    if full_art:
        image |= {"action_image_url": entry["image_url"], "action_video_url": None, "action_focus": entry.get("position")}
    return {**player, **image}


def _key(p: dict) -> tuple[str, int]:
    return p["team"], p["jersey"]


def _name(p: dict) -> str:
    return f'{p["first_name"]} {p["last_name"]}'


def _seconds(clock: str) -> int:
    minutes, seconds = clock.split(":")
    return int(minutes) * 60 + int(seconds)


def _skater_rating(stats: dict) -> int:
    """Made-up match rating for test cards: points, shots, plus/minus and ice time lift it from a base of 60."""
    plus_minus = max(-2, min(2, stats.get("plus_minus") or 0))
    score = (60 + 10 * (stats.get("goals") or 0) + 6 * (stats.get("assists") or 0) + (stats.get("shots") or 0)
             + 3 * plus_minus + ((stats.get("toi") or 0) / 60 - 14) * 0.7)
    return int(max(55, min(99, score)) + 0.5)


def _goalie_rating(stats: dict) -> int:
    """Made-up: 40 at an 80 % save percentage, 99 at 95 % (the range the real goalie rating uses)."""
    return int(40 + 59 * max(0, min(1, ((stats.get("save_pct") or 0) - 80) / 15)) + 0.5)


class TestData:
    __test__ = False  # not a pytest class

    def __init__(self, specs: dict, metrics: dict, format_value, positions: dict, images: dict, nationalities: dict,
                 action_media: dict, card_images: dict, archetypes: dict):
        doc = json.loads(TESTDATA_FILE.read_text(encoding="utf-8"))
        self.games = sorted(doc["games"], key=lambda g: (g["date"], g["start"]))
        self.by_id = {g["id"]: g for g in self.games}
        self.source_note = doc["source"]
        self._specs, self._metrics, self._format = specs, metrics, format_value
        self._positions, self._images, self._nationalities = positions, images, nationalities
        self._action_media = action_media
        self.card_images = card_images
        self._archetypes = archetypes
        self.cards: dict[str, dict] = {}
        self.game_cards: dict[str, list[str]] = {g["id"]: [] for g in self.games}
        self.highlights = {h["game_id"]: h for h in json.loads(HIGHLIGHTS_FILE.read_text(encoding="utf-8"))["games"]}
        self._broadcasts = self._load_broadcasts()
        self._build()

    def _load_broadcasts(self) -> dict[tuple[str, int], dict]:
        """(game id, goal index) -> the stretch of the game's highlight video showing that goal. Fails fast if a clip
        names a game or a score that is not in the test data."""
        broadcasts = {}
        for game_id, video in self.highlights.items():
            if game_id not in self.by_id:
                raise ValueError(f"Highlights for an unknown game: {game_id}")
            scores = [f'{g["home_score"]}-{g["away_score"]}' for g in self.by_id[game_id]["goals"]]
            for clip in video["clips"]:
                if clip["score"] not in scores:
                    raise ValueError(f'Clip in {game_id} points to no goal: {clip["score"]}')
                broadcasts[(game_id, scores.index(clip["score"]))] = {
                    "video_id": f"highlights-{game_id}", "youtube_id": video["youtube_id"],
                    "start": clip["start"], "end": clip["end"]}
        return broadcasts

    def highlight_sources(self, game_ids) -> list[dict]:
        """The highlight videos of the given games, for the source line under a clip (VideoSlot)."""
        return [{"id": f"highlights-{gid}", "youtube_id": h["youtube_id"], "title": h["title"], "channel": h["channel"],
                 "url": h["url"], "permission": f'Official highlights, embedded with the YouTube player from the '
                                                f'{h["channel"]} channel. Not downloaded or re-edited.'}
                for gid in dict.fromkeys(game_ids) if (h := self.highlights.get(gid))]

    def action_of(self, key: tuple[str, int]) -> dict:
        media = self._action_media.get(key, {})
        return {"action_image_url": media.get("image_url"), "action_video_url": media.get("video_url"),
                "action_focus": media.get("focus")}

    def _build(self):
        rng = random.Random(AWARD_SEED)
        award_count = dict.fromkeys([*SKATER_AWARDS, *GOALIE_AWARDS, "Brick Wall", "Game Winner"], 0)
        player_count: dict[tuple[str, int], int] = {}
        record = None  # (speed, player, game) best hardest shot of the games so far
        for game in self.games:
            picks = {} if game["has_wisehockey"] else self._picks(game)
            top = max((p for p in game["players"] if p["stats"].get("shot_top_speed")),
                      key=lambda p: p["stats"]["shot_top_speed"], default=None)
            if top and record and top["stats"]["shot_top_speed"] > record[0]:
                before = record
                speed = top["stats"]["shot_top_speed"]
                picks["recordbreaker"] = (
                    top, f"Hardest shot of the tournament so far: {speed:.1f} km/h, beating the previous best of "
                    f"{before[0]:.1f} km/h by {_name(before[1])} on {before[2]['date'][8:]} Dec.")
            if top and (record is None or top["stats"]["shot_top_speed"] > record[0]):
                record = (top["stats"]["shot_top_speed"], top, game)
            # Man of the Match, and the few kept cards; the rest of the game's cards are awards.
            picks = {t: pick for t, pick in picks.items()
                     if t == "motm" or game["has_wisehockey"] or (pick[0]["first_name"], pick[0]["last_name"]) in KEPT_SPECIALS}
            for special_type, (player, explanation) in picks.items():
                card = self._card(game, special_type, player, explanation)
                self.cards[card["id"]] = card
                self.game_cards[game["id"]].append(card["id"])
            if not game["has_wisehockey"]:
                for card in self._award_cards(game, picks, rng, award_count, player_count):
                    self.cards[card["id"]] = card
                    self.game_cards[game["id"]].append(card["id"])

    def _award_cards(self, game: dict, picks: dict, rng, award_count: dict, player_count: dict) -> list[dict]:
        """Three awards per team for a game without data, handed out at random but always from the awards and the
        players used least so far, so both are spread evenly over the tournament. A player holds one card per game.
        Game Winner only exists in games decided by one goal, for the real scorer of the winning goal; Brick Wall
        and Shot Stopper go to a goalkeeper. The kept cards (see KEPT_SPECIALS) count as awards of their team."""
        taken = {_key(player) for player, _ in picks.values()}
        cards = []
        close = abs(game["home_score"] - game["away_score"]) == 1
        real = self._picks(game)
        for team in (game["home_team"], game["away_team"]):
            kept = [self.cards[c] for c in self.game_cards[game["id"]]
                    if self.cards[c]["player"]["team"] == team and self.cards[c]["special_type"] != "motm"]
            titles = {c["title"] for c in kept}
            for c in kept:
                award_count[c["title"]] += 1
            have = len(kept)
            players = [p for p in game["players"] if p["team"] == team and _key(p) not in taken]
            skaters = [p for p in players if not p["goalkeeper"] and (p["stats"].get("toi") or 0) > 0]
            goalies = [p for p in players if p["goalkeeper"] and p["stats"].get("shots_against")]
            if close and "gamewinner" in real and real["gamewinner"][0]["team"] == team and "Game Winner" not in titles:
                player, explanation = real["gamewinner"]
                cards.append(self._card(game, "gamewinner", player, explanation))
                titles.add("Game Winner")
                award_count["Game Winner"] += 1
                player_count[_key(player)] = player_count.get(_key(player), 0) + 1
                skaters = [p for p in skaters if _key(p) != _key(player)]
                have += 1
            while have < AWARDS_PER_TEAM:
                options = [t for t in SKATER_AWARDS if t not in titles and self._fitting(skaters, t)]
                if goalies:
                    options += [t for t in (*GOALIE_AWARDS, "Brick Wall") if t not in titles]
                rng.shuffle(options)  # ties between equally used awards are broken at random
                title = min(options, key=lambda t: award_count[t])
                titles.add(title)
                award_count[title] += 1
                if title in GOALIE_AWARDS or title == "Brick Wall":
                    player = min(goalies, key=lambda p: player_count.get(_key(p), 0))
                    goalies = []  # one goalkeeper card per team and game
                    s = player["stats"]
                    if title == "Brick Wall":
                        card = self._card(game, "wall", player, f'Stopped {s["saves"]} of {s["shots_against"]} shots '
                                          f'({s["save_pct"]:.1f} %). Test data has no expected goals, so all saves count here.')
                    else:
                        card = self._award_card(game, title, player, GOALIE_AWARDS[title])
                else:
                    stat, attributes = SKATER_AWARDS[title][1:]
                    fitting = sorted(self._fitting(skaters, title), key=lambda p: -(p["stats"].get(stat) or 0))[:CANDIDATES]
                    rng.shuffle(fitting)
                    player = min(fitting, key=lambda p: player_count.get(_key(p), 0))
                    skaters = [p for p in skaters if _key(p) != _key(player)]
                    card = self._award_card(game, title, player, attributes)
                player_count[_key(player)] = player_count.get(_key(player), 0) + 1
                cards.append(card)
                have += 1
        return cards

    def _fitting(self, skaters: list[dict], title: str) -> list[dict]:
        position = {"Forward": FWD, "Defender": DEF}
        return [p for p in skaters if position.get(self._positions.get(_key(p))) in SKATER_AWARDS[title][0]]

    def _picks(self, game: dict) -> dict:
        home_wins = game["home_score"] > game["away_score"]
        winner = game["home_team"] if home_wins else game["away_team"]
        loser_goals = min(game["home_score"], game["away_score"])
        skaters = [p for p in game["players"] if not p["goalkeeper"]]
        picks = {}

        star = max((p for p in skaters if p["team"] == winner),
                   key=lambda p: (p["stats"].get("points", 0), p["stats"].get("goals", 0)), default=None)
        if star and star["stats"].get("points"):
            g, a = star["stats"].get("goals", 0), star["stats"].get("assists", 0)
            picks["motm"] = (star, f'{g} goal{"" if g == 1 else "s"} and {a} assist{"" if a == 1 else "s"}: '
                                   f'the most points on the winning team in the {winner} win.')

        won = [goal for goal in game["goals"] if goal["team"] == winner]
        if len(won) > loser_goals and not game["overtime"]:
            goal = won[loser_goals]
            scorer = goal["scorer"] and next((p for p in skaters if _key(p) == (goal["team"], goal["scorer"]["jersey"])), None)
            if scorer:
                picks["gamewinner"] = (scorer, f'Scored the goal that made it {goal["home_score"]}–{goal["away_score"]} '
                                               f'at {goal["clock"]}. The opponent never drew level again.')

        goalies = [p for p in game["players"] if p["goalkeeper"] and p["stats"].get("shots_against")]
        if goalies:
            wall = max(goalies, key=lambda p: p["stats"]["saves"])
            s = wall["stats"]
            picks["wall"] = (wall, f'Stopped {s["saves"]} of {s["shots_against"]} shots ({s["save_pct"]:.1f} %), the most '
                                   "of any goalkeeper in the game. Test data has no expected goals, so all saves count here.")
        return picks

    def _moments(self, game: dict, player: dict) -> list[dict]:
        key, moments = _key(player), []
        for i, goal in enumerate(game["goals"]):
            scorer = goal["scorer"] and (goal["team"], goal["scorer"]["jersey"])
            helpers = [(goal["team"], a["jersey"]) for a in goal["assists"]]
            if key == scorer:
                text = "Assisted by " + " and ".join(_name(a) for a in goal["assists"]) + "." if goal["assists"] else "Unassisted."
                kind, title = "goal", "Goal"
            elif key in helpers:
                kind, title, text = "assist", "Assist", f'Goal by {_name(goal["scorer"]) if goal["scorer"] else "a teammate"}.'
            else:
                continue
            moments.append(self._moment(game, f"goal-{i}", kind, title, goal["clock"], text,
                                        [f'{goal["home_score"]}–{goal["away_score"]}', STRENGTH.get(goal["strength"] or "")],
                                        self._broadcasts.get((game["id"], i))))
        for i, pen in enumerate(game["penalties"]):
            if pen["player"] and (pen["team"], pen["player"]["jersey"]) == key:
                moments.append(self._moment(game, f"pen-{i}", "penalty", "Penalty", pen["clock"],
                                            f'{pen["reason"]}, {pen["minutes"]} min.', []))
        return sorted(moments, key=lambda m: m["game_seconds"])

    @staticmethod
    def _moment(game: dict, suffix: str, kind: str, title: str, clock: str, text: str, facts: list,
                broadcast: dict | None = None) -> dict:
        seconds = _seconds(clock)
        period = min(seconds // 1200 + 1, 3)
        in_period = seconds - (period - 1) * 1200
        return {
            "id": f"{game['id']}-{suffix}", "game_id": game["id"], "timestamp": str(seconds), "game_seconds": seconds, "kind": kind,
            "period": period, "period_label": f"{ORDINALS[period]} period",
            "clock": f"{in_period // 60}:{in_period % 60:02d}", "game_time": clock, "title": title, "text": text,
            "facts": [f for f in facts if f], "shot_speed": None, "xg": None, "clip": None, "broadcast": broadcast,
        }

    def _attribute(self, game: dict, metric_id: str, player: dict, moments: list[dict]) -> dict:
        metric = self._metrics[metric_id]
        stat = STAT_OF[metric_id]
        pool = [p for p in game["players"] if p["goalkeeper"] == player["goalkeeper"]]
        if metric_id == "shot_top_speed":
            pool = [p for p in pool if p["stats"].get(stat)]  # speeds are missing for players without a shot
        values = [p["stats"].get(stat, 0) or 0 for p in pool]
        raw = player["stats"].get(stat, 0) or 0
        value = raw / 100 if metric_id == "save_pct" else raw
        kinds = MOMENT_KINDS.get(metric_id)
        return {
            "metric_id": metric_id, "label": metric["label"], "value": value,
            "display_value": self._format(value, metric["format"]), "unit": metric["unit"],
            "higher_is_better": metric["higher_is_better"], "definition": metric["definition"],
            "source_definition": "Official game statistics of the Spengler Cup (spenglercup.ch)",
            "match_rank": 1 + sum(v > raw for v in values) if raw else None,
            "team_rank": 1 + sum((p["stats"].get(stat, 0) or 0) > raw for p in pool if p["team"] == player["team"]) if raw else None,
            "players_in_match": len(pool), "rank_pool": "goalkeepers" if player["goalkeeper"] else "players",
            "moment_ids": [m["id"] for m in moments if m["kind"] in kinds] if kinds else None,
        }

    def _card(self, game: dict, special_type: str, player: dict, explanation: str) -> dict:
        spec = self._specs[special_type]
        position = "Goalkeeper" if player["goalkeeper"] else self._positions.get(_key(player), "Skater")
        mr = _goalie_rating(player["stats"]) if player["goalkeeper"] else _skater_rating(player["stats"])
        moments = self._moments(game, player)
        opponent = game["away_team"] if player["team"] == game["home_team"] else game["home_team"]
        card_id = f'test-{special_type}-{game["id"]}'
        return {
            "id": card_id, "type": "special", "kind": "performance",
            "special_type": special_type, "test": True, "test_game": game["id"],
            "rating": {"mr": mr, "tier": tier_of(mr)},
            "player": with_card_image({
                "first_name": player["first_name"], "last_name": player["last_name"], "jersey": player["jersey"],
                "team": player["team"], "position": position,
                "image_url": self._images.get(_key(player)) or player["image_url"],
                "nationality": self._nationalities.get(_key(player)),
                **self.action_of(_key(player)),
            }, self.card_images.get(card_id), full_art=True),
            "title": spec["title"], "archetype": TEST_RULES.get(special_type, spec["rule"]), "archetype_kpis": None,
            "match": {
                "id": game["id"], "date": game["date"], "stage": game["stage"], "home_team": game["home_team"],
                "away_team": game["away_team"], "home_score": game["home_score"], "away_score": game["away_score"],
                "opponent": opponent,
            },
            "attributes": [self._attribute(game, m, player, moments) for m in spec["attributes"]],
            "explanation": explanation, "achievement": None, "video": None, "video_sources": self.highlight_sources([game["id"]]),
            "moments": moments, "edition": "standard", "source": SOURCE,
        }

    def _award_card(self, game: dict, title: str, player: dict, attributes: list[str]) -> dict:
        if title == "Puck Hunter" and player["last_name"] == "Fora":
            # The demo Puck Hunter card goes to Nico Gross instead, when he played in the game.
            player = next((p for p in game["players"] if (p["first_name"], p["last_name"]) == ("Nico", "Gross")), player)
        moments = self._moments(game, player)
        opponent = game["away_team"] if player["team"] == game["home_team"] else game["home_team"]
        team_slug = re.sub(r"[^a-z]+", "-", player["team"].lower()).strip("-")
        title_slug = re.sub(r"[^a-z]+", "-", title.lower()).strip("-")
        card_id = f'test-{title_slug}-{game["id"]}-{team_slug}-{player["jersey"]}'
        mr = _goalie_rating(player["stats"]) if player["goalkeeper"] else _skater_rating(player["stats"])
        position = "Goalkeeper" if player["goalkeeper"] else self._positions.get(_key(player), "Skater")
        return {
            "id": card_id, "type": "special", "kind": "profile",
            "special_type": None, "test": True, "test_game": game["id"],
            "rating": {"mr": mr, "tier": tier_of(mr)},
            "player": with_card_image({
                "first_name": player["first_name"], "last_name": player["last_name"], "jersey": player["jersey"],
                "team": player["team"], "position": position,
                "image_url": self._images.get(_key(player)) or player["image_url"],
                "nationality": self._nationalities.get(_key(player)),
                **self.action_of(_key(player)),
            }, self.card_images.get(card_id)),
            "title": title, "archetype": self._archetypes[title], "archetype_kpis": None,
            "match": {
                "id": game["id"], "date": game["date"], "stage": game["stage"], "home_team": game["home_team"],
                "away_team": game["away_team"], "home_score": game["home_score"], "away_score": game["away_score"],
                "opponent": opponent,
            },
            "attributes": [self._attribute(game, m, player, moments) for m in attributes],
            "explanation": f"{title} for {_name(player)}. There is no tracking data for this game, so the award and "
                           "its winner are picked for the demo.",
            "achievement": None, "video": None, "video_sources": self.highlight_sources([game["id"]]),
            "moments": moments, "edition": "standard", "source": SOURCE,
        }
