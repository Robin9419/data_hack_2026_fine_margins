"""Writes frontend/public/data/player-games.json: every game of every player of the tournament, from the official game
statistics in testdata.json (goals and assists come from the goal lists). Keyed by "<team>#<jersey>".

Run from the backend folder: python -m scripts.player_games"""

import json
from collections import Counter
from pathlib import Path

from app.content import get_content

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "frontend" / "public" / "data" / "player-games.json"
TESTDATA = Path(__file__).resolve().parents[1] / "content" / "testdata.json"
# Team names of the official statistics -> the names of the app (frontend/src/teams.js).
TEAM_NAMES = {"IFK Helsinki": "HIFK"}


def team_name(name: str) -> str:
    return TEAM_NAMES.get(name, name)


def game_row(game: dict, team: str) -> dict:
    home = team == team_name(game["home_team"])
    return {
        "game": game["id"], "date": game["date"], "stage": game["stage"],
        "home_team": team_name(game["home_team"]), "away_team": team_name(game["away_team"]),
        "home_score": game["home_score"], "away_score": game["away_score"],
        "opponent": team_name(game["away_team"] if home else game["home_team"]),
        "won": (game["home_score"] > game["away_score"]) == home,
    }


def all_player_games(content) -> dict:
    out = {}
    for game in json.loads(TESTDATA.read_text(encoding="utf-8"))["games"]:
        goals, assists = Counter(), Counter()
        for goal in game["goals"]:
            if goal.get("scorer"):
                goals[(goal["team"], goal["scorer"]["jersey"])] += 1
            for a in goal.get("assists") or []:
                assists[(goal["team"], a["jersey"])] += 1
        for p in game["players"]:
            s = p["stats"]
            if not s.get("toi"):
                continue
            team = team_name(p["team"])
            row = game_row(game, team) | {"goalkeeper": bool(p["goalkeeper"]), "toi": s["toi"]}
            if p["goalkeeper"]:
                row |= {k: s.get(k) for k in ("saves", "shots_against", "goals_against", "save_pct")}
            else:
                key = (p["team"], p["jersey"])
                row |= {"goals": goals[key], "assists": assists[key], "shots": s.get("shots") or 0,
                        "plus_minus": s.get("plus_minus") or 0, "pim": s.get("pim") or 0}
            out.setdefault(f"{team}#{p['jersey']}", []).append(row)
    # A few players of the final are missing from the official lists; their final comes from the Wisehockey stats.
    m = content.match
    for r in content.rows:
        team = team_name(r["Team"])
        key = f"{team}#{int(r['Jersey'])}"
        if key in out:
            continue
        out[key] = [game_row(m, team) | {
            "goalkeeper": False, "toi": int(float(r["TOI (s)"])), "goals": int(r["G"]), "assists": int(r["A"]),
            "shots": int(r["S"]), "plus_minus": int(r["+"]) - int(r["-"]), "pim": int(r["PIM"]),
        }]
    for rows in out.values():
        rows.sort(key=lambda r: r["date"])
    return out


def main():
    out = all_player_games(get_content())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    teams = Counter(k.rsplit("#", 1)[0] for k in out)
    print(f"{len(out)} players -> {OUT}\n{dict(teams)}")


if __name__ == "__main__":
    main()
