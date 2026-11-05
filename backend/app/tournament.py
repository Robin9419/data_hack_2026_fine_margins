"""The tournament timeline: the demo simulates the 2025 Spengler Cup day by day.

A user is always at one stage: before the tournament, on one of the gamedays (26 to 31 December) or after it. On a
gameday that day's games are still to be played: the user predicts three things per game (the winner, a goal question
and a KPI question; the last two rotate from game to game). Moving on in the timeline plays the games: the predictions are resolved and every correct one earns a
pack. Before the tournament the user predicts the tournament as a whole (champion, top scorer, penalties drawn, overtime
games, total goals); those predictions are resolved with the final. Cards that come from a game (its specials, and for the final the Wisehockey cards) only exist once the game is
played, and the post-game trivia asks about them. The results come from testdata.json (official game pages)."""


from .testdata import TestData, _key, _name

PRE, POST = "pre", "post"
WEEKDAYS = {"2025-12-26": "Fri", "2025-12-27": "Sat", "2025-12-28": "Sun", "2025-12-29": "Mon", "2025-12-30": "Tue",
            "2025-12-31": "Wed"}
SHORT_STAGE = {"Quarterfinal": "Quarter-finals", "Semifinal": "Semi-finals", "Final": "Final"}
PACK_CARDS = 5  # per prediction pack: every card is rolled like a trade-in
SPECIAL_CHANCE = 0.1  # per base-only pack (starter, daily, social, tickets): the chance the last card is a special card
FIRST_GOAL_CANDIDATES = 2  # per team, plus "someone else"
OTHER = "other"


def _team_total(game: dict, team: str, stat: str, goalkeeper: bool) -> int:
    return sum(p["stats"].get(stat) or 0 for p in game["players"] if p["team"] == team and p["goalkeeper"] == goalkeeper)


def _bucket(value: float, buckets: list[tuple[str, str, float]]) -> str:
    """buckets: (id, label, upper bound inclusive); the last bound is infinity."""
    return next(bid for bid, _, upper in buckets if value <= upper)


SHOT_BUCKETS = [("slow", "Under 150 km/h", 149.99), ("mid", "150 to 160 km/h", 160), ("fast", "Over 160 km/h", float("inf"))]
PIM_BUCKETS = [("low", "10 or fewer", 10), ("mid", "11 to 20", 20), ("high", "More than 20", float("inf"))]


def _kpi_top_shot(game: dict):
    top = max((p for p in game["players"] if p["stats"].get("shot_top_speed")), key=lambda p: p["stats"]["shot_top_speed"])
    speed = top["stats"]["shot_top_speed"]
    return {
        "prompt": "How hard will the hardest shot of the game be?",
        "hint": "Every shot's speed is measured. Most games top out around 150 to 160 km/h.",
        "options": [{"id": b, "label": label} for b, label, _ in SHOT_BUCKETS],
        "answer": _bucket(speed, SHOT_BUCKETS),
        "explanation": f"{speed:.1f} km/h by {_name(top)} ({top['team']}).",
    }


def _kpi_busy_period(game: dict):
    goals = [h + a for h, a in game["periods"][:3]]
    best = max(goals)
    answer = "tie" if goals.count(best) > 1 else f"p{goals.index(best) + 1}"
    return {
        "prompt": "Which period will have the most goals?",
        "hint": "Teams often open up in the third period, when the trailing side has to take risks.",
        "options": [{"id": "p1", "label": "1st period"}, {"id": "p2", "label": "2nd period"},
                    {"id": "p3", "label": "3rd period"}, {"id": "tie", "label": "Two periods tie"}],
        "answer": answer,
        "explanation": "Goals per period: " + ", ".join(f"{h}–{a}" for h, a in game["periods"][:3]) + ".",
    }


