"""Writes docs/mockups/card-kpis.js for the user journey mockup (docs/mockups/user-journey.html):
- CARD_KPIS: the data behind each special card of the final (the KPIs that earned it, the story sentence, the game
  events with shot locations), from the Wisehockey data.
- PLAYER_GAMES: every game of the HC Davos and U.S. Collegiate Selects players in the tournament (official game
  statistics in testdata.json: goals, assists, shots, ice time), with a demo role per game. Only the final has tracking
  data, so the roles of the other games come from a simple rule on the official numbers (see demo_role).

Run from the backend folder: python -m scripts.mockup_kpis"""

import json
from collections import Counter
from pathlib import Path

from app.content import get_content

OUT = Path(__file__).resolve().parents[2] / "docs" / "mockups" / "card-kpis.js"
TESTDATA = Path(__file__).resolve().parents[1] / "content" / "testdata.json"
TEAMS = {"HC Davos", "U.S. Collegiate Selects"}
KPI_FIELDS = ("metric_id", "label", "display_value", "unit", "definition", "match_rank", "team_rank", "players_in_match", "rank_pool")
MOMENT_FIELDS = ("kind", "period_label", "clock", "title", "text", "facts", "xg")


def demo_role(row: dict, team_rows: list[dict]) -> str | None:
    """The role a skater stood for in one game, from the official numbers only (no tracking data)."""
    most = lambda key: max((r.get(key) or 0) for r in team_rows)
    if row["goals"] >= 2:
        return "Sniper"
    if row["assists"] >= 2:
        return "Playmaker"
    if row["goals"] and row["shots"] and row["shots"] == most("shots"):
        return "Go-To Scorer"
    if row["shots"] and row["shots"] == most("shots"):
        return "Volume Shooter"
    if row["toi"] and row["toi"] == most("toi"):
        return "Workhorse"
    return None


def player_games(content) -> dict:
    out = {}
    for game in json.loads(TESTDATA.read_text(encoding="utf-8"))["games"]:
        goals, assists = Counter(), Counter()
        for goal in game["goals"]:
            if goal.get("scorer"):
                goals[(goal["team"], goal["scorer"]["jersey"])] += 1
            for a in goal.get("assists") or []:
                assists[(goal["team"], a["jersey"])] += 1
        rows = []
        for p in game["players"]:
            if p["team"] not in TEAMS or not p["stats"].get("toi"):
                continue
            s = p["stats"]
            home = p["team"] == game["home_team"]
            row = {
                "key": f"{p['team']}#{p['jersey']}",
                "team": p["team"],
                "game": game["id"], "date": game["date"], "stage": game["stage"],
                "home_team": game["home_team"], "away_team": game["away_team"],
                "home_score": game["home_score"], "away_score": game["away_score"],
                "opponent": game["away_team"] if home else game["home_team"],
                "won": (game["home_score"] > game["away_score"]) == home,
                "goalkeeper": p["goalkeeper"],
                "toi": s.get("toi"),
            }
            if p["goalkeeper"]:
                row |= {k: s.get(k) for k in ("saves", "shots_against", "goals_against", "save_pct")}
            else:
                key = (p["team"], p["jersey"])
                row |= {"goals": goals[key], "assists": assists[key], "shots": s.get("shots") or 0,
                        "plus_minus": s.get("plus_minus"), "pim": s.get("pim") or 0}
            rows.append(row)
        for row in rows:
            if not row["goalkeeper"]:
                row["role"] = demo_role(row, [r for r in rows if r["team"] == row["team"] and not r["goalkeeper"]])
        for row in rows:
            out.setdefault(row.pop("key"), []).append(row)
    # A few players of the final are missing from the official lists; their final comes from the Wisehockey stats.
    m = content.match
    for r in content.rows:
        key = f"{r['Team']}#{int(r['Jersey'])}"
        if r["Team"] not in TEAMS or key in out:
            continue
        home = r["Team"] == m["home_team"]
        out[key] = [{
            "team": r["Team"], "game": m["id"], "date": m["date"], "stage": "Final",
            "home_team": m["home_team"], "away_team": m["away_team"], "home_score": m["home_score"], "away_score": m["away_score"],
            "opponent": m["away_team"] if home else m["home_team"], "won": (m["home_score"] > m["away_score"]) == home,
            "goalkeeper": False, "toi": int(float(r["TOI (s)"])), "goals": int(r["G"]), "assists": int(r["A"]),
            "shots": int(r["S"]), "plus_minus": int(r["+"]) - int(r["-"]), "pim": int(r["PIM"]), "role": None,
        }]
    return out


def main():
    content = get_content()
    shots = {r["Timestamp"]: r for r in content.event_rows if r["EventType"] in ("Shot", "Goal") and r["EventStartCoordinate"]}
    scoring = [r for r in shots.values() if r["ShotResult"] == "Goal"]

    def shot_row(moment: dict):
        if moment["timestamp"] in shots:
            return shots[moment["timestamp"]]
        if moment["kind"] != "goal":
            return None
        # A goal event has no location; the shot that scored it comes a moment before.
        ts = int(moment["timestamp"])
        near = [r for r in scoring if abs(int(r["Timestamp"]) - ts) < 5000]
        return min(near, key=lambda r: abs(int(r["Timestamp"]) - ts), default=None)

    out = []
    for card in content.cards.values():
        if card.get("type") != "special" or card.get("test") or not card.get("player") or card.get("kind") not in ("profile", "performance"):
            continue
        kpis = card.get("archetype_kpis") or card["attributes"]
        wanted = {mid for k in kpis for mid in k.get("moment_ids") or []}
        moments = []
        for m in card.get("moments") or []:
            if m["id"] not in wanted:
                continue
            item = {f: m.get(f) for f in MOMENT_FIELDS}
            row = shot_row(m)
            if row:
                x, y = (float(v) for v in row["EventStartCoordinate"].split(","))
                # Every shot drawn towards the same net (teams switch ends between periods).
                item["at"] = [round(abs(x), 1), round(y if x >= 0 else -y, 1)]
            moments.append(item)
        player = card["player"]
        out.append({
            "team": player["team"],
            "jersey": player["jersey"],
            "kind": card["kind"],
            "special": card.get("special_type"),
            "title": card["title"],
            "archetype": card.get("archetype"),
            "explanation": card.get("explanation"),
            "kpis": [{f: k.get(f) for f in KPI_FIELDS} for k in kpis],
            "moments": moments,
        })
    OUT.write_text("// Generated by backend/scripts/mockup_kpis.py (Wisehockey data of the final, official game statistics).\n"
                   f"window.CARD_KPIS = {json.dumps(out, ensure_ascii=False, indent=1)};\n"
                   f"window.PLAYER_GAMES = {json.dumps(player_games(content), ensure_ascii=False)};\n", encoding="utf-8")
    print(f"{len(out)} cards -> {OUT}")


if __name__ == "__main__":
    main()
