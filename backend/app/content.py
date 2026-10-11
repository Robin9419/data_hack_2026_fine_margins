"""Loads the static content (metrics, match, cards) and joins it with the
Wisehockey match statistics CSV so card values always come from the data."""

import csv
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTENT_DIR = ROOT / "backend" / "content"
DATA_DIR = ROOT / "data"
PLAYER_IMAGES_FILE = ROOT / "docs" / "player-images.json"


def _load_json(name: str) -> dict:
    return json.loads((CONTENT_DIR / name).read_text(encoding="utf-8"))


def _to_number(raw: str):
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return int(value) if value.is_integer() else value


def format_value(value, fmt: str) -> str:
    if value is None:
        return "–"
    if fmt == "int":
        return str(int(value))
    if fmt == "decimal1":
        return f"{value:.1f}"
    if fmt == "decimal2":
        return f"{value:.2f}"
    if fmt == "pct":
        return f"{round(value * 100)}"
    if fmt == "km":
        return f"{value / 1000:.2f}"
    if fmt == "mmss":
        minutes, seconds = divmod(int(value), 60)
        return f"{minutes}:{seconds:02d}"
    return str(value)


class Content:
    def __init__(self):
        self.match = _load_json("match.json")
        self.metrics = {m["id"]: m for m in _load_json("metrics.json")["metrics"]}
        self.achievements = {a["id"]: a for a in _load_json("achievements.json")["achievements"]}
        cards_doc = _load_json("cards.json")
        self.pack_size = cards_doc["pack_size"]
        self.archetypes = cards_doc["archetypes"]
        rewards_doc = _load_json("rewards.json")
        self.card_points = rewards_doc["card_points"]
        self.rewards = rewards_doc["rewards"]
        self.rows = self._load_stats()
        self.goalie_rows = self._load_goalie_stats()
        self.player_images = self._load_player_images()
        self.cards = {c["id"]: self._build_card(c) for c in cards_doc["cards"]}

    def _load_stats(self) -> list[dict]:
        path = DATA_DIR / self.match["stats_file"]
        with path.open(encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def _load_goalie_stats(self) -> list[dict]:
        """The stats CSV only covers skaters, so goalkeeper numbers are counted from the
        match events CSV: every Shot event names the goalkeeper as the secondary player."""
        path = DATA_DIR / self.match["events_file"]
        with path.open(encoding="utf-8-sig", newline="") as f:
            shots = [r for r in csv.DictReader(f) if r["EventType"] == "Shot" and r["EventSecondaryPlayerName"]]
        sides = {"Home": self.match["home_team"], "Away": self.match["away_team"]}
        goalies = {}
        for shot in shots:
            name = shot["EventSecondaryPlayerName"]  # e.g. "#30 Adam Gajan"
            if name not in goalies:
                number, first, last = name.split(" ", 2)
                goalies[name] = {
                    "Team": sides[shot["EventSecondaryTeam"]],
                    "Jersey": number.lstrip("#"),
                    "FirstName": first,
                    "LastName": last,
                    "Saves": 0,
                    "Goals against": 0,
                    "Shot attempts against": 0,
                }
            g = goalies[name]
            g["Shot attempts against"] += 1
            g["Saves"] += shot["ShotResult"] == "Saved"
            g["Goals against"] += shot["ShotResult"] == "Goal"
        for g in goalies.values():
            g["Shots on goal against"] = g["Saves"] + g["Goals against"]
            g["SV-%"] = g["Saves"] / g["Shots on goal against"] if g["Shots on goal against"] else None
        return list(goalies.values())

    def _load_player_images(self) -> dict[tuple[str, int], str]:
        """(team, jersey) -> image URL, from the player image research file."""
        players = json.loads(PLAYER_IMAGES_FILE.read_text(encoding="utf-8"))["players"]
        return {(p["team"], p["jersey"]): p["image_url"] for p in players if p.get("image_url")}

    def _find_row(self, team: str, jersey: int) -> dict:
        for row in self.rows + self.goalie_rows:
            if row["Team"] == team and int(row["Jersey"]) == jersey:
                return row
        raise ValueError(f"No stats row for {team} #{jersey}")

    def _pool(self, metric: dict) -> list[dict]:
        """Skater metrics are compared with all skaters, goalkeeper metrics with both goalkeepers."""
        return self.goalie_rows if metric.get("goalkeeper") else self.rows

    def _rank(self, metric: dict, value) -> int:
        """1-based rank of value within the metric's pool (ties share a rank)."""
        values = [_to_number(r[metric["column"]]) for r in self._pool(metric)]
        values = [v for v in values if v is not None]
        if metric["higher_is_better"]:
            return 1 + sum(1 for v in values if v > value)
        return 1 + sum(1 for v in values if v < value)

    def _build_attribute(self, metric_id: str, row: dict) -> dict:
        metric = self.metrics[metric_id]
        value = _to_number(row[metric["column"]])
        attr = {
            "metric_id": metric_id,
            "label": metric["label"],
            "value": value,
            "display_value": format_value(value, metric["format"]),
            "unit": metric["unit"],
            "higher_is_better": metric["higher_is_better"],
            "definition": metric["definition"],
            "source_definition": metric["source_definition"],
            "match_rank": self._rank(metric, value) if value is not None else None,
            "players_in_match": len(self._pool(metric)),
            "rank_pool": "goalkeepers" if metric.get("goalkeeper") else "players",
        }
        if "count_column" in metric:
            attr["detail"] = f'{row[metric["count_column"]]} of {row[metric["total_column"]]}'
        return attr

    def _build_card(self, cfg: dict) -> dict:
        row = self._find_row(cfg["team"], cfg["jersey"])
        m = self.match
        opponent = m["away_team"] if cfg["team"] == m["home_team"] else m["home_team"]
        return {
            "id": cfg["id"],
            "player": {
                "first_name": row["FirstName"],
                "last_name": row["LastName"],
                "jersey": cfg["jersey"],
                "team": cfg["team"],
                "position": cfg["position"],
                "image_url": self.player_images.get((cfg["team"], cfg["jersey"])),
            },
            "title": cfg["title"],
            "match": {
                "id": m["id"],
                "date": m["date"],
                "stage": m["stage"],
                "home_team": m["home_team"],
                "away_team": m["away_team"],
                "home_score": m["home_score"],
                "away_score": m["away_score"],
                "opponent": opponent,
            },
            "attributes": [self._build_attribute(mid, row) for mid in cfg["attributes"]],
            "explanation": cfg["explanation"],
            "achievement": self.achievements.get(cfg["achievement"]) if cfg["achievement"] else None,
            "video": cfg["video"],
            "edition": "standard",
            "source": m["events_source"] if cfg["position"] == "Goalkeeper" else m["source"],
        }

    def card_summary(self, card: dict) -> dict:
        """What the gallery shows for a card the user does not own yet: only the (grayed out) photo."""
        player = card["player"]
        return {
            "id": card["id"],
            "player": {
                "image_url": player.get("image_url"),
                "jersey": player.get("jersey"),
                "team": player["team"],
                "first_name": "",
                "last_name": "",
            },
        }

    def progress(self, owned: dict[str, str]) -> dict:
        """Reward-bar state from the owned cards (card id -> edition)."""
        points = sum(self.card_points.get(edition, 0) for edition in owned.values())
        rewards = [{**r, "reached": points >= r["points"]} for r in self.rewards]
        return {
            "points": points,
            "max_points": rewards[-1]["points"],
            "rewards": rewards,
            "owned_count": len(owned),
            "stadium_count": sum(1 for e in owned.values() if e == "stadium"),
            "total_cards": len(self.cards),
        }

    def build_question(self, card_id: str, rng) -> dict:
        """Multiple choice 'who was the <archetype>?' question: the card's player plus two
        other players from the set, shuffled. option_ids are card ids."""
        card = self.cards[card_id]
        others = [c for c in self.cards if c != card_id]
        option_ids = rng.sample(others, min(2, len(others))) + [card_id]
        rng.shuffle(option_ids)
        m = card["match"]
        return {
            "option_ids": option_ids,
            "prompt": f'Who was the "{card["title"]}" in this game?',
            "clue": self.archetypes[card["title"]],
            "match": f'{m["home_team"]} {m["home_score"]}–{m["away_score"]} {m["away_team"]}',
        }


@lru_cache
def get_content() -> Content:
    return Content()
