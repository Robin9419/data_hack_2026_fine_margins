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


def infer_attack_directions(analysis):
    """Infer each side's attacking x sign from the opposing goalkeeper's median x.

    Coordinates may already be normalized across periods. Missing/ambiguous evidence
    leaves direction unavailable rather than assuming that teams switch x signs.
    """
    from statistics import median
    positions = defaultdict(list)
    for snapshot in analysis.snapshots:
        for pid, (side, xy) in snapshot['players'].items():
            if pid in analysis.goalkeeper_ids and xy and side in ('Home', 'Away'):
                positions[(snapshot['period'], side)].append(xy[0])
    directions = {}
    for period in analysis.periods:
        home = positions.get((period, 'Home'), [])
        away = positions.get((period, 'Away'), [])
        if not home or not away:
            continue
        hx, ax = median(home), median(away)
        if abs(hx) < 10 or abs(ax) < 10 or hx * ax >= 0:
            continue
        directions[(period, 'Home')] = 1 if ax > 0 else -1
        directions[(period, 'Away')] = 1 if hx > 0 else -1
    return directions


def pass_packing(analysis, attack_directions=None, window_seconds=2, min_evaluated=10):
    """Signed longitudinal packing with opponent positions frozen at pass release."""
    if window_seconds <= 0 or min_evaluated < 1:
        raise ValueError('KPI parameters must be positive')
    directions = infer_attack_directions(analysis) if attack_directions is None else attack_directions
    if any(direction not in (-1, 1) for direction in directions.values()):
        raise ValueError('Attack directions must be +1 or -1')
    # Reuse the established successful-pass eligibility, source IDs and snapshot timing.
    base = pass_body_pressure(analysis, window_seconds=window_seconds, min_evaluated=min_evaluated)
    results, grouped = [], defaultdict(list)
    for pressure in base['events']:
        result = {k: v for k, v in pressure.items() if k not in ('pbp_pg', 'pbp_pe')}
        result.update(id=f"row-{result['source_row']}-pass_packing", metric_id='pass_packing',
                      value=None, passer_x=None, receiver_x=None, attack_direction=None,
                      bypassed_opponent_ids=[], restored_opponent_ids=[])
        row = analysis.rows[result['source_row'] - 1]
        side = row['EventPrimaryTeam']
        if result['eligible']:
            result['exclusion_reason'] = None
            origin = analysis.snapshots[result['source_row'] - 1]
            reception = analysis.next_snapshot(origin, result['receiver_id'], window_seconds)
            passer_xy = origin['players'].get(result['passer_id'], (None, None))[1]
            direction = directions.get((origin['period'], side))
            result['attack_direction'] = direction
            if direction is None:
                result['exclusion_reason'] = 'unknown_attack_direction'
            elif passer_xy is None:
                result['exclusion_reason'] = 'missing_origin_coordinates'
            elif reception is None:
                result['exclusion_reason'] = 'no_reception_snapshot'
            else:
                receiver_xy = reception['players'][result['receiver_id']][1]
                result.update(passer_x=passer_xy[0], receiver_x=receiver_xy[0])
                start, end = direction * passer_xy[0], direction * receiver_xy[0]
                opposite = 'Away' if side == 'Home' else 'Home'
                for pid, (team, xy) in origin['players'].items():
                    if team != opposite or pid in analysis.goalkeeper_ids:
                        continue
                    if xy is None:
                        result['exclusion_reason'] = 'missing_origin_opponent_coordinates'
                        break
                    x = direction * xy[0]
                    if start < x < end:
                        result['bypassed_opponent_ids'].append(pid)
                    elif end < x < start:
                        result['restored_opponent_ids'].append(pid)
                if result['exclusion_reason'] is None:
                    result['value'] = len(result['bypassed_opponent_ids']) - len(result['restored_opponent_ids'])
        results.append(result)
        if result['passer_id']:
            grouped[result['passer_id']].append(result)
    players = {}
    for pid, passes in grouped.items():
        eligible = [p for p in passes if p['eligible']]
        evaluated = [p for p in eligible if p['value'] is not None]
        n = len(evaluated)
        positive = [p for p in evaluated if p['value'] > 0]
        players[pid] = {'eligible_passes': len(eligible), 'evaluated_passes': n,
                       'coverage': n / len(eligible) if eligible else None,
                       'mean': sum(p['value'] for p in evaluated) / n if n else None,
                       'total': sum(p['value'] for p in evaluated) if n else None,
                       'positive_passes': len(positive), 'positive_share': len(positive) / n if n else None,
                       'ranking_eligible': n >= min_evaluated,
                       'event_ids': [p['id'] for p in evaluated], 'positive_event_ids': [p['id'] for p in positive]}
    return {'parameters': {'window_seconds': window_seconds, 'min_evaluated': min_evaluated,
                           'opponent_snapshot': 'pass_release', 'axis': 'x', 'boundary': 'strict',
                           'attack_directions': {f'{period}:{side}': sign for (period, side), sign in directions.items()}},
            'events': results, 'players': players,
            'exclusions': dict(Counter(p['exclusion_reason'] for p in results if p['exclusion_reason']))}