def _kpi_penalty_minutes(game: dict):
    minutes = sum(p["minutes"] for p in game["penalties"])
    return {
        "prompt": "How many penalty minutes will the referees hand out in total?",
        "hint": "A minor penalty is 2 minutes, a major 5, a misconduct 10.",
        "options": [{"id": b, "label": label} for b, label, _ in PIM_BUCKETS],
        "answer": _bucket(minutes, PIM_BUCKETS),
        "explanation": f'{minutes} penalty minutes from {len(game["penalties"])} penalties.',
    }


def _kpi_power_play_goal(game: dict):
    pp = sum(1 for g in game["goals"] if (g["strength"] or "").startswith("PP"))
    return {
        "prompt": "Will a team score on the power play?",
        "hint": "A power play goal is scored while the other team has a player in the penalty box.",
        "options": [{"id": "yes", "label": "Yes"}, {"id": "no", "label": "No"}],
        "answer": "yes" if pp else "no",
        "explanation": f'{pp} power play {"goal" if pp == 1 else "goals"}.' if pp else "No power play goals.",
    }


def _kpi_busier_goalie(game: dict):
    home, away = game["home_team"], game["away_team"]
    saves = {t: _team_total(game, t, "saves", True) for t in (home, away)}
    if saves[home] == saves[away]:
        return None
    return {
        "prompt": "Whose goalkeeper will be busier and make more saves?",
        "hint": "More saves usually means the other team had more of the puck.",
        "options": [{"id": "home", "label": home, "team": home}, {"id": "away", "label": away, "team": away}],
        "answer": "home" if saves[home] > saves[away] else "away",
        "explanation": f"Saves: {home} {saves[home]}, {away} {saves[away]}.",
    }


def _kpi_more_shots(game: dict):
    home, away = game["home_team"], game["away_team"]
    shots = {t: _team_total(game, t, "shots", False) for t in (home, away)}
    if shots[home] == shots[away]:
        return None
    return {
        "prompt": "Which team will take more shots?",
        "hint": "Counts every shot attempt, on target or not. The team with more shots does not always win.",
        "options": [{"id": "home", "label": home, "team": home}, {"id": "away", "label": away, "team": away}],
        "answer": "home" if shots[home] > shots[away] else "away",
        "explanation": f"Shots: {home} {shots[home]}, {away} {shots[away]}.",
    }


# One KPI question per game, in turn, so every gameday asks something different. A question without a clear answer
# for a game (a tie) is skipped in favour of the next one.
KPI_QUESTIONS = [_kpi_top_shot, _kpi_busy_period, _kpi_penalty_minutes, _kpi_power_play_goal, _kpi_busier_goalie,
                 _kpi_more_shots]


# One goal question per game, in turn like the KPI questions (with a different cycle length, so the pairs vary too).
# The first-scorer question needs the named candidates (see Tournament._first_goal_candidates).

FIRST_GOAL_BUCKETS = [("early", "In the first 5 minutes", 299), ("p1a", "Minute 5 to 10", 599),
                      ("p1b", "Minute 10 to 20", 1199), ("later", "After the 1st period", float("inf"))]
TOTAL_GOAL_BUCKETS = [("low", "4 or fewer", 4), ("mid", "5 or 6", 6), ("high", "7 or 8", 8), ("lots", "9 or more", float("inf"))]
MARGIN_BUCKETS = [("one", "1 goal", 1), ("two", "2 goals", 2), ("more", "3 or more", float("inf"))]
YES_NO = [{"id": "yes", "label": "Yes"}, {"id": "no", "label": "No"}]


def _seconds(clock: str) -> int:
    minutes, seconds = clock.split(":")
    return int(minutes) * 60 + int(seconds)


