"""Road to Final: one evolving card per star player that grows while the tournament goes on.

The card is built from the games played so far on the user's tournament timeline (see tournament.py), so it shows what
the player's tournament looks like up to that point: the rating per game as bars, an average rating and a stage.
See docs/CARD_TYPES.md. The game ratings are the made-up test ratings of testdata.py."""

import re

from .ratings import tier_of
from .testdata import SOURCE, TestData, _key, _skater_rating, with_card_image

STAGES = [
    {"n": 1, "name": "Debut", "when": "After the first game", "trigger": "The player plays his first tournament game.",
     "change": "A card in the tier of that game's rating."},
    {"n": 2, "name": "In Form", "when": "After the second game",
     "trigger": "Every further game. The card rating is the average of all tournament games.",
     "change": "The rating follows the average, a trend arrow and the form chart are added."},
    {"n": 3, "name": "Finalist", "when": "After the semi-final",
     "trigger": "The player's team wins its semi-final and reaches the final.",
     "change": "One tier up and fine glitter."},
    {"n": 4, "name": "Champion", "when": "After the final", "trigger": "The player's team wins the Spengler Cup.",
     "change": "Champion look: dark gold, surname on the side, champion label."},
]
PRE_STAGE = {"n": 0, "name": "Ones to Watch", "when": "From the start of the tournament",
             "trigger": "Available from the start. The card grows with every game the player plays.",
             "change": "The first game gives it a match rating."}
TIER_ORDER = ["bronze", "silver", "gold", "elite"]
STARS_PER_TEAM = 2
MIN_GAMES = 3  # to be a star of the tournament: played at least this many of his team's games


def _won(team: str, game: dict) -> bool:
    own, other = (game["home_score"], game["away_score"]) if game["home_team"] == team else (game["away_score"], game["home_score"])
    return own > other