def expected_assists(analysis, window_seconds=4):
    """Credit the final completed pass before a shot; opponent control breaks attribution."""
    if window_seconds <= 0:
        raise ValueError('Window must be positive')
    ordered = sorted(enumerate(analysis.rows), key=lambda item: (int(item[1]['Timestamp']), item[0]))
    results, grouped = [], defaultdict(list)
    for position, (index, shot) in enumerate(ordered):
        if shot['EventType'] != 'Shot':
            continue
        result = {'id': f'row-{index + 1}-expected_assists', 'metric_id': 'expected_assists',
                  'source_row': index + 1, 'timestamp': shot['Timestamp'], 'period': int(shot['Period']),
                  'shooter_id': shot['EventPrimaryPlayerId'], 'passer_id': None,
                  'pass_source_row': None, 'pass_timestamp': None, 'value': None,
                  'eligible': False, 'exclusion_reason': None}
        try:
            xg = float(shot['ShotXG'])
        except (ValueError, TypeError):
            xg = None
        side = shot['EventPrimaryTeam']
        if xg is None or not isfinite(xg) or not 0 <= xg <= 1:
            result['exclusion_reason'] = 'missing_or_invalid_xg'
        elif not result['shooter_id'] or side not in ('Home', 'Away'):
            result['exclusion_reason'] = 'unidentified_shooter'
        else:
            result['eligible'] = True
            opposite = 'Away' if side == 'Home' else 'Home'
            shot_ts = int(shot['Timestamp'])
            result['exclusion_reason'] = 'no_qualifying_pass'
            for pass_index, previous in reversed(ordered[:position]):
                if int(previous['Timestamp']) < shot_ts - window_seconds * 1000:
                    break
                if int(previous['Period']) != result['period']:
                    continue
                if previous['EventType'] == 'PuckControl' and previous['PuckControlState'] == opposite + 'Control':
                    result['exclusion_reason'] = 'opponent_control'
                    break
                # A completed opponent pass also establishes possession even without a control row.
                if previous['EventType'] == 'Pass' and previous['PassResult'] == 'Successful' and previous['EventPrimaryTeam'] == opposite:
                    result['exclusion_reason'] = 'opponent_control'
                    break
                if (previous['EventType'] == 'Pass' and previous['PassResult'] == 'Successful'
                        and int(previous['Timestamp']) < shot_ts
                        and previous['EventPrimaryTeam'] == side and previous['EventSecondaryTeam'] == side
                        and previous['EventSecondaryPlayerId'] == result['shooter_id']
                        and previous['EventPrimaryPlayerId'] and previous['EventPrimaryPlayerId'] != result['shooter_id']):
                    result.update(passer_id=previous['EventPrimaryPlayerId'], pass_source_row=pass_index + 1,
                                  pass_timestamp=previous['Timestamp'], value=xg, exclusion_reason=None)
                    break
        results.append(result)
        if result['passer_id']:
            grouped[result['passer_id']].append(result)
    players = {}
    for pid, shots in grouped.items():
        n = len(shots)
        players[pid] = {'total': sum(s['value'] for s in shots), 'mean': sum(s['value'] for s in shots) / n,
                       'assisted_shots': n, 'eligible_passes': n, 'evaluated_passes': n,
                       'coverage': 1.0, 'ranking_eligible': True, 'event_ids': [s['id'] for s in shots]}
    return {'parameters': {'window_seconds': window_seconds, 'attribution': 'last_successful_pass',
                           'opponent_control_breaks_attribution': True},
            'events': results, 'players': players,
            'exclusions': dict(Counter(s['exclusion_reason'] for s in results if s['exclusion_reason']))}