def _goal_first_scorer(game: dict, candidates: dict[str, list[dict]]):
    home, away = game["home_team"], game["away_team"]
    first = game["goals"][0]
    named = [p for team in (home, away) for p in candidates.get(team, [])]
    scorer = first["scorer"] and (first["team"], first["scorer"]["jersey"])
    return {
        "prompt": "Who will score the first goal?",
        "hint": "The two top scorers of each team at this Spengler Cup, or anyone else.",
        "options": [{"id": f'{p["team"]}#{p["jersey"]}', "label": _name(p), "team": p["team"]} for p in named]
                   + [{"id": OTHER, "label": "Someone else"}],
        "answer": next((f"{k[0]}#{k[1]}" for k in map(_key, named) if k == scorer), OTHER),
        "explanation": f'{_name(first["scorer"]) if first["scorer"] else "Unknown"} ({first["team"]}) at {first["clock"]}.',
    }


def _goal_first_team(game: dict, _):
    home, away = game["home_team"], game["away_team"]
    first = game["goals"][0]
    return {
        "prompt": "Which team will score first?",
        "hint": "The team that scores first wins most hockey games, but not all of them.",
        "options": [{"id": "home", "label": home, "team": home}, {"id": "away", "label": away, "team": away}],
        "answer": "home" if first["team"] == home else "away",
        "explanation": f'{first["team"]} opened the scoring at {first["clock"]}.',
    }


def _goal_first_time(game: dict, _):
    first = game["goals"][0]
    return {
        "prompt": "When will the first goal be scored?",
        "hint": "A period lasts 20 minutes. Some games open fast, others stay goalless for a long time.",
        "options": [{"id": b, "label": label} for b, label, _ in FIRST_GOAL_BUCKETS],
        "answer": _bucket(_seconds(first["clock"]), FIRST_GOAL_BUCKETS),
        "explanation": f'First goal at {first["clock"]} by {first["team"]}.',
    }


def _goal_total(game: dict, _):
    total = game["home_score"] + game["away_score"]
    return {
        "prompt": "How many goals will be scored in total?",
        "hint": "Both teams together. Spengler Cup games often see 5 to 7 goals.",
        "options": [{"id": b, "label": label} for b, label, _ in TOTAL_GOAL_BUCKETS],
        "answer": _bucket(total, TOTAL_GOAL_BUCKETS),
        "explanation": f'{total} goals: {game["home_score"]}–{game["away_score"]}.',
    }


def _goal_margin(game: dict, _):
    margin = abs(game["home_score"] - game["away_score"])
    return {
        "prompt": "By how many goals will the winner win?",
        "hint": "Many games are decided by one goal, often with an empty net at the end.",
        "options": [{"id": b, "label": label} for b, label, _ in MARGIN_BUCKETS],
        "answer": _bucket(margin, MARGIN_BUCKETS),
        "explanation": f'{game["home_score"]}–{game["away_score"]}, a margin of {margin}.',
    }


def _goal_both_score(game: dict, _):
    both = game["home_score"] > 0 and game["away_score"] > 0
    return {
        "prompt": "Will both teams score?",
        "hint": "A shutout means a goalkeeper kept a clean sheet for the whole game.",
        "options": YES_NO,
        "answer": "yes" if both else "no",
        "explanation": f'{game["home_score"]}–{game["away_score"]}.' + ("" if both else " A shutout."),
    }


def _goal_hat_trick(game: dict, _):
    counts: dict[tuple[str, int], list] = {}
    for g in game["goals"]:
        if g["scorer"]:
            counts.setdefault((g["team"], g["scorer"]["jersey"]), [0, g["scorer"], g["team"]])[0] += 1
    hat = [(p, team) for n, p, team in counts.values() if n >= 3]
    return {
        "prompt": "Will anyone score a hat trick?",
        "hint": "A hat trick is three goals by the same player in one game. Fans throw their hats on the ice.",
        "options": YES_NO,
        "answer": "yes" if hat else "no",
        "explanation": (", ".join(f"{_name(p)} ({team})" for p, team in hat) + " scored three.") if hat
                       else "Nobody scored three goals.",
    }


