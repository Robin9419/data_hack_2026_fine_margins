"""Shootout duel: the user and an opponent (a bot for now) take turns attacking one half of the rink. The attack is one
skater against a goalkeeper (1 vs 1) or two skaters against a goalkeeper and a defender (2 vs 2). Both sides only pick
cards; the play itself is simulated from the cards' strengths and weaknesses.

Strengths and weaknesses come from the game of the card:
- The final's cards use the Wisehockey data: shots and goals by distance to the net, hardest shot, top speed, passes,
  puck battles, blocks, interceptions, and for goalkeepers the saves by distance and after a pass, compared with the
  expected goals (xG) of the shots they faced.
- Every other player card (base cards, legends, and the specials of the other games, which only have box scores) gets a
  random profile from the player's position, seeded by the card id so it never changes. These profiles are deliberately
  weaker than the real ones (at most SAMPLED_MAX): any card can play, but the real-data players are the ones to pick.
  The opponent (a bot in this demo) only picks real-data players.

Every attack starts from a real controlled zone entry of the final: where the puck carrier, his nearest teammate and the
nearest opponent stood as the puck crossed the blue line, mirrored so the attack always goes up the ice, with a little
jitter. From there the carrier skates in, passes or shoots (up to MAX_ACTIONS moves), the teammate without the puck
skates into space, the defender stays between the puck and the net and the goalie follows the puck. Every play comes
with a plain-language explanation of why it ended the way it did.
"""

import math
import random
from functools import lru_cache

from .content import get_content
from .event_kpis import coordinate, infer_attack_directions
from .events import ORDINALS, _clock
from .ratings import HIGH_DANGER_XG

NET = (26.0, 0.0)  # goal line 4 m from the end boards of the 60 m rink, attack towards +x
BLUE_LINE = 7.1
CLOSE_RANGE = 11  # metres from the net: closer is a close-range shot, farther a long-range one
ONE_TIMER_MS = 3000  # a shot within this time of a teammate's completed pass counts as a shot after a pass
REGULATION_ROUNDS = 3
MAX_ROUNDS = 8  # sudden death ends in a draw after this many rounds
STAND_IN = "goalie:"  # id prefix of a skater card playing in goal

# trait: (label, short label, what it does in the duel, phrase when strong, phrase when weak)
SKATER_TRAITS = {
    "close": ("Close-range finishing", "Finishing", "Scores from inside 11 m", "finishes well up close", "struggles to finish up close"),
    "long": ("Long-range shooting", "Long shots", "Scores from 11 m and farther", "scores from distance", "rarely scores from distance"),
    "power": ("Shot power", "Hard shot", "Hard shots beat goalies from distance", "has a hard shot", "has a soft shot"),
    "speed": ("Skating speed", "Speed", "Skates past defenders, and as a defender closes them down", "is fast", "is slow"),
    "passing": ("Passing", "Passing", "Passes that get through and set up one-timers", "passes accurately", "passes poorly"),
    "battles": ("Puck battles", "Puck battles", "Keeps the puck in a duel, or wins it back", "wins puck battles", "loses puck battles"),
    "blocking": ("Shot blocking", "Blocking", "Gets in front of shots as a defender", "blocks shots", "rarely blocks shots"),
    "reading": ("Reading passes", "Interceptions", "Intercepts passes as a defender", "reads passes well", "rarely reads passes"),
}
GOALIE_TRAITS = {
    "close": ("Close-range saves", "Close saves", "Stops chances from in close", "is strong in close", "is beatable in close"),
    "long": ("Long-range saves", "Long saves", "Stops shots from 11 m and farther", "stops long shots", "lets in long shots"),
    "lateral": ("Saves after a pass", "Moving across", "Gets across in time for a one-timer", "moves across quickly after a pass", "is slow to move across after a pass"),
}

# Sampled profiles: random around SAMPLED_LEVEL, moved by the position, never above SAMPLED_MAX.
SAMPLED_LEVEL = 35
SAMPLED_MAX = 60
# Special cards (impact specials, Ones to Watch, legends) without data are stronger than base cards, still random.
SPECIAL_LEVEL = 52
SPECIAL_MAX = 80
# Legends are the best of them: a higher level, and the stats can reach the top of the scale.
LEGEND_LEVEL = 65
LEGEND_MAX = 100
POSITION_BIAS = {
    "Forward": {"close": 10, "long": 8, "power": 5, "blocking": -10, "reading": -5},
    "Defender": {"blocking": 12, "reading": 10, "battles": 5, "close": -10, "long": -5},
}


def _clamp(value, low, high):
    return max(low, min(high, value))


def _plural(n, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 'es' if word.endswith('s') else 's'}"


