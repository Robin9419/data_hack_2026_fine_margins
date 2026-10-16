"""Match rating (MR) and tier per player, computed from the match statistics and events CSVs.

A skater's rating is his best type score: the weighted sum of his percentile in each KPI of the type.
The percentile is (pool - rank) / (pool - 1) with ties sharing the best rank. Percentage KPIs only count
for players with enough attempts and rank among those players. MR = 40 + 59 * score, so 40 to 99.
Goalkeepers use their own formula (save %, high-danger save rate, goals saved above expected)."""

MIN_PASSES = 10
MIN_FACEOFFS = 5
HIGH_DANGER_XG = 0.15

# type -> {stats CSV column: weight}
TYPE_WEIGHTS = {
    "Sniper": {"G": 35, "xGsum": 35, "S": 30},
    "Playmaker": {"A": 40, "Passes": 30, "Pass-%": 30},
    "Speedster": {"SPD TOP (km/h)": 50, "Sprint SPD-Z DIST (m)": 30, "PCW": 20},
    "Defender": {"BKS": 50, "PCW": 25, "TOI (s)": 25},
    "Workhorse": {"TOI (s)": 50, "Dist (m)": 50},
    "Faceoff Ace": {"FOW": 50, "FOW-%": 50},
}
# columns only ranked among players who attempted enough: column -> (attempts column, minimum)
GATED = {"Pass-%": ("All passes", MIN_PASSES), "FOW": ("No. FO", MIN_FACEOFFS), "FOW-%": ("No. FO", MIN_FACEOFFS)}

TIERS = (("elite", 97), ("gold", 90), ("silver", 80), ("bronze", 0))


def tier_of(mr: int) -> str:
    return next(name for name, minimum in TIERS if mr >= minimum)


def _num(raw) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _percentile(value: float, pool: list[float]) -> float:
    if len(pool) < 2:
        return 0.0
    rank = 1 + sum(v > value for v in pool)
    return (len(pool) - rank) / (len(pool) - 1)


def _rounded(x: float) -> int:
    return int(x + 0.5)


def skater_ratings(rows: list[dict]) -> dict[tuple[str, int], dict]:
    def eligible(row: dict, column: str) -> bool:
        gate = GATED.get(column)
        return gate is None or _num(row[gate[0]]) >= gate[1]

    pools = {c: [_num(r[c]) for r in rows if eligible(r, c)] for w in TYPE_WEIGHTS.values() for c in w}
    ratings = {}
    for row in rows:
        scores = {
            name: sum(
                weight * _percentile(_num(row[c]), pools[c]) if eligible(row, c) else 0.0
                for c, weight in weights.items()
            )
            for name, weights in TYPE_WEIGHTS.items()
        }
        best = max(scores, key=scores.get)
        mr = _rounded(40 + 59 * scores[best] / 100)
        ratings[(row["Team"], int(row["Jersey"]))] = {"mr": mr, "tier": tier_of(mr), "type": best}
    return ratings


def goalie_stats(event_rows: list[dict], sides: dict[str, str]) -> dict[tuple[str, int], dict]:
    """Shots on goal (saved or scored, empty-net goals excluded) per goalkeeper, from the Shot events."""
    stats: dict[tuple[str, int], dict] = {}
    for r in event_rows:
        if r["EventType"] != "Shot" or r["ShotResult"] not in ("Saved", "Goal") or not r["EventSecondaryPlayerName"]:
            continue
        key = (sides[r["EventSecondaryTeam"]], int(r["EventSecondaryPlayerName"].split(" ", 1)[0].lstrip("#")))
        g = stats.setdefault(key, {"shots": 0, "saves": 0, "xg": 0.0, "hd_shots": 0, "hd_saves": 0})
        xg = _num(r["ShotXG"])
        saved = r["ShotResult"] == "Saved"
        g["shots"] += 1
        g["saves"] += saved
        g["xg"] += xg
        if xg >= HIGH_DANGER_XG:
            g["hd_shots"] += 1
            g["hd_saves"] += saved
    return stats


def goalie_ratings(event_rows: list[dict], sides: dict[str, str]) -> dict[tuple[str, int], dict]:
    def clamp(v: float) -> float:
        return max(0.0, min(1.0, v))

    ratings = {}
    for key, g in goalie_stats(event_rows, sides).items():
        sv = g["saves"] / g["shots"]
        hd = g["hd_saves"] / g["hd_shots"] if g["hd_shots"] else 0.5
        gsax = g["xg"] - (g["shots"] - g["saves"])
        mr = _rounded(40 + 59 * (0.45 * clamp((sv - 0.80) / 0.15) + 0.35 * hd + 0.2 * clamp((gsax + 2) / 4)))
        ratings[key] = {"mr": mr, "tier": tier_of(mr), "type": "Goalie"}
    return ratings


def compute_ratings(rows: list[dict], event_rows: list[dict], sides: dict[str, str]) -> dict[tuple[str, int], dict]:
    return skater_ratings(rows) | goalie_ratings(event_rows, sides)
