"""Fetches the official game data of the 2025 Spengler Cup (all 11 games) into backend/content/testdata.json.

The Wisehockey export only covers the final, so this is the "test data" for the other games: result, goals, penalties
and per-player statistics from the game pages of spenglercup.ch. Run from the backend folder:

    python -m scripts.fetch_testdata
"""

import json
import re
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "content" / "testdata.json"
BASE = "https://www.spenglercup.ch/en/game/spengler-cup/"
GAMES = [  # (stage, path) in game order
    ("Group Torriani", "regular-season/2025-12-26_hc-fribourg-gotteron_hc-sparta-praha"),
    ("Group Cattini", "regular-season/2025-12-26_team-canada_us-collegiate-selects"),
    ("Group Torriani", "regular-season/2025-12-27_ifk-helsinki_hc-sparta-praha"),
    ("Group Cattini", "regular-season/2025-12-27_hc-davos_us-collegiate-selects"),
    ("Group Torriani", "regular-season/2025-12-28_hc-fribourg-gotteron_ifk-helsinki"),
    ("Group Cattini", "regular-season/2025-12-28_team-canada_hc-davos"),
    ("Quarterfinal", "pre-semifinal/2025-12-29_hc-sparta-praha_team-canada"),
    ("Quarterfinal", "pre-semifinal/2025-12-29_hc-davos_ifk-helsinki"),
    ("Semifinal", "playoff-12-final/2025-12-30_us-collegiate-selects_hc-sparta-praha"),
    ("Semifinal", "playoff-12-final/2025-12-30_hc-fribourg-gotteron_hc-davos"),
    ("Final", "playoff-final/2025-12-31_us-collegiate-selects_hc-davos"),
]
FINAL_ID = "2025-12-31_us-collegiate-selects_hc-davos"  # the game with Wisehockey data (backend/content/match.json)
STAT_KEYS = {
    "G": "goals", "A": "assists", "PTS": "points", "PIM": "pim", "skatingStatistics.plusMinus.total": "plus_minus",
    "skatingStatistics.skating.timeOnIce": "toi", "skatingStatistics.shot.shots": "shots",
    "skatingStatistics.shot.fastestShotSpeed": "shot_top_speed", "saves": "saves", "shotsAgainst": "shots_against",
    "goalsAgainst": "goals_against", "savePercentage": "save_pct",
}


CLUB_NAMES = {"IFK Helsinki": "HIFK"}  # the card set (backend/content/base_cards.json) uses HIFK


def club(name: str) -> str:
    return CLUB_NAMES.get(name, name)


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(request, timeout=60).read().decode("utf-8", "ignore")


def game_object(page: str) -> dict:
    """The game record embedded in the Next.js payload of a game page."""
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', page, flags=re.S)
    payload = "".join(json.loads(f'"{c}"') for c in chunks)
    decoder = json.JSONDecoder()
    for match in re.finditer(r'"game":\{', payload):
        try:
            candidate, _ = decoder.raw_decode(payload[match.end() - 1:])
        except ValueError:
            continue
        if "ticker" in candidate and "stats_players" in candidate:
            return candidate
    raise ValueError("no game record in page")


def player(detail: dict | None) -> dict | None:
    if not detail:
        return None
    return {
        "first_name": detail["givenname"], "last_name": detail["familyname"], "jersey": int(detail["jerseynr"]),
        "image_url": detail.get("portrait1_url") or None,
    }


def number(value):
    try:
        x = float(str(value).replace(",", "."))
    except ValueError:
        return None
    return int(x) if x.is_integer() else x


def toi_seconds(value) -> int:
    minutes, seconds = str(value).split(":")
    return int(minutes) * 60 + int(seconds)


def build_game(stage: str, path: str) -> dict:
    obj = game_object(fetch(BASE + path))
    teams = {obj["teamhome"]["team_id"]: club(obj["teamhome"]["name"]), obj["teamaway"]["team_id"]: club(obj["teamaway"]["name"])}
    start = datetime.fromisoformat(obj["time"]) + timedelta(hours=1)  # the feed is UTC, Davos is UTC+1 in winter
    goals, penalties = [], []
    for e in sorted(obj["ticker"], key=lambda e: int(e["index_overall"] or 0)):
        team = teams[e["team_id"]]
        clock = e["time_formatted"]
        if e["type"] == "goal":
            home, away = (int(x) for x in e["current_result"].split(":"))
            goals.append({
                "clock": clock, "team": team, "home_score": home, "away_score": away, "strength": e.get("goal_type"),
                "scorer": player(e["player_detail"]),
                "assists": [a for a in (player(e.get("assist1_detail")), player(e.get("assist2_detail"))) if a],
            })
        elif e["type"] == "foul":
            penalties.append({
                "clock": clock, "team": team, "player": player(e["player_detail"]), "minutes": int(e["minutes"]),
                "reason": e["foul_name"],
            })
    players = []
    for team_id, rows in obj["stats_players"]["stats"].items():
        for row in rows.values():
            stats = {}
            for key, name in STAT_KEYS.items():
                if key in row and row[key]["value"] not in ("", None):
                    stats[name] = toi_seconds(row[key]["value"]) if name == "toi" else number(row[key]["value"])
            if "TOI" in row and row["TOI"]["value"]:
                stats["toi"] = toi_seconds(row["TOI"]["value"])
            players.append({"team": teams[team_id], **player(row["player"]), "goalkeeper": "saves" in stats, "stats": stats})
    return {
        "id": path.split("/")[-1], "url": BASE + path, "stage": stage, "date": start.date().isoformat(),
        "start": start.strftime("%H:%M"), "arena": obj["arena"].split(",")[0],
        "home_team": club(obj["teamhome"]["name"]), "away_team": club(obj["teamaway"]["name"]),
        "home_score": int(obj["scorehome"]), "away_score": int(obj["scoreaway"]),
        "periods": [[int(obj[f"scorehome_{p}"] or 0), int(obj[f"scoreaway_{p}"] or 0)] for p in ("one", "two", "three")],
        "overtime": bool(obj["overtime_home"] or obj["overtime_away"] or obj["penalty_home"] or obj["penalty_away"]),
        "has_wisehockey": path.endswith(FINAL_ID), "goals": goals, "penalties": penalties, "players": players,
        "logos": {club(obj["teamhome"]["name"]): obj["teamhome"]["logo"], club(obj["teamaway"]["name"]): obj["teamaway"]["logo"]},
    }


if __name__ == "__main__":
    games = [build_game(stage, path) for stage, path in GAMES]
    doc = {
        "_comment": "TEST DATA. Official game data of the 2025 Spengler Cup from spenglercup.ch (generated by "
                    "scripts/fetch_testdata.py; do not edit by hand). Only the final has Wisehockey data. The app "
                    "builds extra cards from these games when a user switches them on.",
        "source": "Spengler Cup Davos, official game pages (spenglercup.ch)",
        "fetched": datetime.now().date().isoformat(),
        "games": games,
    }
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for g in games:
        print(g["id"], f'{g["home_score"]}:{g["away_score"]}', len(g["goals"]), "goals", len(g["players"]), "players")
