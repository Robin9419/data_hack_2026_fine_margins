"""Loads the static content (metrics, match, cards, videos) and joins it with the
Wisehockey match statistics and events CSVs so card values always come from the data."""

import csv
import json
import math
import re
from functools import lru_cache
from pathlib import Path

from .events import ORDINALS, PERIOD_SECONDS, MatchEvents, _clock
from .event_kpis import EventAnalysis, pass_body_pressure, pass_packing, expected_assists, blc_xg, controlled_zone_exits, interceptions
from .ratings import HIGH_DANGER_XG, compute_ratings, goalie_stats
from .road_to_final import RoadToFinal
from .testdata import TestData, with_card_image
from .tournament import Tournament

ROOT = Path(__file__).resolve().parents[2]
CONTENT_DIR = ROOT / "backend" / "content"
DATA_DIR = ROOT / "data"
PLAYER_IMAGES_FILE = CONTENT_DIR / "player-images.json"
MEDIA_DIR = ROOT / "backend" / "media"  # served at /api/media; not in git
CLIPS_DIR = MEDIA_DIR / "clips"  # filled by scripts/cut_clips.py
MOMENTS_PER_KPI = 5  # most moments (video clips) a final impact special shows per KPI


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
    if fmt in ("decimal2", "decimal3"):
        display = f"{value:.2f}"
        # Keep a third decimal only when two decimals would hide a small value.
        if value != 0 and float(display) == 0:
            display = f"{value:.3f}"
        return display
    if fmt == "pct":
        return f"{round(value * 100)}"
    if fmt == "km":
        return f"{value / 1000:.2f}"
    if fmt == "mmss":
        minutes, seconds = divmod(int(value), 60)
        return f"{minutes}:{seconds:02d}"
    return str(value)


# Special cards a user must own to earn the trophy card.
TROPHY_SPECIALS = 3

