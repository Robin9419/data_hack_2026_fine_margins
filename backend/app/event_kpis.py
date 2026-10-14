"""Reusable snapshot analysis and event-level KPI results. No rows are deduplicated."""
from bisect import bisect_right
from collections import Counter, defaultdict
from math import hypot, isfinite


def coordinate(raw):
    try:
        x, y = map(float, raw.split(','))
        return (x, y) if isfinite(x) and isfinite(y) else None
    except (AttributeError, TypeError, ValueError):
        return None


class EventAnalysis:
    def __init__(self, rows, goalkeeper_ids):
        self.rows = rows
        self.goalkeeper_ids = set(goalkeeper_ids)
        self.snapshots = []
        self.periods = defaultdict(list)
        for index, row in enumerate(rows):
            players = {}
            for slot in range(1, 13):
                pid = row.get(f'StartPlayerId{slot}')
                if pid:
                    players[pid] = (row.get(f'StartPlayerTeam{slot}'), coordinate(row.get(f'StartPlayerCoordinates{slot}')))
            snapshot = {'row_index': index, 'timestamp': int(row['Timestamp']), 'period': int(row['Period']), 'players': players}
            self.snapshots.append(snapshot)
            self.periods[snapshot['period']].append(snapshot)
        self.times = {}
        for period, snapshots in self.periods.items():
            snapshots.sort(key=lambda s: (s['timestamp'], s['row_index']))
            self.times[period] = [s['timestamp'] for s in snapshots]

    def next_snapshot(self, origin, player_id, window_seconds):
        """First strictly later snapshot with player coordinates, within the same period."""
        snapshots = self.periods[origin['period']]
        start = bisect_right(self.times[origin['period']], origin['timestamp'])
        for snapshot in snapshots[start:]:
            if snapshot['timestamp'] > origin['timestamp'] + window_seconds * 1000:
                break
            if snapshot['players'].get(player_id, (None, None))[1] is not None:
                return snapshot
        return None

    def pressure(self, snapshot, player_id, side, radius):
        center = snapshot['players'].get(player_id, (None, None))[1]
        if center is None:
            return None
        opponent = 'Away' if side == 'Home' else 'Home'
        count = 0
        for pid, (team, xy) in snapshot['players'].items():
            if team != opponent or pid in self.goalkeeper_ids:
                continue
            if xy is None:
                return None  # Unknown opponent position must not silently reduce pressure.
            count += hypot(xy[0] - center[0], xy[1] - center[1]) <= radius
        return count


def pass_body_pressure(analysis, radius_m=3, window_seconds=2, min_evaluated=10):
    if radius_m <= 0 or window_seconds <= 0 or min_evaluated < 1:
        raise ValueError('KPI parameters must be positive')
    results, grouped = [], defaultdict(list)
    for index, row in enumerate(analysis.rows):
        if row['EventType'] != 'Pass':
            continue
        origin = analysis.snapshots[index]
        passer, receiver = row['EventPrimaryPlayerId'], row['EventSecondaryPlayerId']
        side = row['EventPrimaryTeam']
        result = {'id': f'row-{index + 1}-pass_body_pressure', 'metric_id': 'pass_body_pressure',
                  'source_row': index + 1, 'timestamp': row['Timestamp'], 'period': origin['period'],
                  'passer_id': passer, 'receiver_id': receiver, 'eligible': False,
                  'reception_timestamp': None, 'reception_source_row': None,
                  'pbp_pg': None, 'pbp_pe': None, 'value': None, 'exclusion_reason': None}
        if row['PassResult'] != 'Successful':
            result['exclusion_reason'] = 'unsuccessful_pass'
        elif not passer or not receiver or side not in ('Home', 'Away') or row['EventSecondaryTeam'] != side:
            result['exclusion_reason'] = 'unidentified_or_incompatible_players'
        else:
            result['eligible'] = True
            reception = analysis.next_snapshot(origin, receiver, window_seconds)
            pg = analysis.pressure(origin, passer, side, radius_m)
            result['pbp_pg'] = pg
            if reception is not None:
                result['reception_timestamp'] = str(reception['timestamp'])
                result['reception_source_row'] = reception['row_index'] + 1
                result['pbp_pe'] = analysis.pressure(reception, receiver, side, radius_m)
            if pg is None:
                result['exclusion_reason'] = 'missing_origin_coordinates'
            elif reception is None:
                result['exclusion_reason'] = 'no_reception_snapshot'
            elif result['pbp_pe'] is None:
                result['exclusion_reason'] = 'missing_reception_opponent_coordinates'
            else:
                result['value'] = pg - result['pbp_pe']
        results.append(result)
        if passer:
            grouped[passer].append(result)
    players = {}
    for pid, passes in grouped.items():
        eligible = [p for p in passes if p['eligible']]
        evaluated = [p for p in eligible if p['value'] is not None]
        n = len(evaluated)
        positive = sum(p['value'] > 0 for p in evaluated)
        players[pid] = {'eligible_passes': len(eligible), 'evaluated_passes': n,
                        'coverage': n / len(eligible) if eligible else None,
                        'mean': sum(p['value'] for p in evaluated) / n if n else None,
                        'positive_passes': positive, 'positive_share': positive / n if n else None,
                        'ranking_eligible': n >= min_evaluated,
                        'event_ids': [p['id'] for p in evaluated],
                        'positive_event_ids': [p['id'] for p in evaluated if p['value'] > 0]}
    return {'parameters': {'radius_m': radius_m, 'window_seconds': window_seconds, 'min_evaluated': min_evaluated},
            'events': results, 'players': players,
            'exclusions': dict(Counter(p['exclusion_reason'] for p in results if p['exclusion_reason']))}