def _goal_late(game: dict, _):
    late = [g for g in game["goals"] if 55 * 60 <= _seconds(g["clock"]) < 60 * 60]
    return {
        "prompt": "Will there be a goal in the last 5 minutes of regulation time?",
        "hint": "Late goals are common: the trailing team pulls its goalkeeper for an extra skater.",
        "options": YES_NO,
        "answer": "yes" if late else "no",
        "explanation": ("Late goals at " + ", ".join(g["clock"] for g in late) + ".") if late
                       else "No goal after 55:00.",
    }


GOAL_QUESTIONS = [_goal_first_scorer, _goal_total, _goal_first_time, _goal_first_team, _goal_margin, _goal_late,
                  _goal_both_score, _goal_hat_trick]


# Tournament predictions: made before the tournament starts (the pre stage), resolved once the final is played. They
# are stored like a game's predictions, under the id OUTLOOK, and every right one earns a pack.
OUTLOOK = "tournament"
TOP_SCORER_CANDIDATES = 2  # per team, plus "someone else"
OVERTIME_BUCKETS = [("0", "None", 0), ("1", "1 game", 1), ("2", "2 games", 2), ("3", "3 games", 3),
                    ("4", "4 or more", float("inf"))]
TOURNAMENT_GOAL_BUCKETS = [("40", "Under 50", 49), ("50", "50 to 59", 59), ("60", "60 to 69", 69),
                           ("70", "70 to 79", 79), ("80", "80 or more", float("inf"))]


def _winner(game: dict) -> str:
    return game["home_team"] if game["home_score"] > game["away_score"] else game["away_team"]


def _scorers(games: list[dict]) -> list[tuple[int, int, dict]]:
    """Every skater's tournament (points, goals, player), best first: the scoring ranking goes by points, then goals."""
    totals: dict[tuple[str, int], list] = {}
    for game in games:
        for p in game["players"]:
            if not p["goalkeeper"]:
                entry = totals.setdefault(_key(p), [0, 0, p])
                entry[0] += p["stats"].get("points") or 0
                entry[1] += p["stats"].get("goals") or 0
    return sorted((tuple(v) for v in totals.values()), key=lambda v: (-v[0], -v[1], v[2]["team"], v[2]["jersey"]))


def _team_options(teams: list[str]) -> list[dict]:
    return [{"id": team, "label": team, "team": team} for team in teams]


