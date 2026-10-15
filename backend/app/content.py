"""Loads the static content (metrics, match, cards, videos) and joins it with the
Wisehockey match statistics and events CSVs so card values always come from the data."""

import csv
import json
from functools import lru_cache
from pathlib import Path

from .events import MatchEvents
from .event_kpis import EventAnalysis, pass_body_pressure

ROOT = Path(__file__).resolve().parents[2]
CONTENT_DIR = ROOT / "backend" / "content"
DATA_DIR = ROOT / "data"
PLAYER_IMAGES_FILE = ROOT / "docs" / "player-images.json"
MEDIA_DIR = ROOT / "backend" / "media"  # served at /api/media; not in git
CLIPS_DIR = MEDIA_DIR / "clips"  # filled by scripts/cut_clips.py


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
        self.archetype_metrics = {k: v for k, v in cards_doc["archetype_metrics"].items() if not k.startswith("_")}
        rewards_doc = _load_json("rewards.json")
        self.card_points = rewards_doc["card_points"]
        self.rewards = rewards_doc["rewards"]
        videos_doc = _load_json("videos.json")
        self.videos = {v["id"]: v for v in videos_doc["videos"]}
        self.recording = videos_doc.get("recording")
        self.rows = self._load_stats()
        self.event_rows = self._load_events()
        self.events = MatchEvents(
            self.event_rows,
            {"Home": self.match["home_team"], "Away": self.match["away_team"]},
            list(self.videos.values()),
            self._camera_clip,
        )
        self.goalie_rows = self._load_goalie_stats()
        goalkeeper_ids = {r['EventSecondaryPlayerId'] for r in self.event_rows
                          if r['EventType'] == 'Shot' and r['EventSecondaryPlayerId']}
        self.analysis = EventAnalysis(self.event_rows, goalkeeper_ids)
        self.derived_kpis = {'pass_body_pressure': pass_body_pressure(self.analysis)}
        self._add_pass_moments()
        self.player_images = self._load_player_images()
        self.cards = {c["id"]: self._build_card(c) for c in cards_doc["cards"]}
        self._add_pressure_card()
        base_doc = _load_json("base_cards.json")
        self.cards |= {c["id"]: self._build_base_card(c, base_doc) for c in base_doc["cards"]}

    def _add_pass_moments(self):
        for result in self.derived_kpis['pass_body_pressure']['events']:
            if result['value'] is None:
                continue
            row = self.event_rows[result['source_row'] - 1]
            moment = self.events._moment(
                row, 'pass_pressure', 'Pressure-reducing pass' if result['value'] > 0 else 'Successful pass',
                f"To {self.events.names.get(result['receiver_id'], 'receiver')}. "
                f"PBP {result['value']:+d}: {result['pbp_pg']} → {result['pbp_pe']} opposing skaters.")
            moment.update(id=result['id'], kpi=result)
            self.events.by_player.setdefault(result['passer_id'], []).append(moment)
        for moments in self.events.by_player.values():
            moments.sort(key=lambda m: (int(m['timestamp']), m['id']))

    def _add_pressure_card(self):
        candidates = [(pid, stats) for pid, stats in self.derived_kpis['pass_body_pressure']['players'].items()
                      if stats['ranking_eligible'] and stats['mean'] > 0]
        if not candidates:
            return
        # Deterministic tie break: more evaluated passes, then player ID.
        pid, stats = max(candidates, key=lambda item: (item[1]['mean'], item[1]['evaluated_passes'], item[0]))
        team, jersey = next(key for key, value in self.events.ids.items() if value == pid)
        self.archetypes['Pressure Reliever'] = ('Highest average reduction in nearby opposing skaters through successful passes, '
                                               'with at least 10 evaluated passes. Snapshot-based estimate.')
        self.archetype_metrics['Pressure Reliever'] = ['pbp_mean', 'pbp_positive_share', 'pbp_evaluated']
        cfg = {'id': 'pressure-reliever', 'team': team, 'jersey': jersey, 'position': 'Skater',
               'title': 'Pressure Reliever', 'attributes': ['pbp_mean', 'pbp_positive_share', 'pbp_evaluated'],
               'explanation': f"Reduced nearby opponent pressure by {stats['mean']:.2f} skaters per evaluated pass on average. "
                              f"{stats['evaluated_passes']} of {stats['eligible_passes']} eligible passes could be evaluated. "
                              'This measures pressure relief, not overall passing or attacking quality.',
               'achievement': None, 'video': None}
        self.cards[cfg['id']] = self._build_card(cfg)

    def _load_stats(self) -> list[dict]:
        path = DATA_DIR / self.match["stats_file"]
        with path.open(encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def _load_events(self) -> list[dict]:
        path = DATA_DIR / self.match["events_file"]
        with path.open(encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def _load_goalie_stats(self) -> list[dict]:
        """The stats CSV only covers skaters, so goalkeeper numbers are counted from the
        match events CSV: every Shot event names the goalkeeper as the secondary player."""
        shots = [r for r in self.event_rows if r["EventType"] == "Shot" and r["EventSecondaryPlayerName"]]
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
        if metric.get('derived'):
            values = [s[metric['aggregate']] for s in self.derived_kpis[metric['derived']]['players'].values()
                      if s['ranking_eligible']]
        else:
            values = [_to_number(r[metric["column"]]) for r in self._pool(metric)]
        values = [v for v in values if v is not None]
        if metric["higher_is_better"]:
            return 1 + sum(1 for v in values if v > value)
        return 1 + sum(1 for v in values if v < value)

    def _team_rank(self, metric: dict, value, team: str) -> int:
        """Like _rank, but only among the player's own team."""
        if metric.get('derived'):
            ids = {pid for (player_team, jersey), pid in self.events.ids.items() if player_team == team}
            values = [stats[metric['aggregate']] for pid, stats in self.derived_kpis[metric['derived']]['players'].items()
                      if pid in ids and stats['ranking_eligible']]
        else:
            values = [_to_number(r[metric["column"]]) for r in self._pool(metric) if r["Team"] == team]
        values = [v for v in values if v is not None]
        if metric["higher_is_better"]:
            return 1 + sum(1 for v in values if v > value)
        return 1 + sum(1 for v in values if v < value)

    def _build_attribute(self, metric_id: str, row: dict, moments: list[dict]) -> dict:
        metric = self.metrics[metric_id]
        if metric.get('derived'):
            stats = self.derived_kpis[metric['derived']]['players'].get(
                self.events.player_id(row['Team'], int(row['Jersey'])), {})
            value = stats.get(metric['aggregate'])
        else:
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
            "team_rank": self._team_rank(metric, value, row["Team"]) if value is not None else None,
            "players_in_match": (sum(s['ranking_eligible'] for s in self.derived_kpis[metric['derived']]['players'].values())
                                 if metric.get('derived') else len(self._pool(metric))),
            "rank_pool": "goalkeepers" if metric.get("goalkeeper") else "players",
        }
        # Ids of the events behind the number (see "events" in metrics.json); None if the
        # metric can't be traced to single events (e.g. time on ice, skating distance).
        attr["moment_ids"] = MatchEvents.select(moments, metric["events"]) if "events" in metric else None
        if metric.get('derived'):
            attr['coverage'] = stats.get('coverage')
            attr['detail'] = f"{stats.get('evaluated_passes', 0)} of {stats.get('eligible_passes', 0)} eligible passes evaluated"
            attr['moment_ids'] = stats.get('positive_event_ids' if metric['aggregate'] == 'positive_share' else 'event_ids', [])
            if not stats.get('ranking_eligible'):
                attr['match_rank'] = None
                attr['team_rank'] = None
        if "count_column" in metric:
            attr["detail"] = f'{row[metric["count_column"]]} of {row[metric["total_column"]]}'
        return attr

    def _build_card(self, cfg: dict) -> dict:
        row = self._find_row(cfg["team"], cfg["jersey"])
        moments = self.events.moments(self.events.player_id(cfg["team"], cfg["jersey"]))
        m = self.match
        return {
            "id": cfg["id"],
            "type": "special",
            "player": self._player(cfg, row),
            "title": cfg["title"],
            "archetype": self.archetypes.get(cfg["title"]),
            # The KPIs that earned the archetype, for the card back (may differ from the card's own attributes).
            "archetype_kpis": [self._build_attribute(mid, row, moments) for mid in self.archetype_metrics[cfg["title"]]],
            "match": self._match(cfg["team"]),
            "attributes": [self._build_attribute(mid, row, moments) for mid in cfg["attributes"]],
            "explanation": cfg["explanation"],
            "achievement": self.achievements.get(cfg["achievement"]) if cfg["achievement"] else None,
            "video": cfg["video"] or self._featured_video(moments),
            "video_sources": [self._video_source(v) for v in self.videos.values()] + self._recording_source(),
            "moments": moments,
            "edition": "standard",
            "source": m["events_source"] if cfg["position"] == "Goalkeeper" else m["source"],
        }

    def _player(self, cfg: dict, row: dict) -> dict:
        return {
            "first_name": row["FirstName"],
            "last_name": row["LastName"],
            "jersey": cfg["jersey"],
            "team": cfg["team"],
            "position": cfg["position"],
            "image_url": self.player_images.get((cfg["team"], cfg["jersey"])),
        }

    def _match(self, team: str) -> dict:
        m = self.match
        return {
            "id": m["id"],
            "date": m["date"],
            "stage": m["stage"],
            "home_team": m["home_team"],
            "away_team": m["away_team"],
            "home_score": m["home_score"],
            "away_score": m["away_score"],
            "opponent": m["away_team"] if team == m["home_team"] else m["home_team"],
        }

    def _build_base_card(self, cfg: dict, doc: dict) -> dict:
        """A plain card with the player's profile only: no archetype, stats or highlights. Players of the two teams
        in the final are named from the stats CSV; the other teams' cards, and the final's backup goalkeepers (who
        have no CSV row), carry the name themselves. Only the two finalists' cards link the match."""
        in_final = cfg["team"] in (self.match["home_team"], self.match["away_team"])
        row = ({"FirstName": cfg["first_name"], "LastName": cfg["last_name"]} if "first_name" in cfg
               else self._find_row(cfg["team"], cfg["jersey"]))
        bio_keys = ("date_of_birth", "place_of_birth", "nationality", "height_cm", "weight_kg", "shoots", "draft", "club")
        return {
            "id": cfg["id"],
            "type": "base",
            "player": self._player(cfg, row),
            "title": None,
            "match": self._match(cfg["team"]) if in_final else None,
            "bio": {k: cfg.get(k) for k in bio_keys},
            "edition": "standard",
            "source": doc["source"],
            "source_url": cfg.get("ep_url"),
        }

    def _camera_clip(self, timestamp: str) -> dict | None:
        """The clip cut from the arena recording for this event, if it has been cut
        (scripts/cut_clips.py). Checked once at startup, so restart after cutting."""
        if not self.recording or not (CLIPS_DIR / f"{timestamp}.mp4").exists():
            return None
        return {
            "video_id": self.recording["id"],
            "url": f"/api/media/clips/{timestamp}.mp4",
            "poster": f"/api/media/clips/{timestamp}.jpg",
        }

    def _recording_source(self) -> list[dict]:
        if not self.recording:
            return []
        return [{"id": self.recording["id"], "title": self.recording["title"]}]

    @staticmethod
    def _video_source(video: dict) -> dict:
        return {k: video[k] for k in ("id", "youtube_id", "title", "channel", "url", "permission")}

    def _featured_video(self, moments: list[dict]) -> dict | None:
        """The card's highlight: the player's best moment on camera (first goal, else first
        assist, else the most dangerous save or shot by xG, else a faceoff win). Without
        camera clips, the player's first goal or assist in the broadcast highlights. Otherwise
        the whole highlight reel, labelled as game highlights rather than as this player's."""
        filmed = [m for m in moments if m["clip"]]

        def of_kind(*kinds):
            return [m for m in filmed if m["kind"] in kinds]

        best = (
            of_kind("goal")[:1]
            or of_kind("assist")[:1]
            or sorted(of_kind("save", "shot"), key=lambda m: -(m["xg"] or 0))[:1]
            or sorted(of_kind('pass_pressure'), key=lambda m: -m['kpi']['value'])[:1]
            or of_kind("faceoff_win")[:1]
        )
        if best:
            return {**best[0]["clip"], "description": self._describe(best[0]), "scope": "moment"}
        own = next((m for m in moments if m["kind"] in ("goal", "assist") and m["broadcast"]), None)
        if own:
            return {
                **own["broadcast"],
                "poster": f'https://i.ytimg.com/vi/{own["broadcast"]["youtube_id"]}/hqdefault.jpg',
                "description": self._describe(own),
                "scope": "moment",
            }
        if not self.videos:
            return None
        video = next(iter(self.videos.values()))
        return {
            "video_id": video["id"],
            "youtube_id": video["youtube_id"],
            "start": 0,
            "end": None,
            "poster": f'https://i.ytimg.com/vi/{video["youtube_id"]}/hqdefault.jpg',
            "description": "Official highlights of the whole game. None of this player's own goals or assists are in it.",
            "scope": "game",
        }

    @staticmethod
    def _describe(m: dict) -> str:
        return f'{m["title"]} at {m["clock"]} of the {m["period_label"]}. {m["text"]}'.strip()

    def card_summary(self, card: dict) -> dict:
        """What the gallery shows for a card the user does not own yet: only the (grayed out) photo."""
        player = card["player"]
        return {
            "id": card["id"],
            "type": card["type"],
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
        """Multiple choice question: the card's player plus two other players with the same card
        type (so a player never shows up twice), shuffled. option_ids are card ids. Special cards
        ask 'who was the <archetype>?', base cards 'who is this player?' with a profile clue."""
        card = self.cards[card_id]
        others = [c for c, other in self.cards.items() if c != card_id and other["type"] == card["type"]]
        option_ids = rng.sample(others, min(2, len(others))) + [card_id]
        rng.shuffle(option_ids)
        m = card["match"]
        if card["type"] == "base":
            prompt, clue = "Who is this player?", self._profile_clue(card)
        else:
            prompt, clue = f'Who was the "{card["title"]}" in this game?', self.archetypes[card["title"]]
        return {
            "option_ids": option_ids,
            "prompt": prompt,
            "clue": clue,
            "match": f'{m["home_team"]} {m["home_score"]}–{m["away_score"]} {m["away_team"]}' if m else None,
        }

    @staticmethod
    def _profile_clue(card: dict) -> str:
        player, bio = card["player"], card["bio"]
        clue = f'{player["position"]} for {player["team"]}, wearing #{player["jersey"]}'
        if bio["date_of_birth"] and bio["place_of_birth"]:
            clue += f', born {bio["date_of_birth"][:4]} in {bio["place_of_birth"]}'
        return clue + "."


@lru_cache
def get_content() -> Content:
    return Content()
