"""Turns the Wisehockey match events CSV into a timeline of moments per player
(goals, assists, shots, saves, faceoff wins) and links each one to video: a clip
cut from the full-game arena recording (`clip`) and, for goals, the matching
stretch of the official broadcast highlights on YouTube (`broadcast`). So the
numbers on a card can be traced back to single events and watched."""

from collections import defaultdict

PERIOD_SECONDS = 20 * 60

SHOT_RESULTS = {"Saved": "saved", "Missed": "missed the net", "Blocked": "blocked"}
ORDINALS = {1: "1st", 2: "2nd", 3: "3rd"}


# Which clip window (videos.json -> recording.windows) each kind of moment uses.
CLIP_WINDOWS = {"goal": "goal", "assist": "goal", "goal_against": "goal", "faceoff_win": "faceoff"}


def clip_window_kind(moment_kind: str) -> str:
    return CLIP_WINDOWS.get(moment_kind, "shot")


def _clock(seconds: int) -> str:
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes}:{seconds:02d}"


def _number(raw: str):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


class MatchEvents:
    def __init__(self, rows: list[dict], sides: dict[str, str], videos: list[dict], camera_clip=lambda ts: None):
        self.rows = rows
        self.camera_clip = camera_clip  # event Timestamp -> clip cut from the recording, or None
        self.sides = sides  # "Home"/"Away" -> team name
        self.names: dict[str, str] = {}  # player id -> "#19 Adam Tambellini"
        self.ids: dict[tuple[str, int], str] = {}  # (team, jersey) -> player id
        for r in rows:
            for role in ("Primary", "Secondary"):
                pid, name = r[f"Event{role}PlayerId"], r[f"Event{role}PlayerName"]
                if pid and name:
                    self.names[pid] = name
                    self.ids[(sides[r[f"Event{role}Team"]], int(name.split(" ", 1)[0].lstrip("#")))] = pid
        self.clips = self._load_clips(videos)
        self.by_player = self._build_moments()

    def _load_clips(self, videos: list[dict]) -> dict[tuple[int, int], dict]:
        """(period, match clock of the Goal event) -> clip. Fails fast if a clip names a goal
        that is not in the data, so a typo cannot silently attach footage to the wrong moment."""
        goals = {(int(r["Period"]), int(r["MatchClock"])) for r in self.rows if r["EventType"] == "Goal"}
        clips = {}
        for video in videos:
            for clip in video["clips"]:
                key = (clip["period"], clip["match_clock"])
                if key not in goals:
                    raise ValueError(f'Clip in {video["id"]} points to no goal: period {key[0]}, clock {key[1]}')
                clips[key] = {"video_id": video["id"], "youtube_id": video["youtube_id"], "start": clip["start"], "end": clip["end"]}
        return clips

    def player_id(self, team: str, jersey: int) -> str | None:
        return self.ids.get((team, jersey))

    def moments(self, player_id: str | None) -> list[dict]:
        return self.by_player.get(player_id, [])

    def _strength(self, r: dict, side: str) -> str | None:
        """Power play / short-handed / empty net, seen from the team on `side`."""
        other = "Away" if side == "Home" else "Home"
        if r[f"{other}GoalieOnIce"] == "FALSE":
            return "Empty net"
        if not r["TeamStrength"]:
            return None
        home, away = (int(n) for n in r["TeamStrength"].split("v"))
        own, opp = (home, away) if side == "Home" else (away, home)
        if own > opp:
            return "Power play"
        if own < opp:
            return "Short-handed"
        return None

    def _moment(self, r: dict, kind: str, title: str, text: str = "", facts=(), shot: dict | None = None, broadcast=None) -> dict:
        period, clock = int(r["Period"]), int(r["MatchClock"])
        speed = _number(shot["ShotSpeed"]) if shot else None
        xg = _number(shot["ShotXG"]) if shot else None
        shot_facts = []
        if xg is not None:
            shot_facts.append(f"xG {xg:.2f}")
        if speed:  # 0 means the speed was not measured
            shot_facts.append(f"{speed:.1f} km/h")
        return {
            "id": f'{r["Timestamp"]}-{kind}',
            "timestamp": r["Timestamp"],
            "kind": kind,
            "period": period,
            "period_label": f"{ORDINALS.get(period, period)} period",
            "clock": _clock(clock),
            "game_time": _clock((period - 1) * PERIOD_SECONDS + clock),
            "title": title,
            "text": text,
            "facts": shot_facts + [f for f in facts if f],
            "shot_speed": speed or None,
            "xg": xg,
            "clip": self.camera_clip(r["Timestamp"]),
            "broadcast": broadcast,
        }

    def _build_moments(self) -> dict[str, list[dict]]:
        by_player = defaultdict(list)
        score = {"Home": 0, "Away": 0}
        goal_shot = None  # the Shot row of a goal; the Goal row that follows carries the assists
        for r in self.rows:
            kind = r["EventType"]
            if kind == "Shot":
                shooter, goalie, result = r["EventPrimaryPlayerId"], r["EventSecondaryPlayerId"], r["ShotResult"]
                side = r["EventPrimaryTeam"]
                if result == "Goal":
                    goal_shot = r
                    continue
                by_player[shooter].append(
                    self._moment(r, "shot", "Shot", SHOT_RESULTS.get(result, result).capitalize(), [self._strength(r, side)], shot=r)
                )
                if goalie:
                    shooter_name = self.names.get(shooter, "unknown")
                    if result == "Saved":
                        by_player[goalie].append(self._moment(r, "save", "Save", f"Stopped {shooter_name}", shot=r))
                    else:
                        text = f"{shooter_name}, {SHOT_RESULTS.get(result, result)}"
                        by_player[goalie].append(self._moment(r, "shot_against", "Shot attempt against", text, shot=r))
            elif kind == "Goal":
                scorer, side = r["EventPrimaryPlayerId"], r["EventPrimaryTeam"]
                score[side] += 1
                shot = goal_shot if goal_shot and goal_shot["EventPrimaryPlayerId"] == scorer else None
                broadcast = self.clips.get((int(r["Period"]), int(r["MatchClock"])))
                assists = [pid for pid in (r["GoalAssist1Id"], r["GoalAssist2Id"]) if pid]
                score_text = f'Score {score["Home"]}–{score["Away"]}'
                strength = self._strength(r, side)
                assist_text = (
                    "Assisted by " + " and ".join(self.names.get(a, "unknown") for a in assists) if assists else "Unassisted"
                )
                by_player[scorer].append(
                    self._moment(r, "goal", "Goal", f"{assist_text}. {score_text}.", [strength], shot=shot, broadcast=broadcast)
                )
                for n, pid in enumerate(assists, 1):
                    which = "Primary" if n == 1 else "Secondary"
                    text = f"{which} assist on the goal by {self.names.get(scorer, 'unknown')}. {score_text}."
                    by_player[pid].append(self._moment(r, "assist", "Assist", text, [strength], broadcast=broadcast))
                goalie = shot["EventSecondaryPlayerId"] if shot else None
                if goalie:
                    text = f"Scored by {self.names.get(scorer, 'unknown')}. {score_text}."
                    by_player[goalie].append(self._moment(r, "goal_against", "Goal against", text, shot=shot, broadcast=broadcast))
                goal_shot = None
            elif kind == "Faceoff" and r["EventPrimaryPlayerId"]:
                zone = r["EventPosition"]
                if zone in ("HomeTeamZone", "AwayTeamZone"):
                    own = (zone == "HomeTeamZone") == (r["EventPrimaryTeam"] == "Home")
                    where = "in the defensive zone" if own else "in the offensive zone"
                else:
                    where = "in the neutral zone"
                by_player[r["EventPrimaryPlayerId"]].append(self._moment(r, "faceoff_win", "Faceoff won", f"Won the draw {where}"))
        return dict(by_player)

    @staticmethod
    def select(moments: list[dict], kinds: list[str]) -> list[str]:
        """Ids of the moments behind a metric. 'hardest_shot' picks the single fastest measured shot."""
        ids = []
        for kind in kinds:
            if kind == "hardest_shot":
                shots = [m for m in moments if m["kind"] in ("goal", "shot") and m["shot_speed"]]
                if shots:
                    ids.append(max(shots, key=lambda m: m["shot_speed"])["id"])
            else:
                ids += [m["id"] for m in moments if m["kind"] == kind]
        return ids
