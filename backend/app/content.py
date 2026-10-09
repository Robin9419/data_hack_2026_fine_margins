"""Loads the static content (metrics, match, cards) and joins it with the
Wisehockey match statistics CSV so card values always come from the data."""

import csv
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTENT_DIR = ROOT / "backend" / "content"
DATA_DIR = ROOT / "data"


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
        self.starter_card_ids = cards_doc["starter_card_ids"]
        self.rows = self._load_stats()
        self.cards = {c["id"]: self._build_card(c) for c in cards_doc["cards"]}

    def _load_stats(self) -> list[dict]:
        path = DATA_DIR / self.match["stats_file"]
        with path.open(encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def _find_row(self, team: str, jersey: int) -> dict:
        for row in self.rows:
            if row["Team"] == team and int(row["Jersey"]) == jersey:
                return row
        raise ValueError(f"No stats row for {team} #{jersey}")

    def _rank(self, metric: dict, value) -> int:
        """1-based rank of value among all players in the match (ties share a rank)."""
        values = [_to_number(r[metric["column"]]) for r in self.rows]
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
            "players_in_match": len(self.rows),
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
            "source": m["source"],
        }

    def card_summary(self, card: dict) -> dict:
        """What the gallery shows for a card the user does not own yet."""
        return {
            "id": card["id"],
            "player": {"team": card["player"]["team"]},
            "title": card["title"],
            "match": card["match"],
        }


@lru_cache
def get_content() -> Content:
    return Content()