def _outlook_questions(games: list[dict]) -> list[dict]:
    final = next(g for g in games if g["stage"] == "Final")
    teams = sorted({g["home_team"] for g in games} | {g["away_team"] for g in games})
    champion = _winner(final)

    scorers = _scorers(games)
    points, goals, top = scorers[0]
    named = []
    for team in teams:
        named += [p for _, _, p in scorers if p["team"] == team][:TOP_SCORER_CANDIDATES]
    top_id = f'{top["team"]}#{top["jersey"]}'
    scorer_options = [{"id": f'{p["team"]}#{p["jersey"]}', "label": _name(p), "team": p["team"]} for p in named]

    # Drawing a penalty: an opponent is sent to the box for a foul on you. A team draws every penalty its opponents take.
    drawn = {team: 0 for team in teams}
    for game in games:
        for pen in game["penalties"]:
            drawn[game["away_team"] if pen["team"] == game["home_team"] else game["home_team"]] += 1
    most_drawn = max(drawn.values())
    drawers = [team for team in teams if drawn[team] == most_drawn]

    overtime = sum(1 for g in games if g["overtime"])
    total = sum(g["home_score"] + g["away_score"] for g in games)
    ranking = sorted(teams, key=lambda t: -drawn[t])
    return [
        {"id": "champion", "prompt": "Who will win the Spengler Cup?",
         "hint": "Six teams, two groups, then quarter-finals, semi-finals and the final on 31 December.",
         "options": _team_options(teams), "answer": champion,
         "explanation": f'{champion} won the final {final["home_score"]}–{final["away_score"]} against '
                        f'{final["away_team"] if champion == final["home_team"] else final["home_team"]}.'},
        {"id": "top_scorer", "prompt": "Who will be the tournament's top scorer?",
         "hint": "The player with the most points (goals plus assists) over the whole tournament. "
                 "Two candidates per team, or anyone else.",
         "options": scorer_options + [{"id": OTHER, "label": "Someone else"}],
         "answer": top_id if top_id in {o["id"] for o in scorer_options} else OTHER,
         "explanation": f'{_name(top)} ({top["team"]}) with {points} points ({goals} goals).'},
        {"id": "penalties_drawn", "prompt": "Which team will draw the most penalties?",
         "hint": "A team draws a penalty when an opponent is sent to the penalty box for a foul against it.",
         # A tie is not expected; should one happen, the first of the tied teams counts.
         "options": _team_options(teams), "answer": drawers[0],
         "explanation": "Penalties drawn: " + ", ".join(f"{t} {drawn[t]}" for t in ranking) + "."},
        {"id": "overtime", "prompt": "How many games will go to overtime?",
         "hint": f"A game tied after 60 minutes goes to overtime, then to a shootout. {len(games)} games in total.",
         "options": [{"id": b, "label": label} for b, label, _ in OVERTIME_BUCKETS],
         "answer": _bucket(overtime, OVERTIME_BUCKETS),
         "explanation": f'{overtime} of {len(games)} games went to overtime.' if overtime
                        else f"All {len(games)} games were decided in regulation time."},
        {"id": "total_goals", "prompt": "How many goals will be scored in the whole tournament?",
         "hint": f"All {len(games)} games together. A Spengler Cup game usually sees 5 to 7 goals.",
         "options": [{"id": b, "label": label} for b, label, _ in TOURNAMENT_GOAL_BUCKETS],
         "answer": _bucket(total, TOURNAMENT_GOAL_BUCKETS),
         "explanation": f"{total} goals in {len(games)} games, {total / len(games):.1f} per game."},
    ]