class RoadToFinal:
    def __init__(self, testdata: TestData, positions: dict, highlights: list[dict]):
        self._td = testdata
        self._positions = positions
        self._highlights = {(h["team"], h["jersey"]): h for h in highlights}
        self._player = {}  # (game id, (team, jersey)) -> the player's entry in that game
        self._rating = {}  # same key -> made-up match rating, only for skaters who got ice time
        for game in testdata.games:
            for p in game["players"]:
                self._player[(game["id"], _key(p))] = p
                if not p["goalkeeper"] and p["stats"].get("toi"):
                    self._rating[(game["id"], _key(p))] = _skater_rating(p["stats"])
        self.team_games: dict[str, list[dict]] = {}
        for game in testdata.games:
            for team in (game["home_team"], game["away_team"]):
                self.team_games.setdefault(team, []).append(game)
        self.stars = self._stars()

    def _stars(self) -> list[tuple[str, int]]:
        """The best skaters of each team by their average rating over all of the team's games."""
        stars = []
        for team, games in self.team_games.items():
            averages = {}
            for key in {k for (gid, k) in self._rating if k[0] == team}:
                ratings = [self._rating[(g["id"], key)] for g in games if (g["id"], key) in self._rating]
                if len(ratings) >= MIN_GAMES:
                    averages[key] = sum(ratings) / len(ratings)
            stars += sorted(averages, key=lambda k: (-averages[k], k[1]))[:STARS_PER_TEAM]
        return stars

    def cards_for(self, played: set[str]) -> list[dict]:
        """A card per star, from the start of the tournament on, built from the given games that have been played."""
        included = {g for g in played if g in self._td.by_id}
        return [self._card(key, included) for key in self.stars]

    @staticmethod
    def _card_id(key: tuple[str, int]) -> str:
        return f'test-road-{re.sub(r"[^a-z]+", "-", key[0].lower().replace("ö", "o")).strip("-")}-{key[1]}'

    def pointed(self, game_id: str) -> list[dict]:
        """The stars with a goal or an assist in the game: their card id, name and points in that game."""
        result = []
        for key in self.stars:
            entry = self._player.get((game_id, key))
            goals, assists = (entry["stats"].get("goals") or 0, entry["stats"].get("assists") or 0) if entry else (0, 0)
            if goals or assists:
                result.append({"card_id": self._card_id(key), "name": f'{entry["first_name"]} {entry["last_name"]}',
                               "goals": goals, "assists": assists})
        return result

    @staticmethod
    def _label(game: dict, index: int) -> str:
        return {"Quarterfinal": "QF", "Semifinal": "Semi", "Final": "Final"}.get(game["stage"], f"G{index + 1}")

    def _card(self, key: tuple[str, int], included: set[str]) -> dict:
        team = key[0]
        games = self.team_games[team]
        slots, played = [], []
        for i, game in enumerate(games):
            mr = self._rating.get((game["id"], key)) if game["id"] in included else None
            opponent = game["away_team"] if game["home_team"] == team else game["home_team"]
            slots.append({"label": self._label(game, i), "mr": mr, "game_id": game["id"], "opponent": opponent,
                          "result": f'{game["home_score"]}–{game["away_score"]}', "date": game["date"]})
            if mr is not None:
                played.append((game, slots[-1]))

        n = len(played)
        stage = 0 if n == 0 else 1 if n == 1 else 2
        semi = next((g for g, _ in played if g["stage"] == "Semifinal"), None)
        final = next((g for g, _ in played if g["stage"] == "Final"), None)
        if stage == 2 and semi and _won(team, semi):
            stage = 3
            if final and _won(team, final):
                stage = 4
        average = int(sum(s["mr"] for _, s in played) / n + 0.5) if n else None
        tier = None
        if n:
            tier = tier_of(average)
            if stage >= 3:
                tier = TIER_ORDER[min(TIER_ORDER.index(tier) + 1, len(TIER_ORDER) - 1)]
        trend = average - played[0][1]["mr"] if n >= 2 else None

        # Before the first game the card shows the player from his first game in the schedule.
        last = played[-1][0] if n else None
        first_seen = next(g for g in games if (g["id"], key) in self._player)
        entry = self._player[((last or first_seen)["id"], key)]
        moments = []
        for game, slot in played:
            for m in self._td._moments(game, entry):
                moments.append({**m, "text": f'{slot["label"]} vs {slot["opponent"]}. {m["text"]}'})
        info = STAGES[stage - 1] if stage else PRE_STAGE
        goals = sum(self._player[(g["id"], key)]["stats"].get("goals", 0) for g, _ in played)
        assists = sum(self._player[(g["id"], key)]["stats"].get("assists", 0) for g, _ in played)
        card_id = self._card_id(key)
        return {
            "id": card_id, "type": "special",
            "kind": "road", "special_type": None, "test": True, "test_game": None,
            "rating": {"mr": average, "tier": tier},
            "player": with_card_image({
                "first_name": entry["first_name"], "last_name": entry["last_name"], "jersey": key[1], "team": team,
                "position": self._positions.get(key, "Skater"),
                "image_url": self._td._images.get(key) or entry["image_url"],
                "nationality": self._td._nationalities.get(key),
                **self._td.action_of(key),
            }, (self._td.card_images.get(f"{card_id}-champ") if stage == 4 else None) or self._td.card_images.get(card_id),
                full_art=True),
            "title": "Spengler Cup Champion" if stage == 4 else info["name"],
            "archetype": "An evolving card: it grows with every game of the tournament the player plays.",
            "archetype_kpis": None,
            "match": None if last is None else {
                "id": last["id"], "date": last["date"], "stage": last["stage"], "home_team": last["home_team"],
                "away_team": last["away_team"], "home_score": last["home_score"], "away_score": last["away_score"],
                "opponent": last["away_team"] if last["home_team"] == team else last["home_team"],
            },
            "attributes": [
                self._total("goals", goals, moments), self._total("assists", assists, moments),
                self._total("points", goals + assists, moments),
            ],
            "explanation": (f'Stage {stage}, {info["name"]}: {n} {"game" if n == 1 else "games"} played, '
                            f'{f"average match rating {average}" if n else "no match rating yet"}. {info["trigger"]}'),
            "achievement": None, "video": self._highlight(key), "video_sources": self._highlight_sources(key),
            "moments": moments, "edition": "standard",
            "source": SOURCE,
            "road": {
                "stage": stage, "stage_name": info["name"], "games": slots, "trend": trend, "played": n,
                "stages": [{**s, "reached": s["n"] <= stage} for s in STAGES],
            },
        }

    def _highlight(self, key: tuple[str, int]) -> dict | None:
        h = self._highlights.get(key)
        if not h:
            return None
        return {"video_id": h["id"], "youtube_id": h["youtube_id"], "start": h["start"], "end": h["end"],
                "poster": f'https://i.ytimg.com/vi/{h["youtube_id"]}/hqdefault.jpg', "description": h["title"],
                "scope": "player"}

    def _highlight_sources(self, key: tuple[str, int]) -> list[dict]:
        h = self._highlights.get(key)
        if not h:
            return []
        return [{"id": h["id"], "youtube_id": h["youtube_id"], "title": h["title"], "channel": h["channel"],
                 "url": h["url"], "permission": f'Player highlight embedded with the YouTube player from {h["channel"]}. '
                                                 "Not downloaded or re-edited."}]

    def _total(self, metric_id: str, value: int, moments: list[dict]) -> dict:
        metric = self._td._metrics[metric_id]
        kinds = {"goals": ("goal",), "assists": ("assist",), "points": ("goal", "assist")}[metric_id]
        return {
            "metric_id": metric_id, "label": metric["label"], "value": value, "display_value": str(value),
            "unit": "", "higher_is_better": True, "definition": f'{metric["definition"]} Total over the games shown.',
            "source_definition": "Official game statistics of the Spengler Cup (spenglercup.ch)",
            "match_rank": None, "team_rank": None, "players_in_match": None, "rank_pool": "players",
            "moment_ids": [m["id"] for m in moments if m["kind"] in kinds],
        }