class Content:
    def __init__(self):
        self.match = _load_json("match.json")
        self.metrics = {m["id"]: m for m in _load_json("metrics.json")["metrics"]}
        self.achievements = {a["id"]: a for a in _load_json("achievements.json")["achievements"]}
        cards_doc = _load_json("cards.json")
        self.pack_size = cards_doc["pack_size"]
        self.archetypes = cards_doc["archetypes"]
        self.archetype_metrics = {k: v for k, v in cards_doc["archetype_metrics"].items() if not k.startswith("_")}
        self.award_categories = _load_json('award_categories.json')['categories']
        self.trivia = _load_json("trivia.json")
        rewards_doc = _load_json("rewards.json")
        self.card_points = rewards_doc["card_points"]
        self.stadium_multiplier = rewards_doc["stadium_multiplier"]
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
        self.sides = {"Home": self.match["home_team"], "Away": self.match["away_team"]}
        self.ratings = compute_ratings(self.rows, self.event_rows, self.sides)
        self.goalie_rows = self._load_goalie_stats()
        goalkeeper_ids = {r['EventSecondaryPlayerId'] for r in self.event_rows
                          if r['EventType'] == 'Shot' and r['EventSecondaryPlayerId']}
        self.analysis = EventAnalysis(self.event_rows, goalkeeper_ids)
        self.derived_kpis = {'pass_body_pressure': pass_body_pressure(self.analysis),
                             'pass_packing': pass_packing(self.analysis),
                             'expected_assists': expected_assists(self.analysis),
                             'blc_xg': blc_xg(self.analysis),
                             'controlled_zone_exits': controlled_zone_exits(self.analysis),
                             'interceptions': interceptions(self.analysis)}
        self._add_pass_moments()
        self._add_packing_moments()
        self._add_xa_moments()
        self._add_zone_moments()
        self._add_interception_moments()
        self.player_images = self._load_player_images()
        base_doc = _load_json("base_cards.json")
        # Dual nationalities ("Canada / USA") show the first one on the card.
        self.nationalities = {(c["team"], c["jersey"]): c["nationality"].split(" / ")[0]
                              for c in base_doc["cards"] if c.get("nationality")}
        self.instagram = {(c["team"], c["jersey"]): c["instagram"] for c in base_doc["cards"] if c.get("instagram")}
        self.action_media = {(m["team"], m["jersey"]): m for m in _load_json("action_media.json")["players"]}
        self.card_images = _load_json("card_images.json")
        self.cards = {c["id"]: self._build_card(c) for c in cards_doc["cards"]}
        self._add_pressure_card()
        self._add_progression_card()
        self._add_xa_card()
        self._add_category_cards()
        self.cards |= {c["id"]: self._build_base_card(c, base_doc) for c in base_doc["cards"]}
        self._add_performance_cards(cards_doc["performance_specials"])
        self.reward_rules = {}  # reward card id -> function(owned card ids -> editions) saying whether it is earned
        self._add_reward_cards(_load_json("reward_cards.json"))
        positions = {(c["player"]["team"], c["player"]["jersey"]): c["player"]["position"]
                     for c in self.cards.values() if c["player"]}
        self.testdata = TestData(cards_doc["performance_specials"], self.metrics, format_value, positions, self.player_images,
                                 self.nationalities, self.action_media, self.card_images,
                                 self.archetypes)
        self.road_to_final = RoadToFinal(self.testdata, positions, _load_json("road_videos.json")["players"],
                                         _load_json("watch_stats.json")["players"])
        self.tournament = Tournament(self.testdata)
        # The game a card comes from (None: not tied to a game). Such a card only exists once its game is played on
        # the user's timeline. The cards built from the Wisehockey data, and the reward cards about them, are the final.
        final_id = self.tournament.final["id"]
        self.card_game = {cid: final_id for cid, c in self.cards.items()
                          if c["type"] == "special" or c.get("context_type") == "moment"}
        self.cards |= self.testdata.cards  # the specials of the other games (official game statistics)
        self.card_game |= {cid: c["test_game"] for cid, c in self.testdata.cards.items()}
        legends_doc = _load_json("legends.json")
        self.legend_thresholds = legends_doc["thresholds"]
        self.cards |= {c["id"]: self._build_legend_card(c, legends_doc) for c in legends_doc["cards"]}
        for category in self.award_categories:
            titles = set(category.get('existing_awards', [])) | {award['title'] for award in category['awards']}
            for card in self.cards.values():
                if card['type'] == 'special' and card['title'] in titles:
                    card.update(category_id=category['id'], category=category['label'])

    def _add_pass_moments(self):
        for result in self.derived_kpis['pass_body_pressure']['events']:
            if result['value'] is None:
                continue
            row = self.event_rows[result['source_row'] - 1]
            moment = self.events._moment(
                row, 'pass_pressure', 'Pressure-reducing pass' if result['value'] > 0 else 'Successful pass',
                f"Pass to {self.events.names.get(result['receiver_id'], 'receiver')}. "
                f"Opponents applying pressure: {result['pbp_pg']} before the pass, "
                f"{result['pbp_pe']} at reception (pressure reduction: {result['value']:+d}).")
            moment.update(id=result['id'], kpi=result)
            self.events.by_player.setdefault(result['passer_id'], []).append(moment)
        for moments in self.events.by_player.values():
            moments.sort(key=lambda m: (int(m['timestamp']), m['id']))

    def _add_packing_moments(self):
        for result in self.derived_kpis['pass_packing']['events']:
            if result['value'] is None:
                continue
            row = self.event_rows[result['source_row'] - 1]
            moment = self.events._moment(
                row, 'pass_packing', 'Packing pass',
                f"Pass to {self.events.names.get(result['receiver_id'], 'receiver')}. "
                f"Net change in opponents bypassed by the pass: {result['value']:+d}, "
                "based on their positions when the puck was released.")
            moment.update(id=result['id'], kpi=result)
            self.events.by_player.setdefault(result['passer_id'], []).append(moment)
        for moments in self.events.by_player.values():
            moments.sort(key=lambda m: (int(m['timestamp']), m['id']))

    def _without_profile(self, candidates):
        """A player holds one profile card per game: drop the candidates who already have one, so that an award
        whose winner is taken goes to the next best player."""
        held = {(c['player']['team'], c['player']['jersey']) for c in self.cards.values()
                if c.get('kind') == 'profile' and c.get('player')}
        return [(pid, stats) for pid, stats in candidates
                if next((key for key, value in self.events.ids.items() if value == pid), None) not in held]

    def _add_pressure_card(self):
        candidates = [(pid, stats) for pid, stats in self.derived_kpis['pass_body_pressure']['players'].items()
                      if stats['ranking_eligible'] and stats['mean'] > 0]
        candidates = self._without_profile(candidates)
        if not candidates:
            return
        # Deterministic tie break: more evaluated passes, then player ID.
        pid, stats = max(candidates, key=lambda item: (item[1]['mean'], item[1]['evaluated_passes'], item[0]))
        team, jersey = next(key for key, value in self.events.ids.items() if value == pid)
        self.archetypes['Pressure Breaker'] = ('Highest average reduction in nearby opposing skaters through successful passes, '
                                               'with at least 10 passes that can be assessed. Compares pressure within 3 metres '
                                               'of the passer with pressure on the receiver shortly afterwards, using tracking estimates.')
        self.archetype_metrics['Pressure Breaker'] = ['pbp_mean', 'packing_mean', 'packing_total']
        cfg = {'id': 'pressure-reliever', 'team': team, 'jersey': jersey, 'position': 'Skater',
               'title': 'Pressure Breaker', 'attributes': ['pbp_mean', 'packing_mean', 'packing_total'],
               'explanation': f"Left teammates with {stats['mean']:.2f} fewer nearby opponents per completed pass on average. "
                              f"Enough tracking information was available for {stats['evaluated_passes']} of "
                              f"{stats['eligible_passes']} passes. This award recognises passes that relieve pressure.",
               'achievement': None, 'video': None}
        self.cards[cfg['id']] = self._build_card(cfg)

    def _add_progression_card(self):
        calculation = self.derived_kpis['pass_packing']
        candidates = [(pid, stats) for pid, stats in calculation['players'].items()
                      if stats['ranking_eligible'] and stats['mean'] > 0]
        candidates = self._without_profile(candidates)
        if not candidates:
            return
        pid, stats = max(candidates, key=lambda item: (item[1]['mean'], item[1]['evaluated_passes'], item[0]))
        team, jersey = next(key for key, value in self.events.ids.items() if value == pid)
        minimum = calculation['parameters']['min_evaluated']
        title = 'Progression Master'
        self.archetypes[title] = (
            f'Highest average number of opponents bypassed towards the attacking goal, with a score above zero '
            f'and at least {minimum} passes that can be assessed. Opponents are judged by where they stood '
            'when the pass was released. Backward passes can reduce the score; ties favour more assessed passes.')
        metrics = ['packing_mean', 'packing_total', 'packing_positive_share']
        self.archetype_metrics[title] = metrics
        cfg = {'id': 'progression-master', 'team': team, 'jersey': jersey, 'position': 'Skater',
               'title': title, 'attributes': metrics,
               'explanation': f"Bypassed an average of {stats['mean']:.2f} opponents per assessed pass towards the attacking goal, "
                              f"the highest qualifying average in this game. The total was {stats['total']} after "
                              f"subtracting the effect of backward passes. Enough tracking information was available "
                              f"for {stats['evaluated_passes']} of {stats['eligible_passes']} passes.",
               'achievement': None, 'video': None}
        card = self._build_card(cfg)
        filmed = [m for m in card['moments'] if m['kind'] == 'pass_packing' and m['kpi']['value'] > 0 and m['clip']]
        if filmed:
            best = max(filmed, key=lambda m: (m['kpi']['value'], -int(m['timestamp'])))
            card['video'] = {**best['clip'], 'description': self._describe(best), 'scope': 'moment'}
        card['source'] = self.match['events_source']
        self.cards[cfg['id']] = card

    def _add_xa_moments(self):
        for result in self.derived_kpis['expected_assists']['events']:
            if result['value'] is None:
                continue
            row = self.event_rows[result['source_row'] - 1]
            moment = self.events._moment(row, 'expected_assist', 'Chance set up',
                f"Pass to {self.events.names.get(result['shooter_id'], 'shooter')} sets up a shot "
                f"with {result['value']:.3f} xG.", shot=row)
            moment.update(id=result['id'], kpi=result)
            self.events.by_player.setdefault(result['passer_id'], []).append(moment)
        for moments in self.events.by_player.values():
            moments.sort(key=lambda m: (int(m['timestamp']), m['id']))

    def _add_xa_card(self):
        candidates = [(pid, stats) for pid, stats in self.derived_kpis['expected_assists']['players'].items()
                      if stats['total'] > 0]
        candidates = self._without_profile(candidates)
        if not candidates:
            return
        pid, stats = max(candidates, key=lambda item: (item[1]['total'], item[1]['assisted_shots'], item[0]))
        team, jersey = next(key for key, value in self.events.ids.items() if value == pid)
        title = 'Chance Architect'
        self.archetypes[title] = ('Highest total expected assists (xA): scoring-chance quality created by passes that set up shots. '
                                 'The last completed pass within four seconds of a shot receives that shot\'s estimated '
                                 'chance of scoring, provided the opponents do not gain control before the shot.')
        metrics = ['xa_total', 'xa_assisted_shots', 'xa_mean']
        self.archetype_metrics[title] = metrics
        cfg = {'id': 'chance-architect', 'team': team, 'jersey': jersey, 'position': 'Skater',
               'title': title, 'attributes': metrics,
               'explanation': f"Created {stats['total']:.3f} expected assists from {stats['assisted_shots']} shots. "
                              'Expected assists add up the scoring chances of shots set up by the player\'s passes. '
                              'Only the last completed pass within four seconds before each shot counts, '
                              'provided the opponents do not gain control before the shot.',
               'achievement': None, 'video': None}
        card = self._build_card(cfg)
        filmed = [m for m in card['moments'] if m['kind'] == 'expected_assist' and m['clip']]
        if filmed:
            best = max(filmed, key=lambda m: (m['kpi']['value'], -int(m['timestamp'])))
            card['video'] = {**best['clip'], 'description': self._describe(best), 'scope': 'moment'}
        card['source'] = self.match['events_source']
        self.cards[cfg['id']] = card

    def _add_zone_moments(self):
        for metric_id, kind in [('blc_xg', 'zone_entry'), ('controlled_zone_exits', 'zone_exit')]:
            for result in self.derived_kpis[metric_id]['events']:
                if result['value'] is None:
                    continue
                row = self.event_rows[result['source_row'] - 1]
                entry = metric_id == 'blc_xg'
                title = 'Offensive zone entry' if entry else ('Controlled zone exit' if result['value'] else 'Uncontrolled zone exit')
                outcomes = {
                    'PossessionMaintained': 'Possession maintained after crossing the blue line.',
                    'PossessionLost': 'Possession lost after crossing the blue line.',
                    'PuckDumpedIn': 'Puck dumped in rather than carried under control.',
                }
                text = (f"The team's {len(result['shot_source_rows'])} shots after this entry "
                        f"total {result['value']:.3f} expected goals. "
                        'The sequence includes any recovery of the puck inside the zone.' if entry
                        else outcomes.get(result['crossing_result'],
                                          re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', result['crossing_result']) + '.'))
                moment = self.events._moment(row, kind, title, text)
                moment.update(id=result['id'], kpi=result)
                if entry:
                    duration = (int(result['end_timestamp']) - int(result['timestamp'])) / 1000
                    moment['clip_window'] = [-3, duration + 2]
                self.events.by_player.setdefault(result['player_id'], []).append(moment)
        for moments in self.events.by_player.values():
            moments.sort(key=lambda m: (int(m['timestamp']), m['id']))

    def _add_interception_moments(self):
        for result in self.derived_kpis['interceptions']['events']:
            if result['value'] is None:
                continue
            row = self.event_rows[result['source_row'] - 1]
            moment = self.events._moment(row, 'interception', 'Pass intercepted',
                f"Intercepted a pass from {self.events.names.get(result['passer_id'], 'opponent')}.")
            moment.update(id=result['id'], kpi=result)
            self.events.by_player.setdefault(result['interceptor_id'], []).append(moment)
        for moments in self.events.by_player.values():
            moments.sort(key=lambda m: (int(m['timestamp']), m['id']))

    def _add_category_cards(self):
        for category in self.award_categories:
            for award in category['awards']:
                if award.get('derived'):
                    calculation = self.derived_kpis[award['derived']]
                    candidates = [(pid, stats) for pid, stats in calculation['players'].items()
                                  if stats['ranking_eligible'] and stats[award['aggregate']] is not None
                                  and stats[award['aggregate']] > 0
                                  and any(value == pid for value in self.events.ids.values())]
                else:
                    metric = self.metrics[award['primary_metric']]
                    candidates = []
                    for row in self.rows:
                        pid = self.events.player_id(row['Team'], int(row['Jersey']))
                        value = _to_number(row[metric['column']])
                        if pid and pid not in self.analysis.goalkeeper_ids and value is not None and math.isfinite(value) and value > 0:
                            candidates.append((pid, {award['aggregate']: value}))
                candidates = self._without_profile(candidates)
                if award.get('tie_break_metric'):
                    enriched = []
                    for pid, stats in candidates:
                        # Copy calculator aggregates rather than mutating the cached analysis.
                        stats = dict(stats)
                        team, jersey = next(key for key, value in self.events.ids.items() if value == pid)
                        moments = self.events.moments(pid)
                        attr = self._build_attribute(award['tie_break_metric'], self._find_row(team, jersey), moments)
                        stats[award['tie_break_aggregate']] = attr['value'] if attr['value'] is not None else 0
                        enriched.append((pid, stats))
                    candidates = enriched
                if not candidates:
                    continue
                pid, stats = max(candidates, key=lambda item: (
                    item[1][award['aggregate']], item[1][award['tie_break_aggregate']], item[0]))
                team, jersey = next(key for key, value in self.events.ids.items() if value == pid)
                title, metrics = award['title'], award['metrics']
                self.archetypes[title] = award['definition']
                self.archetype_metrics[title] = metrics
                cfg = {'id': award['id'], 'team': team, 'jersey': jersey, 'position': 'Skater',
                       'title': title, 'attributes': metrics, 'explanation': award['definition'],
                       'achievement': None, 'video': None}
                card = self._build_card(cfg)
                card.update(category_id=category['id'], category=category['label'],
                            source=self.match['events_source'] if award.get('derived') else self.match['source'])
                ids = set(card['attributes'][0]['moment_ids'] or [])
                filmed = [m for m in card['moments'] if m['id'] in ids and m['clip'] and m['kpi']['value'] > 0]
                card['video'] = None
                if filmed:
                    best = max(filmed, key=lambda m: (m['kpi']['value'], -int(m['timestamp'])))
                    card['video'] = {**best['clip'], 'description': self._describe(best), 'scope': 'moment'}
                self.cards[award['id']] = card

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
            "source_label": metric["source_label"],
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
            if metric['derived'] == 'expected_assists':
                attr['detail'] = f"{stats.get('assisted_shots', 0)} attributed shots"
            elif metric['derived'] == 'blc_xg':
                attr['detail'] = f"{stats.get('evaluated_entries', 0)} of {stats.get('eligible_entries', 0)} eligible entries evaluated"
            elif metric['derived'] == 'controlled_zone_exits':
                attr['detail'] = (f"{format_value(stats.get('controlled_exits'), 'int')} of "
                                  f"{stats.get('evaluated_exits', 0)} evaluated exits controlled; "
                                  f"{stats.get('eligible_exits', 0)} eligible crossings")
            elif metric['derived'] == 'interceptions':
                attr['detail'] = f"{stats.get('interceptions', 0)} intercepted opponent passes across all zones"
            else:
                attr['detail'] = f"{stats.get('evaluated_passes', 0)} of {stats.get('eligible_passes', 0)} eligible passes evaluated"
            event_key = ('positive_event_ids' if metric['aggregate'] == 'positive_share' else
                         'controlled_event_ids' if metric['aggregate'] == 'controlled_exits' else 'event_ids')
            attr['moment_ids'] = stats.get(event_key, [])
            if not stats.get('ranking_eligible'):
                attr['match_rank'] = None
                attr['team_rank'] = None
        if "count_column" in metric:
            attr["detail"] = f'{row[metric["count_column"]]} of {row[metric["total_column"]]}'
        return attr

    @staticmethod
    def _cap_moments(moments: list[dict], attributes: list[dict]) -> list[dict]:
        """A card only shows the moments behind its own KPIs, at most MOMENTS_PER_KPI per KPI: the ones on video first,
        then the highest KPI value. The KPIs' moment_ids are trimmed to the kept moments."""
        by_id = {m["id"]: m for m in moments}

        def rank(moment_id: str):
            m = by_id[moment_id]
            value = (m.get("kpi") or {}).get("value")
            return (not (m["clip"] or m["broadcast"]), -(value if isinstance(value, (int, float)) else 0))

        kept: set[str] = set()
        for attr in attributes:
            ids = [i for i in dict.fromkeys(attr.get("moment_ids") or []) if i in by_id]
            if attr.get("moment_ids") is None:
                continue
            attr["moment_ids"] = [i for i in by_id if i in set(sorted(ids, key=rank)[:MOMENTS_PER_KPI])]
            kept.update(attr["moment_ids"])
        return [m for m in moments if m["id"] in kept]

    def _build_card(self, cfg: dict) -> dict:
        row = self._find_row(cfg["team"], cfg["jersey"])
        moments = self.events.moments(self.events.player_id(cfg["team"], cfg["jersey"]))
        m = self.match
        archetype_kpis = [self._build_attribute(mid, row, moments) for mid in self.archetype_metrics[cfg["title"]]]
        attributes = [self._build_attribute(mid, row, moments) for mid in cfg["attributes"]]
        moments = self._cap_moments(moments, [*attributes, *archetype_kpis])
        return {
            "id": cfg["id"],
            "type": "special",
            "kind": cfg.get("kind", "profile"),
            "special_type": cfg.get("special_type"),
            "rating": self._rating(cfg["team"], cfg["jersey"]),
            "player": self._player(cfg, row),
            "title": cfg["title"],
            "archetype": self.archetypes.get(cfg["title"]),
            # The KPIs that earned the archetype, for the card back (may differ from the card's own attributes).
            "archetype_kpis": archetype_kpis,
            "match": self._match(cfg["team"]),
            "attributes": attributes,
            "explanation": cfg["explanation"],
            "achievement": self.achievements.get(cfg["achievement"]) if cfg["achievement"] else None,
            "video": cfg["video"] or self._featured_video(moments),
            "video_sources": [self._video_source(v) for v in self.videos.values()] + self._recording_source(),
            "moments": moments,
            "edition": "standard",
            "source": m["events_source"] if cfg["position"] == "Goalkeeper" else m["source"],
        }

    def _rating(self, team: str, jersey: int) -> dict | None:
        """Match rating and tier of the player in this game (see ratings.py)."""
        rating = self.ratings.get((team, jersey))
        return {"mr": rating["mr"], "tier": rating["tier"]} if rating else None

    def _add_performance_cards(self, specs: dict):
        """Specials awarded by a fixed rule from the match data: Player of the Match, Game Winner, Brick Wall."""
        m = self.match
        home_wins = m["home_score"] > m["away_score"]
        winner, loser = (m["home_team"], m["away_team"]) if home_wins else (m["away_team"], m["home_team"])
        winner_goals, loser_goals = max(m["home_score"], m["away_score"]), min(m["home_score"], m["away_score"])

        def number(row: dict, column: str):
            return _to_number(row[column]) or 0

        def plural(n, word: str) -> str:
            return f"{n} {word}{'' if n == 1 else 's'}"

        def team_and_jersey(player_id: str) -> tuple[str, int]:
            return next(key for key, value in self.events.ids.items() if value == player_id)

        picks = {}
        star = max((r for r in self.rows if r["Team"] == winner), key=lambda r: (number(r, "P"), number(r, "G")))
        picks["motm"] = (
            (star["Team"], int(star["Jersey"])),
            f"{plural(number(star, 'G'), 'goal')} and {plural(number(star, 'A'), 'assist')}: "
            f"the most points on the winning team in the {winner} win.",
        )

        score = {"Home": 0, "Away": 0}
        won_goals = 0
        for r in self.event_rows:
            if r["EventType"] != "Goal":
                continue
            score[r["EventPrimaryTeam"]] += 1
            if self.sides[r["EventPrimaryTeam"]] != winner:
                continue
            won_goals += 1
            if won_goals == loser_goals + 1:
                period, clock = int(r["Period"]), int(r["MatchClock"])
                picks["gamewinner"] = (
                    team_and_jersey(r["EventPrimaryPlayerId"]),
                    f"Scored the goal that made it {won_goals}–{sum(score.values()) - won_goals} for {winner} at "
                    f"{_clock((period - 1) * PERIOD_SECONDS + clock)} ({ORDINALS.get(period, period)} period). "
                    f"{loser} never drew level again.",
                )
                break

        goalies = goalie_stats(self.event_rows, self.sides)
        if goalies:
            key, g = max(goalies.items(), key=lambda item: (item[1]["hd_saves"], item[1]["saves"]))
            picks["wall"] = (
                key,
                f"Stopped {g['hd_saves']} of {g['hd_shots']} high-danger chances (shots worth at least "
                f"{HIGH_DANGER_XG} expected goals), the most of any goalkeeper in the game.",
            )

        positions = {(c["player"]["team"], c["player"]["jersey"]): c["player"]["position"] for c in self.cards.values()}
        for special_type, (key, explanation) in picks.items():
            spec = specs[special_type]
            self.archetypes[spec["title"]] = spec["rule"]
            self.archetype_metrics[spec["title"]] = spec["attributes"]
            cfg = {
                "id": spec["id"], "kind": "performance", "special_type": special_type,
                "team": key[0], "jersey": key[1], "position": positions.get(key, "Skater"),
                "title": spec["title"], "attributes": spec["attributes"], "explanation": explanation,
                "achievement": None, "video": None,
            }
            self.cards[cfg["id"]] = self._build_card(cfg)

    def _add_reward_cards(self, doc: dict):
        """Cards earned from what the user owns: a collector card per club whose base cards are all owned, plus context cards."""
        match = self._match(self.match["home_team"])
        by_team: dict[str, list[str]] = {}
        for cid, card in self.cards.items():
            if card["type"] == "base":
                by_team.setdefault(card["player"]["team"], []).append(cid)

        collector = doc["collector"]
        for team, ids in by_team.items():
            card_id = "collector-" + re.sub(r"\W+", "-", team.lower())
            self.cards[card_id] = {
                "id": card_id, "type": "reward", "kind": "collector", "special_type": None, "rating": None,
                "player": None, "team": team, "title": team, "match": self._match(team), "edition": "reward",
                "requires": ids, "unlock": collector["unlock"],
                "explanation": f"All {len(ids)} base cards of {team} in one collection.",
                "club": doc["clubs"].get(team),
                "intro_video": self._intro_video(collector.get("intro_videos", {}).get(team)),
                "source": self.match["source"],
            }
            self.reward_rules[card_id] = lambda owned, ids=ids: all(i in owned for i in ids)

        for cfg in doc["context"]:
            card = {
                "id": cfg["id"], "type": "reward", "kind": "context", "context_type": cfg["context_type"],
                "special_type": None, "rating": None, "player": None, "title": cfg["title"], "match": match,
                "edition": "reward", "unlock": cfg["unlock"], "source": self.match["source"],
                **{k: cfg[k] for k in ("headline", "text", "image_url", "image_alt", "image_position", "credit", "about")
                   if k in cfg},
            }
            if cfg.get("video_id"):
                card["intro_video"] = self._intro_video(cfg["video_id"], cfg.get("video_description", ""))
            if cfg["context_type"] == "moment":
                scorer = self._add_moment_facts(card)
                self.reward_rules[cfg["id"]] = lambda owned, who=scorer: any(
                    (self.cards[c]["player"] or {}).get("team") == who[0] and (self.cards[c]["player"] or {}).get("jersey") == who[1]
                    for c in owned if c in self.cards and self.cards[c]["type"] != "reward"
                )
            elif cfg["context_type"] == "stadium":
                self.reward_rules[cfg["id"]] = lambda owned: "stadium" in owned.values()
            else:
                # The trophy exists from the start of the tournament and is not about one game.
                card["match"] = None
                self.reward_rules[cfg["id"]] = lambda owned: sum(
                    self.cards.get(c, {}).get("type") == "special" for c in owned) >= TROPHY_SPECIALS
            self.cards[cfg["id"]] = card

    @staticmethod
    def _intro_video(youtube_id: str | None, description: str = "Official welcome video, Spengler Cup Davos",
                     start: int = 0, end: int | None = None) -> dict | None:
        """A YouTube clip shown on a reward card's page and pop-up: the official 'Welcome <team>' video of a collector
        card, the video of a stadium or trophy card, or a legend's video (optionally only the stretch start–end, in
        seconds, of a longer video)."""
        if not youtube_id:
            return None
        return {"youtube_id": youtube_id, "start": start or 0, "end": end, "scope": "game",
                "poster": f"https://i.ytimg.com/vi/{youtube_id}/hqdefault.jpg",
                "description": description}

    def _goal_video(self, goal: dict | None) -> dict | None:
        """The clip of a goal: the arena camera cut if there is one, else the TV replay of the highlights."""
        if not goal:
            return None
        clip = goal["clip"] or goal["broadcast"]
        if not clip:
            return None
        poster = clip.get("poster") or f'https://i.ytimg.com/vi/{clip["youtube_id"]}/hqdefault.jpg'
        return {**clip, "poster": poster, "scope": "game", "description": "The last goal of the game"}

    def _add_moment_facts(self, card: dict) -> tuple[str, int]:
        """Fills the moment card from the last goal of the game and returns the scorer as (team, jersey)."""
        score = {"Home": 0, "Away": 0}
        last = None
        for r in self.event_rows:
            if r["EventType"] == "Goal":
                score[r["EventPrimaryTeam"]] += 1
                last = r
        team, jersey = next(k for k, v in self.events.ids.items() if v == last["EventPrimaryPlayerId"])
        period, clock = int(last["Period"]), int(last["MatchClock"])
        assists = [re.sub(r"^#\d+ ", "", self.events.names.get(a, "unknown")) for a in (last["GoalAssist1Id"], last["GoalAssist2Id"]) if a]
        positions = {(c["player"]["team"], c["player"]["jersey"]): c["player"]["position"]
                     for c in self.cards.values() if c["player"]}
        row = self._find_row(team, jersey)
        card["player"] = self._player({"id": card["id"], "team": team, "jersey": jersey,
                                       "position": positions.get((team, jersey), "Skater")}, row)
        goal = next((m for m in self.events.moments(last["EventPrimaryPlayerId"])
                     if m["kind"] == "goal" and m["timestamp"] == last["Timestamp"]), None)
        card["intro_video"] = self._goal_video(goal)
        card["headline"] = f'{score["Home"]}–{score["Away"]}'
        assist_text = f" Assisted by {' and '.join(assists)}." if assists else " Unassisted."
        card["text"] = (
            f'{row["FirstName"]} {row["LastName"]} scored the last goal at {_clock((period - 1) * PERIOD_SECONDS + clock)}'
            f" ({ORDINALS.get(period, period)} period)." + assist_text
        )
        return team, jersey

    def earned_cards(self, owned: dict[str, str]) -> dict[str, str]:
        """Reward cards the user has earned from the cards they own (card id -> edition)."""
        return {cid: "reward" for cid, rule in self.reward_rules.items() if rule(owned)}

    def _action_media(self, team: str, jersey: int) -> dict:
        media = self.action_media.get((team, jersey), {})
        return {"action_image_url": media.get("image_url"), "action_video_url": media.get("video_url"),
                "action_focus": media.get("focus")}

    def _player(self, cfg: dict, row: dict) -> dict:
        return with_card_image({
            "first_name": row["FirstName"],
            "last_name": row["LastName"],
            "jersey": cfg["jersey"],
            "team": cfg["team"],
            "position": cfg["position"],
            "image_url": self.player_images.get((cfg["team"], cfg["jersey"])),
            "nationality": self.nationalities.get((cfg["team"], cfg["jersey"])),
            "instagram": self.instagram.get((cfg["team"], cfg["jersey"])),
            **self._action_media(cfg["team"], cfg["jersey"]),
        }, self.card_images.get(cfg.get("id")), full_art=cfg.get("kind") == "performance")

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
            "kind": "base",
            "special_type": None,
            "rating": None,
            "player": self._player(cfg, row),
            "title": None,
            "match": self._match(cfg["team"]) if in_final else None,
            "bio": {k: cfg.get(k) for k in bio_keys},
            "edition": "standard",
            "source": doc["source"],
            "source_url": cfg.get("ep_url"),
        }

    def _build_legend_card(self, cfg: dict, doc: dict) -> dict:
        """A club legend: not from the 2025 tournament, so no stats or match, only why the player is a legend. Won
        automatically by collecting a share of the club's cards (see legends_due)."""
        return {
            "id": cfg["id"],
            "type": "legend",
            "player": {
                "first_name": cfg["first_name"],
                "last_name": cfg["last_name"],
                "jersey": cfg.get("jersey"),
                "team": cfg["team"],
                "position": cfg["position"],
                "image_url": cfg.get("image_url"),
                "image_position": cfg.get("image_position"),
                "instagram": cfg.get("instagram"),
            },
            "title": "Legend",
            "match": None,
            "legend": {k: cfg.get(k) for k in ("era", "nationality", "summary", "spengler_cup", "honours", "moment",
                                                "image_credit", "image_source_url", "sources")},
            "edition": "legend",
            "intro_video": self._intro_video(cfg.get("video_id"), f"{cfg['first_name']} {cfg['last_name']}",
                                             cfg.get("video_start", 0), cfg.get("video_end")),
            "source": doc["source"],
        }

    def available(self, played: set[str]) -> set[str]:
        """Ids of the cards that exist once the given games are played: every card not tied to a game, plus the cards
        of those games."""
        return {cid for cid in self.cards if self.card_game.get(cid) is None or self.card_game[cid] in played}

    def game_cards(self, game_id: str) -> list[str]:
        return [cid for cid, gid in self.card_game.items() if gid == game_id and self.cards[cid]["type"] == "special"]

    def club_cards(self, team: str, available: set[str]) -> list[str]:
        """The cards that count towards a club's collection: its base and special cards (not its legends) that exist
        so far. The club grows with every game it plays."""
        return [cid for cid, c in self.cards.items()
                if c["type"] in ("base", "special") and c["player"]["team"] == team and cid in available]

    def legends_due(self, team: str, owned: dict[str, str], available: set[str]) -> int:
        """How many legends a user has earned for the club: one per threshold (share of club_cards owned) reached."""
        club = self.club_cards(team, available)
        have = sum(cid in owned for cid in club)
        return sum(have >= math.ceil(t * len(club)) for t in self.legend_thresholds)

    def club_progress(self, owned: dict[str, str], available: set[str]) -> list[dict]:
        """Per club: cards collected, legends owned and how many cards the next legend needs."""
        teams = dict.fromkeys(c["player"]["team"] for c in self.cards.values() if c["type"] == "legend")
        result = []
        for team in teams:
            club = self.club_cards(team, available)
            have = sum(cid in owned for cid in club)
            steps = [math.ceil(t * len(club)) for t in self.legend_thresholds]
            legends = [cid for cid, c in self.cards.items() if c["type"] == "legend" and c["player"]["team"] == team]
            result.append({
                "team": team,
                "owned": have,
                "total": len(club),
                "legends_owned": sum(cid in owned for cid in legends),
                "legends_total": len(legends),
                "thresholds": steps,
                "next_at": next((n for n in steps if n > have), None),
            })
        return result

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
        """What the gallery shows for a card the user does not own yet: only the (grayed out) photo. A legend shows
        nothing but its club, so it stays a surprise. Reward cards show what unlocks them instead, which is not a
        secret."""
        if card["type"] == "reward":
            keys = ("id", "type", "kind", "context_type", "title", "unlock", "requires", "team")
            return {**{k: card[k] for k in keys if k in card}, "player": None}
        summary = {"id": card["id"], "type": card["type"], "player": self._photo_only(card["player"], card["type"] == "legend")}
        if "kind" in card:
            summary["kind"] = card["kind"]
        return summary

    @staticmethod
    def _photo_only(player: dict, hide_identity: bool = False) -> dict:
        return {
            "image_url": None if hide_identity else player.get("image_url"),
            "image_position": None if hide_identity else player.get("image_position"),
            "jersey": None if hide_identity else player.get("jersey"),
            "team": player["team"],
            "first_name": "",
            "last_name": "",
        }

    def card_value(self, card_id: str, edition: str) -> int:
        """Reward points for one owned card: base cards and legends by their own value, reward cards (collector and
        context, the Collector filter) by the 'reward' value, every other card (special) as a special. A stadium edition
        is worth the stadium multiplier."""
        card_type = self.cards[card_id]["type"]
        if card_type in ("base", "legend", "reward"):
            value = self.card_points[card_type]
        else:
            value = self.card_points["special"]
        return value * self.stadium_multiplier if edition == "stadium" else value

    def progress(self, owned: dict[str, str], available: set[str]) -> dict:
        """Reward-bar state from the owned cards (card id -> edition) among the cards that exist so far."""
        points = sum(self.card_value(cid, edition) for cid, edition in owned.items() if cid in self.cards)
        rewards = [{**r, "reached": points >= r["points"]} for r in self.rewards]
        return {
            "points": points,
            "max_points": rewards[-1]["points"],
            "rewards": rewards,
            "owned_count": len(owned),
            "stadium_count": sum(1 for e in owned.values() if e == "stadium"),
            "total_cards": len(available),
            "clubs": self.club_progress(owned, available),
        }

    def build_question(self, card_id: str, rng) -> dict:
        """Multiple choice question: the card's player plus two other players, shuffled. option_ids are card ids.
        For a card from a game the other options are players of that game in the same role (goalkeeper or skater):
        at most one with another special card of the game (so the questions of one game don't all list the same
        names), the rest from the base cards of both teams. Special cards describe the playstyle in plain words (see
        trivia.json), base cards ask 'who is this player?'. The hint button shows 'hint' and strikes out 'eliminate',
        one of the wrong options."""
        card = self.cards[card_id]
        player_of = lambda cid: (self.cards[cid]["player"]["team"], self.cards[cid]["player"]["jersey"])
        player = player_of(card_id)
        game = self.card_game.get(card_id)
        if game:
            teams = (card["match"]["home_team"], card["match"]["away_team"])
            goalie = card["player"]["position"] == "Goalkeeper"
            same_role = lambda cid: (self.cards[cid]["player"]["position"] == "Goalkeeper") == goalie
            specials = [c for c in self.game_cards(game) if same_role(c) and player_of(c) != player]
            base = [c for c, o in self.cards.items() if o["type"] == "base" and o["player"]["team"] in teams and same_role(c)]
            rng.shuffle(specials)
            rng.shuffle(base)
            candidates = specials[:1] + base
        else:
            candidates = [c for c, other in self.cards.items() if other["type"] == card["type"]]
            rng.shuffle(candidates)
        # One option per player, so a player with several cards is not listed twice.
        distinct = {}
        for c in candidates:
            if player_of(c) != player:
                distinct.setdefault(player_of(c), c)
        others = list(distinct.values())[:2]
        option_ids = others + [card_id]
        rng.shuffle(option_ids)
        m = card["match"]
        if card["type"] == "base":
            prompt, hint = "Who is this player?", self._profile_clue(card)
        else:
            wording = self.trivia["titles"].get(card["title"])
            prompt = wording["prompt"] if wording else f'Who was the "{card["title"]}" in this game?'
            hint = wording["hint"] if wording else card["archetype"] or self.archetypes[card["title"]]
        return {
            "option_ids": option_ids,
            "prompt": prompt,
            "hint": hint,
            "eliminate": rng.choice(others) if others else None,
            "match": f'{m["home_team"]} {m["home_score"]}–{m["away_score"]} {m["away_team"]}' if m else None,
        }

    def explain_answer(self, card_id: str) -> str:
        """Why the card's player is the right answer, shown after a wrong one: the playstyle the card stands for and
        the player's numbers from the game (zeros left out, they would only confuse)."""
        card = self.cards[card_id]
        if card["type"] == "base":
            return self._profile_clue(card)
        wording = self.trivia["titles"].get(card["title"])
        why = wording["why"] if wording else card["archetype"] or self.archetypes[card["title"]]
        phrases = self.trivia["stat_phrases"]
        stats = []
        for attr in card.get("archetype_kpis") or card.get("attributes") or []:
            shown = attr.get("display_value")
            if attr.get("metric_id") not in phrases or shown in (None, "–") or not _to_number(shown.replace(":", "")):
                continue
            singular, plural = phrases[attr["metric_id"]]
            stats.append((singular if shown == "1" else plural).format(shown))
        return f'{why} In this game: {", ".join(stats)}.' if stats else why

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