def _num(raw) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _dist(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _segment(p, a, b) -> tuple[float, float]:
    """Distance from p to the segment a-b, and how far along the segment (0 to 1) the closest point is."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = dx * dx + dy * dy
    t = 0.0 if not length else _clamp(((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length, 0.0, 1.0)
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy), t


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def _short(name: str) -> str:
    return name.split(" ", 1)[-1] if " " in name else name


def _strengths(traits: dict) -> tuple[list[str], list[str]]:
    ranked = sorted(traits, key=lambda k: -traits[k]["value"])
    strengths = [k for k in ranked if traits[k]["value"] >= 65][:3]
    weaknesses = [k for k in reversed(ranked) if traits[k]["value"] <= 35][:2]
    return strengths, weaknesses


class Shootout:
    """Player profiles of every impact special card, and the real attacking moments of the final."""

    def __init__(self, content):
        self.content = content
        self.directions = infer_attack_directions(content.analysis)
        self.final_id = content.tournament.final["id"]
        self.positions = {(c["player"]["team"], c["player"]["jersey"]): c["player"]["position"]
                          for c in content.cards.values() if c["type"] == "base"}
        self.shots = self._final_shots()
        self.skater_data = self._final_skaters()
        self.goalie_data = self._final_goalies()
        self.profiles = {}
        for cid, card in content.cards.items():
            if card["type"] in ("special", "base", "legend") and card.get("player"):
                self.profiles[cid] = self._profile(cid, card)
        # The Ones to Watch (Road to Final) cards are players too: they are not in content.cards, but they play with the
        # real data of the final when the player played it.
        # A Ones to Watch card only has data once the final is played, so there are two versions of it (see at()).
        self.final_profiles = dict(self.profiles)
        for card in content.road_to_final.cards_for(set()):
            self.profiles[card["id"]] = self._profile(card["id"], card, data=False)
            self.final_profiles[card["id"]] = self._profile(card["id"], card, data=True)
        self._add_stand_ins()
        self.scenarios = self._scenarios()

    def at(self, final_played: bool) -> dict:
        """The profiles at a stage of the tournament: the tracking data of the final only exists once it is played."""
        return self.final_profiles if final_played else self.profiles

    def _add_stand_ins(self):
        """For a user without a goalkeeper card: every skater card also exists as a stand-in goalie (id STAND_IN + card
        id), a skater put in goal with really bad goalie stats."""
        for cid, p in list(self.final_profiles.items()):
            if p["role"] != "skater":
                continue
            key = STAND_IN + cid
            rng = random.Random(key)
            traits = {t: {"value": rng.randint(5, 18), "evidence": None, "label": v[0], "short": v[1], "use": v[2]}
                      for t, v in GOALIE_TRAITS.items()}
            strengths, weaknesses = _strengths(traits)
            self.profiles[key] = self.final_profiles[key] = {
                **p, "card_id": key, "role": "goalie", "position": "Goalkeeper", "real": False, "game": None,
                "traits": traits, "strengths": strengths, "weaknesses": weaknesses, "stand_in": True}

    # Profiles

    def _position(self, card: dict) -> str:
        p = card["player"]
        if p["position"] in ("Forward", "Defender", "Goalkeeper"):
            return p["position"]
        return self.positions.get((p["team"], p["jersey"]), "Forward")

    def _final_shots(self) -> list[dict]:
        """Every shot of the final with its distance to the net it was aimed at, and whether it came within
        ONE_TIMER_MS of a completed pass by the shooter's team."""
        shots, last_pass = [], {}
        for r in self.content.event_rows:
            side, ts = r["EventPrimaryTeam"], int(r["Timestamp"])
            if r["EventType"] == "Pass" and r["PassResult"] == "Successful":
                last_pass[side] = ts
            if r["EventType"] != "Shot":
                continue
            xy = coordinate(r["EventStartCoordinate"])
            sign = self.directions.get((int(r["Period"]), side))
            if not xy or not sign:
                continue
            shots.append({
                "shooter": r["EventPrimaryPlayerId"],
                "goalie": r["EventSecondaryPlayerId"] or None,
                "result": r["ShotResult"],
                "xg": _num(r["ShotXG"]),
                "distance": _dist((xy[0] * sign, xy[1] * sign), NET),
                "after_pass": ts - last_pass.get(side, -10**12) <= ONE_TIMER_MS,
            })
        return shots

    def _final_skaters(self) -> dict[tuple[str, int], dict]:
        """Raw numbers, ranks and evidence for every skater of the final, by (team, jersey)."""
        content = self.content
        intercepts = content.derived_kpis["interceptions"]["players"]
        xa = content.derived_kpis["expected_assists"]["players"]
        raw, facts = {}, {}
        for row in content.rows:
            key = (row["Team"], int(row["Jersey"]))
            pid = content.events.player_id(*key)
            own = [s for s in self.shots if s["shooter"] == pid and s["result"] in ("Saved", "Goal")]
            close = [s for s in own if s["distance"] < CLOSE_RANGE]
            far = [s for s in own if s["distance"] >= CLOSE_RANGE]
            goals_close = sum(s["result"] == "Goal" for s in close)
            goals_far = [s for s in far if s["result"] == "Goal"]
            passes, pass_pct = _num(row["Passes"]), _num(row["Pass-%"])
            xa_total = (xa.get(pid) or {}).get("total") or 0
            steals = (intercepts.get(pid) or {}).get("interceptions") or 0
            raw[key] = {
                "close": goals_close + 0.15 * len(close),
                "long": len(goals_far) + 0.15 * len(far),
                "power": _num(row["S TOP (km/h)"]),
                "speed": _num(row["SPD TOP (km/h)"]),
                "passing": pass_pct * min(1, passes / 15) + 0.6 * xa_total + 0.1 * _num(row["A"]),
                "battles": _num(row["PCW"]),
                "blocking": _num(row["BKS"]),
                "reading": steals,
            }
            longest = max((s["distance"] for s in goals_far), default=None)
            facts[key] = {
                "close": f"{_plural(goals_close, 'goal')} from {_plural(len(close), 'shot')} on goal inside 11 m",
                "long": f"{_plural(len(goals_far), 'goal')} from {_plural(len(far), 'shot')} on goal from 11 m or more"
                        + (f", one from {longest:.0f} m" if longest else ""),
                "power": f"Hardest shot {_num(row['S TOP (km/h)']):.1f} km/h" if _num(row["S TOP (km/h)"]) else "No shot speed measured",
                "speed": f"Top speed {_num(row['SPD TOP (km/h)']):.1f} km/h",
                "passing": (f"{round(pass_pct * 100)}% of {_plural(int(passes), 'pass')} completed"
                            + (f", {xa_total:.2f} expected assists" if xa_total else "")),
                "battles": f"{_plural(int(_num(row['PCW'])), 'puck battle')} won",
                "blocking": f"{_plural(int(_num(row['BKS'])), 'shot')} blocked",
                "reading": f"{_plural(int(steals), 'pass')} intercepted",
            }
        n = len(raw)
        result = {}
        for key, values in raw.items():
            traits = {}
            for trait, value in values.items():
                below = sum(other[trait] < value for other in raw.values())
                rank = 1 + sum(other[trait] > value for other in raw.values())
                traits[trait] = {"value": round(15 + 80 * below / (n - 1)),
                                 "evidence": f"{facts[key][trait]} (#{rank} of {n} skaters)"}
            result[key] = traits
        return result

    def _final_goalies(self) -> dict[str, dict]:
        """Saves for each goalkeeper of the final, by player id: on the high-danger chances (the Brick Wall rule, they
        are the close-range chances), on shots from 11 m or more and on shots right after a pass. Each is the saves
        above what the xG of the shots expected, shrunk towards average for small samples."""
        result = {}
        for gid in {s["goalie"] for s in self.shots if s["goalie"]}:
            faced = [s for s in self.shots if s["goalie"] == gid and s["result"] in ("Saved", "Goal")]
            groups = {
                "close": ([s for s in faced if s["xg"] >= HIGH_DANGER_XG], f"high-danger chances ({HIGH_DANGER_XG} xG or more)"),
                "long": ([s for s in faced if s["distance"] >= CLOSE_RANGE], "shots from 11 m or more"),
                "lateral": ([s for s in faced if s["after_pass"]], "shots right after a pass"),
            }
            traits = {}
            for trait, (shots, what) in groups.items():
                saves = sum(s["result"] == "Saved" for s in shots)
                expected = len(shots) - sum(s["xg"] for s in shots)
                above = (saves - expected) / (len(shots) + 3)
                evidence = f"Stopped {saves} of {len(shots)} {what}; xG expected {expected:.1f}"
                soft = [s for s in shots if s["result"] == "Goal" and s["xg"] < 0.05]
                if soft:
                    evidence += f". Let in a goal from {soft[0]['distance']:.0f} m worth only {soft[0]['xg']:.3f} xG"
                traits[trait] = {"value": round(_clamp(50 + 300 * above, 10, 95)), "evidence": evidence}
            result[gid] = traits
        return result

    @staticmethod
    def _sampled(cid: str, position: str, special: bool = False, legend: bool = False) -> dict:
        rng = random.Random(cid)
        level, top = ((LEGEND_LEVEL, LEGEND_MAX) if legend else (SPECIAL_LEVEL, SPECIAL_MAX)) if special else (SAMPLED_LEVEL, SAMPLED_MAX)
        if position == "Goalkeeper":
            return {t: {"value": round(_clamp(level + 3 + rng.randint(-12, 12), 15, top)), "evidence": None}
                    for t in GOALIE_TRAITS}
        bias = POSITION_BIAS.get(position, {})
        return {t: {"value": round(_clamp(level + bias.get(t, 0) + rng.randint(-12, 12), 10, top)),
                    "evidence": None} for t in SKATER_TRAITS}

    def _profile(self, cid: str, card: dict, data: bool = True) -> dict:
        p = card["player"]
        position = self._position(card)
        goalie = position == "Goalkeeper"
        traits = None
        if self.content.card_game.get(cid) == self.final_id or (card.get("kind") == "road" and data):
            if goalie:
                traits = self.goalie_data.get(self.content.events.player_id(p["team"], p["jersey"]))
            else:
                traits = self.skater_data.get((p["team"], p["jersey"]))
        real = traits is not None
        if not real:
            traits = self._sampled(cid, position, card["type"] in ("special", "legend"), card["type"] == "legend")
        labels = GOALIE_TRAITS if goalie else SKATER_TRAITS
        traits = {t: {**traits[t], "label": labels[t][0], "short": labels[t][1], "use": labels[t][2]} for t in labels}
        strengths, weaknesses = _strengths(traits)
        m = card.get("match") or {}
        if real and card.get("kind") == "road":
            m = self.content.tournament.final  # the data is from the final
        return {
            "card_id": cid,
            "player": f'{p["first_name"]} {p["last_name"]}',
            "who": (p["first_name"], p["last_name"], p["team"]),
            "name": p["last_name"],
            "role": "goalie" if goalie else "skater",
            "position": position,
            "real": real,
            "game": f'{m["home_team"]} {m["home_score"]}–{m["away_score"]} {m["away_team"]}' if m and (card["type"] == "special" or real) else None,
            "traits": traits,
            "strengths": strengths,
            "weaknesses": weaknesses,
        }

    # Scenarios

    def _scenarios(self) -> list[dict]:
        """The controlled zone entries of the final: the puck carrier at the blue line with his nearest teammate (the
        support) and the nearest opposing skater (the defender), where they are spread out enough to be told apart."""
        content = self.content
        goalies = content.analysis.goalkeeper_ids
        sides = {"Home": content.match["home_team"], "Away": content.match["away_team"]}
        result = []
        for snap in content.analysis.snapshots:
            r = content.event_rows[snap["row_index"]]
            if (r["EventType"], r["BluelineCrossingDirection"], r["BluelineCrossingResult"]) != (
                    "BluelineCrossing", "TowardsOpponent", "PossessionMaintained"):
                continue
            pid, side = r["EventPrimaryPlayerId"], r["EventPrimaryTeam"]
            sign = self.directions.get((snap["period"], side))
            carrier = snap["players"].get(pid, (None, None))[1]
            if not sign or not carrier or pid in goalies:
                continue
            norm = lambda xy: (round(xy[0] * sign, 1), round(xy[1] * sign, 1))
            c = norm(carrier)
            if not (3 <= c[0] <= 11 and abs(c[1]) <= 12):
                continue
            others = [(s, norm(xy)) for p, (s, xy) in snap["players"].items() if p != pid and p not in goalies and xy]
            mates = sorted((xy for s, xy in others if s == side and 4 <= _dist(xy, c) <= 18
                            and 1 <= xy[0] <= 22 and abs(xy[1]) <= 13), key=lambda xy: _dist(xy, c))
            support = mates[0] if mates else None
            opponents = sorted((xy for s, xy in others if s != side and 2.5 <= _dist(xy, c) <= 12
                                and 2 <= xy[0] <= 24 and abs(xy[1]) <= 14
                                and (not support or _dist(xy, support) >= 2.5)), key=lambda xy: _dist(xy, c))
            period = snap["period"]
            result.append({
                "carrier": c,
                "support": support,
                "defender": opponents[0] if opponents else None,
                "source": f'{sides[side]} zone entry, {ORDINALS.get(period, period)} period {_clock(int(r["MatchClock"]))}',
            })
        return result

    def scenario(self, mode: str, rng: random.Random, seen: list[int]) -> tuple[int, dict]:
        """A random zone entry not played yet in this duel (seen), jittered by up to 0.6 m, with the carrier set back
        up to 2 m so the attack starts with a skate over the blue line. Returns (index, scenario)."""
        pool = [i for i, s in enumerate(self.scenarios) if mode == "1v1" or (s["support"] and s["defender"])]
        index = rng.choice([i for i in pool if i not in seen] or pool)
        s = self.scenarios[index]

        def jitter(xy, back=0.0):
            return [round(_clamp(xy[0] - back + rng.uniform(-0.6, 0.6), 1, 23), 1),
                    round(_clamp(xy[1] + rng.uniform(-0.6, 0.6), -13, 13), 1)]

        result = {"carrier": jitter(s["carrier"], rng.uniform(0, 2)), "source": s["source"]}
        if mode == "2v2":
            result["support"] = jitter(s["support"])
            result["defender"] = jitter(s["defender"])
        return index, result


@lru_cache
def get_shootout() -> Shootout:
    return Shootout(get_content())


# Simulation

MAX_ACTIONS = 5  # moves of the attack (skate, pass, shoot); the last one is always a shot
SKATE_X_MAX = 22  # how close to the net a player skates before passing or shooting

AVERAGE = {
    "skater": {"name": "an average skater", "role": "skater", "real": False, "card_id": None,
               "traits": {t: {"value": 50, "label": v[0], "evidence": None} for t, v in SKATER_TRAITS.items()}},
    "goalie": {"name": "an average goalie", "role": "goalie", "real": False, "card_id": None,
               "traits": {t: {"value": 50, "label": v[0], "evidence": None} for t, v in GOALIE_TRAITS.items()}},
}


def _u(profile: dict, trait: str) -> float:
    """A trait as -1 (worst) to +1 (best), 0 is average."""
    return (profile["traits"][trait]["value"] - 50) / 50


def _factor(profile: dict, trait: str, helps_attack: bool, weight: float) -> dict:
    """A trait that moved a chance. impact is how much it moved it for the attack (log-odds, negative: for the
    defence), so the biggest reasons can be picked out."""
    t = profile["traits"][trait]
    good, bad = (SKATER_TRAITS if profile["role"] == "skater" else GOALIE_TRAITS)[trait][3:]
    impact = weight * _u(profile, trait) * (1 if helps_attack else -1)
    return {
        "card_id": profile["card_id"], "name": profile["name"], "trait": trait, "label": t["label"],
        "value": t["value"], "evidence": t["evidence"], "real": profile["real"], "impact": round(impact, 3),
        "favours": "attack" if impact >= 0 else "defence",
        "text": f'{profile["name"]} {good if t["value"] >= 50 else bad}',
    }


def shot_chance(shooter: dict, goalie: dict, pos, passer: dict | None = None) -> tuple[float, list[dict]]:
    """Goal chance of a shot from pos: a distance and angle model of expected goals (lifted a bit, it is a shootout),
    moved by the shooter's and goalie's traits for that range. Right after a pass the goalie has to move across: his
    'after a pass' trait and the passer's passing count too."""
    d = _dist(pos, NET)
    angle = math.atan2(abs(pos[1]), max(NET[0] - pos[0], 0.1))
    base = 0.6 * math.exp(-d / 5) * max(math.cos(angle), 0.15) + 0.01
    key = "close" if d < CLOSE_RANGE else "long"
    factors = [_factor(shooter, key, True, 1.2), _factor(goalie, key, False, 1.2)]
    if key == "long":
        factors.append(_factor(shooter, "power", True, 0.5))
    if passer:
        factors += [_factor(goalie, "lateral", False, 0.9), _factor(passer, "passing", True, 0.3)]
    logit = math.log(base / (1 - base)) + 0.45 + (0.45 if passer else 0) + sum(f["impact"] for f in factors)
    return _clamp(_sigmoid(logit), 0.03, 0.85), factors


def block_chance(defender: dict | None, d_pos, shot_pos) -> tuple[float, list[dict]]:
    """A defender within 2 m of the shooting lane, and in front of the shooter, may block the shot."""
    if not defender or not d_pos:
        return 0.0, []
    lane, t = _segment(d_pos, shot_pos, NET)
    if lane > 2.0 or t < 0.05:
        return 0.0, []
    return (1 - lane / 2.0) * (0.2 + 0.45 * defender["traits"]["blocking"]["value"] / 100), [_factor(defender, "blocking", False, 1.0)]


def battle_chance(carrier: dict, defender: dict | None, d_pos, start, target) -> tuple[float, list[dict]]:
    """Chance the defender takes the puck off a carrier skating from start to target: only if he can reach the path
    (a fast defender reaches farther), then speed and puck battles decide."""
    if not defender or not d_pos:
        return 0.0, []
    reach = 2 + 3 * defender["traits"]["speed"]["value"] / 100
    contest = _clamp(1 - _segment(d_pos, start, target)[0] / reach, 0, 1)
    if not contest:
        return 0.0, []
    factors = [_factor(carrier, "speed", True, 0.9), _factor(carrier, "battles", True, 0.9),
               _factor(defender, "battles", False, 1.08), _factor(defender, "speed", False, 0.72)]
    return contest * _sigmoid(-sum(f["impact"] for f in factors)) * 0.45, factors


def pass_chance(passer: dict, defender: dict | None, d_pos, start, target) -> tuple[float, list[dict]]:
    """Chance the defender intercepts a pass: only near the passing lane, then reading against passing."""
    if not defender or not d_pos:
        return 0.0, []
    lane, t = _segment(d_pos, start, target)
    if lane > 2.5 or t < 0.05 or t > 0.95:
        return 0.0, []
    factors = [_factor(passer, "passing", True, 1.8), _factor(defender, "reading", False, 1.8)]
    return (1 - lane / 2.5) * _sigmoid(-sum(f["impact"] for f in factors)) * 0.9, factors


def _move(a, b, step: float):
    """From a towards b, at most step metres."""
    d = _dist(a, b)
    if d <= step:
        return [round(b[0], 2), round(b[1], 2)]
    return [round(a[0] + (b[0] - a[0]) * step / d, 2), round(a[1] + (b[1] - a[1]) * step / d, 2)]


def _goal_side(defender: dict, d_pos, puck, share: float = 1.0):
    """Where the defender gets to after the puck moved: towards a point 2.8 m in front of the puck on its way to the net.
    A fast defender gets closer."""
    d = _dist(puck, NET) or 1
    target = (puck[0] + 2.8 * (NET[0] - puck[0]) / d, puck[1] + 2.8 * (NET[1] - puck[1]) / d)
    k = share * (0.35 + 0.4 * defender["traits"]["speed"]["value"] / 100)
    return [round(d_pos[0] + k * (target[0] - d_pos[0]), 2), round(d_pos[1] + k * (target[1] - d_pos[1]), 2)]


def _open_spot(puck):
    """Where the attacker without the puck goes to get open: a bit ahead of the puck, on the other side of the slot."""
    return [_clamp(puck[0] + 3, 10, 20.5), -4.5 if puck[1] >= 0 else 4.5]


def _skate_target(skater: dict, pos):
    gain = 3.5 + 4 * skater["traits"]["speed"]["value"] / 100
    return [round(min(pos[0] + gain, SKATE_X_MAX), 2), round(pos[1] * 0.55, 2)]


def _goalie_spot(puck):
    return [NET[0] - 0.9, round(_clamp(puck[1] * 0.12, -1.0, 1.0), 2)]


def _mate(holder: str) -> str:
    return "A2" if holder == "A1" else "A1"


def _speed(p: dict) -> float:
    return p["traits"]["speed"]["value"] / 100


def _after_skate(p: dict, state: dict, holder: str) -> dict:
    """The positions after the holder skated in: the teammate gets open, the defender stays goal side."""
    target = _skate_target(p[holder], state[holder])
    new = {**state, holder: target, "puck": target, "G": _goalie_spot(target)}
    mate = _mate(holder)
    if p.get(mate):
        new[mate] = _move(state[mate], _open_spot(target), 3 + 4 * _speed(p[mate]))
    if p.get("D"):
        new["D"] = _goal_side(p["D"], state["D"], target)
    return new


def _after_pass(p: dict, state: dict, holder: str) -> dict:
    """The positions after a pass: the passer moves on into space, the defender shifts towards the receiver."""
    receiver = state[_mate(holder)]
    new = {**state, holder: _move(state[holder], _open_spot(receiver), 2.5), "puck": list(receiver),
           "G": _goalie_spot(receiver)}
    if p.get("D"):
        new["D"] = _goal_side(p["D"], state["D"], receiver, 0.6)
    return new


def _shot_risks(p: dict, state: dict, holder: str, after_pass: bool):
    blocked, block_factors = block_chance(p.get("D"), state.get("D"), state[holder])
    chance, factors = shot_chance(p[holder], p["G"], state[holder], p[_mate(holder)] if after_pass else None)
    return blocked, block_factors, chance, factors


def _continuations(p: dict, state: dict, holder: str) -> list[tuple]:
    """(kind, risk, factors, next state, next holder, after a pass) for skating in and passing."""
    moves = []
    if state[holder][0] < SKATE_X_MAX - 0.5:
        target = _skate_target(p[holder], state[holder])
        risk, factors = battle_chance(p[holder], p.get("D"), state.get("D"), state[holder], target)
        moves.append(("skate", risk, factors, _after_skate(p, state, holder), holder, False))
    mate = _mate(holder)
    if p.get(mate):
        risk, factors = pass_chance(p[holder], p.get("D"), state.get("D"), state[holder], state[mate])
        moves.append(("pass", risk, factors, _after_pass(p, state, holder), mate, True))
    return moves


def _value(p: dict, state: dict, holder: str, left: int, after_pass: bool, depth: int = 2) -> float:
    """Expected goals of the best way to play on from here, looking depth moves ahead."""
    blocked, _, chance, _ = _shot_risks(p, state, holder, after_pass)
    best = (1 - blocked) * chance
    if left > 1 and depth > 0:
        for _, risk, _, nxt, nholder, npass in _continuations(p, state, holder):
            best = max(best, (1 - risk) * _value(p, nxt, nholder, left - 1, npass, depth - 1))
    return best


def _choose(options: list[tuple[str, float]], rng: random.Random) -> str:
    """Mostly the best option, sometimes another: players don't always read a play right."""
    weights = [math.exp(value / 0.03) for _, value in options]
    return rng.choices([kind for kind, _ in options], weights=weights)[0]


def _players(attack: dict, defense: dict) -> dict:
    return {"A1": attack["carrier"], "A2": attack.get("support"), "D": defense.get("defender"), "G": defense["goalie"]}


def _why(kind: str, chance: float, base: float, factors: list[dict], context: list[str], headline: str,
         goal_for_attack: bool) -> dict:
    """The explanation of the decisive moment: what happened, the chance it had, the same chance with average players,
    the biggest reasons (traits that moved it most), and whether luck played a part."""
    reasons = sorted((f for f in factors if abs(f["impact"]) >= 0.15), key=lambda f: -abs(f["impact"]))[:3]
    luck = None
    if goal_for_attack and chance < 0.3:
        luck = f"It was only a {round(chance * 100)}% chance, so the attack had some luck."
    elif not goal_for_attack and chance >= 0.5:
        luck = f"It was a {round(chance * 100)}% chance, so the defence had some luck."
    label = {"shot": "Goal chance", "block": "Chance of a block", "battle": "Chance to lose the puck",
             "interception": "Chance of an interception"}[kind]
    return {"kind": kind, "headline": headline, "chance": {"label": label, "value": chance}, "base": base,
            "context": context, "reasons": reasons, "luck": luck}


def simulate(scenario: dict, attack: dict, defense: dict, rng: random.Random) -> dict:
    """Plays one attack. attack: {'carrier', 'support'?} and defense: {'goalie', 'defender'?} are profiles. Returns the
    keyframes for the animation (positions in metres, attack towards +x), the steps with their chances and the traits
    behind them, the explanation of the decisive moment ('why') and the outcome."""
    p = _players(attack, defense)
    avg = {k: (AVERAGE["goalie"] if k == "G" else AVERAGE["skater"]) if v else None for k, v in p.items()}
    state = {"A1": list(scenario["carrier"]), "puck": list(scenario["carrier"])}
    if p["A2"]:
        state["A2"] = list(scenario["support"])
    if p["D"]:
        state["D"] = list(scenario["defender"])
    state["G"] = _goalie_spot(state["puck"])
    frames, steps = [], []

    def frame(caption: str, ms: int, **extra):
        frames.append({"positions": {k: list(v) for k, v in state.items()}, "caption": caption, "ms": ms, **extra})

    def step(text: str, chance: dict | None, factors: list[dict], outcome: str | None = None):
        steps.append({"text": text, "chance": chance, "factors": factors, "outcome": outcome})

    def end(goal: bool, ending: str, why: dict, caption: str):
        frame(caption, 1400, outcome="goal" if goal else "stopped")
        return {"goal": goal, "ending": ending, "frames": frames, "steps": steps, "why": why, "summary": why["headline"]}

    frame(f"{p['A1']['name']} carries the puck in", 900)
    holder, after_pass, left = "A1", False, MAX_ACTIONS
    while True:
        player = p[holder]
        moves = _continuations(p, state, holder) if left > 1 else []
        blocked, block_factors, chance, shot_factors = _shot_risks(p, state, holder, after_pass)
        options = [("shoot", (1 - blocked) * chance)] + [
            (kind, (1 - risk) * _value(p, nxt, nh, left - 1, npass)) for kind, risk, _, nxt, nh, npass in moves]
        kind = _choose(options, rng)
        left -= 1
        if kind == "shoot":
            at = state[holder]
            distance = _dist(at, NET)
            shot = "one-timer" if after_pass else "shot"
            rng_word = "close range" if distance < CLOSE_RANGE else "long range"
            context = [f"The {shot} came from {distance:.0f} m, which counts as {rng_word}: "
                       + ("finishing in close and close-range saves decide." if distance < CLOSE_RANGE
                          else "long-range shooting, shot power and long-range saves decide.")]
            if after_pass:
                context.append(f"It came right after {p[_mate(holder)]['name']}'s pass, so the goalie had to move across.")
            if blocked and rng.random() < blocked:
                state["puck"] = list(state["D"])
                base = block_chance(avg["D"], state["D"], at)[0]
                step(f"{player['name']} shoots from {distance:.0f} m, but {p['D']['name']} is in the lane.",
                     {"label": "Chance of a block", "value": blocked}, block_factors, "blocked")
                return end(False, "block", _why("block", blocked, base, block_factors,
                                                [f"{p['D']['name']} stood in the shooting lane."],
                                                f"{p['D']['name']} blocked {player['name']}'s {shot}.", False),
                           f"Blocked by {p['D']['name']}")
            if blocked:
                step(f"{p['D']['name']} is in the shooting lane but can't block it.",
                     {"label": "Chance of a block", "value": blocked}, block_factors, "through")
            goal = rng.random() < chance
            base = shot_chance(avg[holder], avg["G"], at, avg[_mate(holder)] if after_pass else None)[0]
            step(f"{shot.capitalize()} by {player['name']} from {distance:.0f} m.",
                 {"label": "Goal chance", "value": chance}, shot_factors, "goal" if goal else "saved")
            state["puck"] = [NET[0] + 0.6, round(rng.uniform(-0.7, 0.7), 2)] if goal else list(state["G"])
            headline = (f"{player['name']} scored with a {shot} from {distance:.0f} m." if goal
                        else f"{p['G']['name']} saved {player['name']}'s {shot} from {distance:.0f} m.")
            why = _why("shot", chance, base, shot_factors, context, headline, goal)
            return end(goal, "goal" if goal else "save", why, "GOAL!" if goal else f"Saved by {p['G']['name']}")
        _, risk, factors, nxt, nholder, npass = next(m for m in moves if m[0] == kind)
        if kind == "skate":
            target = nxt[holder]
            if risk and rng.random() < risk:
                start = state[holder]
                spot = [round((start[0] + target[0]) / 2, 2), round((start[1] + target[1]) / 2, 2)]
                base = battle_chance(avg[holder], avg["D"], state["D"], start, target)[0]
                state = {**nxt, holder: spot, "puck": list(nxt["D"]), "G": _goalie_spot(spot)}
                step(f"{player['name']} skates in and {p['D']['name']} steps up.",
                     {"label": "Chance to lose the puck", "value": risk}, factors, "lost")
                return end(False, "battle", _why("battle", risk, base, factors,
                                                 [f"{p['D']['name']} could reach {player['name']}'s skating path."],
                                                 f"{p['D']['name']} took the puck off {player['name']}.", False),
                           f"{p['D']['name']} wins the puck")
            state = nxt
            step(f"{player['name']} skates in" + (f", past {p['D']['name']}." if risk else "."),
                 {"label": "Chance to lose the puck", "value": risk} if risk else None, factors if risk else [],
                 "kept" if risk else None)
            frame(f"{player['name']} skates in", 1000)
            after_pass = False
            continue
        receiver = p[nholder]
        if risk and rng.random() < risk:
            start, target = state[holder], state[nholder]
            _, t = _segment(state["D"], start, target)
            spot = [round(start[0] + t * (target[0] - start[0]), 2), round(start[1] + t * (target[1] - start[1]), 2)]
            base = pass_chance(avg[holder], avg["D"], state["D"], start, target)[0]
            state = {**state, "D": spot, "puck": list(spot)}
            step(f"{player['name']} passes to {receiver['name']}, but {p['D']['name']} reads it.",
                 {"label": "Chance of an interception", "value": risk}, factors, "lost")
            return end(False, "interception", _why("interception", risk, base, factors,
                                                   [f"{p['D']['name']} was close to the passing lane."],
                                                   f"{p['D']['name']} intercepted {player['name']}'s pass.", False),
                       f"Intercepted by {p['D']['name']}")
        state = nxt
        step(f"{player['name']} passes to {receiver['name']}.",
             {"label": "Chance of an interception", "value": risk} if risk else None, factors if risk else [],
             "through" if risk else None)
        frame(f"Pass to {receiver['name']}", 800)
        holder, after_pass = nholder, True


# Duel


def slots(mode: str, attacking: bool) -> list[str]:
    if attacking:
        return ["carrier", "support"] if mode == "2v2" else ["carrier"]
    return ["goalie", "defender"] if mode == "2v2" else ["goalie"]


def new_duel(mode: str, rng: random.Random, available: set[str] | None = None) -> dict:
    duel = {
        "mode": mode, "round": 1, "attacker": "you", "score": {"you": 0, "bot": 0}, "attempts": {"you": 0, "bot": 0},
        "scouted": [], "history": [], "finished": False, "winner": None, "seen": [],
    }
    start_turn(duel, rng, available)
    return duel


def start_turn(duel: dict, rng: random.Random, available: set[str] | None = None):
    """A new zone entry. When the bot defends, it commits its goalie (and defender) now, before the user picks."""
    seen = duel.setdefault("seen", [])  # duels saved before zone entries have no list yet
    index, duel["scenario"] = get_shootout().scenario(duel["mode"], rng, seen)
    seen.append(index)
    duel["bot_picks"] = bot_defend(duel, rng, available) if duel["attacker"] == "you" else None


def bot_pool(role: str, exclude: set[tuple] = frozenset(), available: set[str] | None = None) -> list[str]:
    """The cards the bot picks from: only players with real data, one card per player, none of the excluded players
    (those the user plays this turn). The bot is not limited to a collection: it can pick any card that exists at this
    state of the tournament (available), or any card when that is None."""
    def pick(real_only: bool) -> list[str]:
        pool = {}
        for p in get_shootout().profiles.values():
            if (p["real"] or not real_only) and p["role"] == role and p["who"] not in exclude \
                    and (available is None or p["card_id"] in available):
                pool.setdefault(p["who"], p["card_id"])
        return list(pool.values())

    # Before the final is played there are no real-data cards yet: then the bot plays whatever exists.
    return pick(True) or pick(False)


def _noisy(rng: random.Random, value: float, spread: float) -> float:
    return value + rng.gauss(0, spread)


def bot_defend(duel: dict, rng: random.Random, available: set[str] | None = None) -> dict:
    """The bot's goalie (and defender), picked without knowing the attackers."""
    profiles = get_shootout().profiles
    lateral = 0.3 if duel["mode"] == "2v2" else 0.0

    def goalie_score(cid):
        t = profiles[cid]["traits"]
        return _noisy(rng, (t["close"]["value"] + t["long"]["value"]) / 2 + t["lateral"]["value"] * lateral, 12)

    picks = {"goalie": max(bot_pool("goalie", available=available), key=goalie_score)}
    if duel["mode"] == "2v2":
        def defender_score(cid):
            t = profiles[cid]["traits"]
            return _noisy(rng, t["blocking"]["value"] * 0.35 + t["battles"]["value"] * 0.3
                          + t["reading"]["value"] * 0.3 + t["speed"]["value"] * 0.2, 12)
        picks["defender"] = max(bot_pool("skater", available=available), key=defender_score)
    return picks


def bot_attack(duel: dict, defense: dict, rng: random.Random, available: set[str] | None = None,
               profiles: dict | None = None) -> dict:
    """The bot's attackers, picked after it has seen who defends: it tries the line-ups and keeps the one that looks
    best, with noise so it can be outplayed."""
    profiles = profiles or get_shootout().profiles
    free = bot_pool("skater", {profiles[cid]["who"] for cid in defense.values()}, available)
    scenario = duel["scenario"]
    state = {"A1": scenario["carrier"], "G": _goalie_spot(scenario["carrier"])}
    if duel["mode"] == "2v2":
        state |= {"A2": scenario["support"], "D": scenario["defender"]}
        lineups = [{"carrier": a, "support": b} for a in free for b in free if a != b]
    else:
        lineups = [{"carrier": a} for a in free]
    defense_profiles = {slot: profiles[cid] for slot, cid in defense.items()}

    def value(lineup):
        p = _players({slot: profiles[cid] for slot, cid in lineup.items()}, defense_profiles)
        return _noisy(rng, _value(p, state, "A1", MAX_ACTIONS, False), 0.06)

    return max(lineups, key=value)


def play_turn(duel: dict, picks: dict, rng: random.Random, available: set[str] | None = None,
              profiles: dict | None = None) -> dict:
    """The user's picks for the current turn (slot -> card id, already validated against their collection). Plays it,
    records it and moves the duel on. The bot picks from the cards available at this state of the tournament. Returns
    the simulation result. profiles are those of the user's stage (see Shootout.at)."""
    profiles = profiles or get_shootout().profiles
    you_attack = duel["attacker"] == "you"
    if you_attack:
        attack_ids, defense_ids = picks, duel["bot_picks"]
    else:
        defense_ids = picks
        attack_ids = bot_attack(duel, picks, rng, available, profiles)
    attacker = duel["attacker"]
    result = simulate(duel["scenario"], {s: profiles[c] for s, c in attack_ids.items()},
                      {s: profiles[c] for s, c in defense_ids.items()}, rng)
    bot_ids = defense_ids if you_attack else attack_ids
    duel["scouted"] = list(dict.fromkeys(duel["scouted"] + list(bot_ids.values())))
    duel["attempts"][attacker] += 1
    duel["score"][attacker] += result["goal"]
    entry = {"round": duel["round"], "attacker": attacker, "goal": result["goal"], "summary": result["summary"],
             "attack": attack_ids, "defense": defense_ids, "scenario": duel["scenario"]}
    duel["history"].append(entry)
    _advance(duel, rng, available)
    return {**result, "attacker": attacker, "attack": attack_ids, "defense": defense_ids}


def _advance(duel: dict, rng: random.Random, available: set[str] | None = None):
    """Next turn, or the end: in regulation as soon as one side cannot catch up, in sudden death after a round with
    different results. After MAX_ROUNDS still level it is a draw."""
    score, attempts, r = duel["score"], duel["attempts"], duel["round"]
    if r <= REGULATION_ROUNDS:
        left = {side: REGULATION_ROUNDS - attempts[side] for side in score}
        if score["you"] > score["bot"] + left["bot"] or score["bot"] > score["you"] + left["you"]:
            return _finish(duel)
    if attempts["you"] == attempts["bot"]:
        if r >= REGULATION_ROUNDS and score["you"] != score["bot"]:
            return _finish(duel)
        if r >= MAX_ROUNDS:
            return _finish(duel)
        duel["round"] += 1
        duel["attacker"] = "you"
    else:
        duel["attacker"] = "bot"
    start_turn(duel, rng, available)


def _finish(duel: dict):
    duel["finished"] = True
    duel["scenario"] = None
    duel["bot_picks"] = None
    you, bot = duel["score"]["you"], duel["score"]["bot"]
    duel["winner"] = "you" if you > bot else "bot" if bot > you else None