class Tournament:
    def __init__(self, testdata: TestData):
        self.games = testdata.games
        self.by_id = testdata.by_id
        self.days = sorted({g["date"] for g in self.games})
        self.stages = [PRE, *self.days, POST]
        self.final = next(g for g in self.games if g["stage"] == "Final")
        self._candidates = self._first_goal_candidates()
        self.questions = {g["id"]: self._questions(g, i) for i, g in enumerate(self.games)}
        self.questions[OUTLOOK] = _outlook_questions(self.games)
        # The tournament predictions as a round of their own, shown like a game without teams.
        first = self.games[0]
        self.outlook = {"id": OUTLOOK, "kind": "outlook", "date": first["date"], "start": first["start"],
                        "stage": "Tournament", "arena": first["arena"], "home_team": None, "away_team": None}

    # Stages

    def played(self, stage: str) -> set[str]:
        """Ids of the games already played at this stage: those before the gameday, all of them after the tournament."""
        if stage == POST:
            return {g["id"] for g in self.games}
        return {g["id"] for g in self.games if stage != PRE and g["date"] < stage}

    def resolved(self, stage: str) -> set[str]:
        """Ids of the prediction rounds decided at this stage: the games played, plus the tournament predictions once
        the final is played."""
        played = self.played(stage)
        return played | {OUTLOOK} if self.final["id"] in played else played

    def today(self, stage: str) -> list[dict]:
        return [g for g in self.games if g["date"] == stage]

    def rounds(self, stage: str) -> list[dict]:
        """The prediction rounds open at this stage: the tournament predictions before the tournament, else the
        gameday's games."""
        return [self.outlook] if stage == PRE else self.today(stage)

    def round_by_id(self, round_id: str) -> dict | None:
        return self.outlook if round_id == OUTLOOK else self.by_id.get(round_id)

    def timeline(self) -> list[dict]:
        stops = [{"id": PRE, "label": "Pre", "sub": "Before", "games": 0}]
        for day in self.days:
            games = self.today(day)
            stages = {g["stage"] for g in games}
            sub = SHORT_STAGE.get(next(iter(stages)), "Groups") if len(stages) == 1 else "Groups"
            stops.append({"id": day, "label": f"{WEEKDAYS.get(day, '')} {int(day[8:])}", "sub": sub,
                          "games": len(games)})
        stops.append({"id": POST, "label": "Post", "sub": "After", "games": 0})
        return stops

    # Predictions

    def _first_goal_candidates(self) -> dict[str, list[dict]]:
        """The two top goal scorers of each team over the tournament, as the named first-goal options."""
        totals: dict[tuple[str, int], list] = {}
        for game in self.games:
            for p in game["players"]:
                if not p["goalkeeper"]:
                    entry = totals.setdefault(_key(p), [0, 0, p])
                    entry[0] += p["stats"].get("goals") or 0
                    entry[1] += p["stats"].get("points") or 0
        by_team: dict[str, list[dict]] = {}
        for key, (goals, points, p) in sorted(totals.items(), key=lambda kv: (-kv[1][0], -kv[1][1], kv[0][1])):
            if len(by_team.setdefault(key[0], [])) < FIRST_GOAL_CANDIDATES:
                by_team[key[0]].append(p)
        return by_team

    def _questions(self, game: dict, index: int) -> list[dict]:
        home, away = game["home_team"], game["away_team"]
        home_wins = game["home_score"] > game["away_score"]
        result = f'{home} {game["home_score"]}–{game["away_score"]} {away}' + (" after overtime" if game["overtime"] else "")
        winner = {
            "id": "winner", "prompt": "Who will win?",
            "hint": "There are no draws: a tied game goes to overtime and a shootout.",
            "options": [{"id": "home", "label": home, "team": home}, {"id": "away", "label": away, "team": away}],
            "answer": "home" if home_wins else "away", "explanation": f"{result}.",
        }

        goal = GOAL_QUESTIONS[index % len(GOAL_QUESTIONS)](game, self._candidates)
        for offset in range(len(KPI_QUESTIONS)):
            kpi = KPI_QUESTIONS[(index + offset) % len(KPI_QUESTIONS)](game)
            if kpi:
                break
        return [winner, {"id": "goal", **goal}, {"id": "kpi", **kpi}]

    def answer_of(self, game_id: str, question_id: str) -> str | None:
        return next((q["answer"] for q in self.questions[game_id] if q["id"] == question_id), None)

    def correct_count(self, game_id: str, predictions: dict[str, str]) -> int:
        return sum(predictions.get(q["id"]) == q["answer"] for q in self.questions[game_id])

    def game_view(self, game: dict, played: bool, predictions: dict[str, str], pack: dict | None) -> dict:
        """What the gameday panel shows for a game (or the tournament predictions). Results and right answers only once
        the game is played."""
        keys = ("id", "date", "start", "stage", "arena", "home_team", "away_team")
        view = {k: game[k] for k in keys} | {"kind": game.get("kind", "game")}
        questions = []
        for q in self.questions[game["id"]]:
            shown = {k: q[k] for k in ("id", "prompt", "hint", "options")}
            shown["prediction"] = predictions.get(q["id"])
            if played:
                shown |= {"answer": q["answer"], "explanation": q["explanation"]}
            questions.append(shown)
        view["questions"] = questions
        view["played"] = played
        view["locked"] = pack is not None  # resolved: predictions can no longer change
        if played:
            if game["id"] != OUTLOOK:
                view |= {"home_score": game["home_score"], "away_score": game["away_score"], "overtime": game["overtime"]}
            view["correct"] = self.correct_count(game["id"], predictions)
            view["packs"] = view["correct"]
            view["packs_claimed"] = bool(pack and pack["claimed"])
        return view

