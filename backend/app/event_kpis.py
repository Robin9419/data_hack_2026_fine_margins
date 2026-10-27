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


CROSSING_OUTCOMES = {'PossessionMaintained', 'PossessionLost', 'PuckDumpedIn'}
ZONE_NAMES = {'HomeTeamZone', 'AwayTeamZone', 'NeutralZone'}


def _crossing(analysis, index, directions):
    """Classify a provider-labelled crossing using its blue-line x and team direction.

    EventPosition can refer to either side of the line, so it cannot by itself
    distinguish entry from exit. None outcomes do not establish a puck crossing.
    """
    row = analysis.rows[index]
    side = row.get('EventPrimaryTeam')
    sign = directions.get((int(row['Period']), side))
    xy = coordinate(row.get('EventStartCoordinate'))
    movement = row.get('BluelineCrossingDirection')
    if side not in ('Home', 'Away'):
        return None, 'unknown_team'
    if sign not in (-1, 1):
        return None, 'unknown_attack_direction'
    if xy is None or xy[0] == 0:
        return None, 'missing_crossing_coordinates'
    if movement not in ('TowardsOpponent', 'TowardsHome'):
        return None, 'unknown_crossing_direction'
    offensive_line = sign * xy[0] > 0
    forward = movement == 'TowardsOpponent'
    kind = ('offensive_entry' if forward else 'offensive_exit') if offensive_line else (
        'defensive_exit' if forward else 'defensive_entry')
    return {'kind': kind, 'side': side, 'attack_direction': sign, 'x': xy[0]}, None


def _zone_result(row, index, metric_id):
    return {'id': f'row-{index + 1}-{metric_id}', 'metric_id': metric_id,
            'source_row': index + 1, 'timestamp': row['Timestamp'], 'period': int(row['Period']),
            'player_id': row.get('EventPrimaryPlayerId'), 'team': row.get('EventPrimaryTeam'),
            'crossing_kind': None, 'crossing_result': row.get('BluelineCrossingResult'),
            'eligible': False, 'value': None, 'exclusion_reason': None}


def controlled_zone_exits(analysis, attack_directions=None):
    """Count defensive puck crossings whose exported outcome confirms retained possession."""
    directions = infer_attack_directions(analysis) if attack_directions is None else attack_directions
    if any(direction not in (-1, 1) for direction in directions.values()):
        raise ValueError('Attack directions must be +1 or -1')
    results, grouped = [], defaultdict(list)
    for index, row in enumerate(analysis.rows):
        if row['EventType'] != 'BluelineCrossing':
            continue
        result = _zone_result(row, index, 'controlled_zone_exits')
        crossing, error = _crossing(analysis, index, directions)
        if crossing:
            result.update(crossing_kind=crossing['kind'], attack_direction=crossing['attack_direction'])
        if error:
            result['exclusion_reason'] = error
        elif crossing['kind'] != 'defensive_exit':
            result['exclusion_reason'] = 'not_defensive_exit'
        elif not result['player_id'] or result['player_id'] in analysis.goalkeeper_ids:
            result['exclusion_reason'] = 'unidentified_or_goalkeeper'
        else:
            result['eligible'] = True
            if result['crossing_result'] not in CROSSING_OUTCOMES:
                result['exclusion_reason'] = 'unknown_crossing_outcome'
            else:
                result['value'] = int(result['crossing_result'] == 'PossessionMaintained')
            grouped[result['player_id']].append(result)
        results.append(result)
    players = {}
    for pid, exits in grouped.items():
        evaluated = [event for event in exits if event['value'] is not None]
        n = len(evaluated)
        successful = [event for event in evaluated if event['value'] == 1]
        players[pid] = {'eligible_exits': len(exits), 'attempted_exits': n, 'evaluated_exits': n,
                       'controlled_exits': len(successful) if n else None,
                       'success_share': len(successful) / n if n else None,
                       'coverage': n / len(exits), 'ranking_eligible': n > 0,
                       'event_ids': [event['id'] for event in evaluated],
                       'controlled_event_ids': [event['id'] for event in successful]}
    return {'parameters': {'success_outcome': 'PossessionMaintained', 'retention_window_seconds': None,
                           'attack_directions': {f'{p}:{s}': d for (p, s), d in directions.items()}},
            'events': results, 'players': players,
            'exclusions': dict(Counter(e['exclusion_reason'] for e in results if e['exclusion_reason']))}


def blc_xg(analysis, attack_directions=None, min_evaluated=3):
    """Own-team shot xG after an offensive puck entry, until zone departure or stoppage.

    Opponent possession inside the zone never ends a sequence. Each shot belongs
    to at most one entry. Missing xG or an unclosed sequence makes the total unknown.
    """
    if min_evaluated < 1:
        raise ValueError('Minimum evaluated entries must be positive')
    directions = infer_attack_directions(analysis) if attack_directions is None else attack_directions
    if any(direction not in (-1, 1) for direction in directions.values()):
        raise ValueError('Attack directions must be +1 or -1')
    results, active = [], {}

    def finish(side, row=None, index=None, reason='unclosed_sequence'):
        result = active.pop(side)
        result.update(end_timestamp=row['Timestamp'] if row else None,
                      end_source_row=index + 1 if index is not None else None, end_reason=reason)
        if reason == 'unclosed_sequence':
            result['exclusion_reason'] = reason
        elif result['missing_xg_source_rows']:
            result['exclusion_reason'] = 'missing_or_invalid_sequence_xg'
        else:
            result['value'] = result['known_xg_total']

    ordered = sorted(enumerate(analysis.rows), key=lambda item: (int(item[1]['Timestamp']), item[0]))
    for index, row in ordered:
        period, kind = int(row['Period']), row['EventType']
        for side in list(active):
            if active[side]['period'] != period:
                finish(side, reason='unclosed_sequence')
        crossing, error = _crossing(analysis, index, directions) if kind == 'BluelineCrossing' else (None, None)
        meaningful_crossing = crossing and row.get('BluelineCrossingResult') in CROSSING_OUTCOMES
        for side in list(active):
            offensive_zone = 'AwayTeamZone' if side == 'Home' else 'HomeTeamZone'
            departure = False
            if meaningful_crossing:
                departure = (directions[(period, side)] * crossing['x'] < 0
                             or (crossing['side'] == side and crossing['kind'] == 'offensive_exit')
                             or (crossing['side'] != side and crossing['kind'] == 'defensive_exit'))
            elif kind == 'PuckControl':
                end_zone = row.get('PuckControlEndZone')
                departure = end_zone in ZONE_NAMES and end_zone != offensive_zone
            elif kind in ('Pass', 'Shot', 'Dump', 'Clear', 'Goal'):
                # These event locations describe puck actions. Player-only crossings
                # and penalty locations must never be used as puck departure evidence.
                zone = row.get('EventPosition')
                departure = zone in ZONE_NAMES and zone != offensive_zone
            if kind in ('StoppageOfPlay', 'Faceoff', 'Goal'):
                # A Goal row follows its Shot; do not count it as another shot.
                finish(side, row, index, 'stoppage')
            elif departure:
                finish(side, row, index, 'zone_departure')

        if kind == 'BluelineCrossing':
            result = _zone_result(row, index, 'blc_xg')
            result.update(end_timestamp=None, end_source_row=None, end_reason=None,
                          shot_source_rows=[], shot_timestamps=[], missing_xg_source_rows=[], known_xg_total=0.0)
            if crossing:
                result.update(crossing_kind=crossing['kind'], attack_direction=crossing['attack_direction'])
            if error:
                result['exclusion_reason'] = error
            elif crossing['kind'] != 'offensive_entry':
                result['exclusion_reason'] = 'not_offensive_entry'
            elif not result['player_id'] or result['player_id'] in analysis.goalkeeper_ids:
                result['exclusion_reason'] = 'unidentified_or_goalkeeper'
            elif result['crossing_result'] not in CROSSING_OUTCOMES:
                result['exclusion_reason'] = 'unknown_crossing_outcome'
            else:
                result['eligible'] = True
                side = crossing['side']
                if side in active:
                    result['exclusion_reason'] = 'overlapping_entry_without_departure'
                else:
                    active[side] = result
            results.append(result)
        elif kind == 'Shot' and row.get('EventPrimaryTeam') in active:
            result = active[row['EventPrimaryTeam']]
            result['shot_source_rows'].append(index + 1)
            result['shot_timestamps'].append(row['Timestamp'])
            try:
                xg = float(row.get('ShotXG'))
            except (TypeError, ValueError):
                xg = None
            if xg is None or not isfinite(xg) or not 0 <= xg <= 1:
                result['missing_xg_source_rows'].append(index + 1)
            else:
                result['known_xg_total'] += xg
    for side in list(active):
        finish(side)
    grouped = defaultdict(list)
    for result in results:
        if result['eligible']:
            grouped[result['player_id']].append(result)
    players = {}
    for pid, entries in grouped.items():
        evaluated = [entry for entry in entries if entry['value'] is not None]
        n = len(evaluated)
        players[pid] = {'eligible_entries': len(entries), 'evaluated_entries': n,
                       'total': sum(e['value'] for e in evaluated) if n else None,
                       'mean': sum(e['value'] for e in evaluated) / n if n else None,
                       'shot_entries': sum(bool(e['shot_source_rows']) for e in evaluated),
                       'coverage': n / len(entries), 'ranking_eligible': n >= min_evaluated,
                       'event_ids': [e['id'] for e in evaluated]}
    return {'parameters': {'min_evaluated': min_evaluated, 'opponent_control_ends_sequence': False,
                           'entry_outcomes': sorted(CROSSING_OUTCOMES),
                           'attack_directions': {f'{p}:{s}': d for (p, s), d in directions.items()}},
            'events': results, 'players': players,
            'exclusions': dict(Counter(e['exclusion_reason'] for e in results if e['exclusion_reason']))}


def interceptions(analysis):
    """Provider-labelled intercepted passes, credited to the opposing secondary skater."""
    results, grouped = [], defaultdict(list)
    skaters = {row.get(f'Event{role}PlayerId') for row in analysis.rows for role in ('Primary', 'Secondary')
               if row.get(f'Event{role}PlayerId') and row.get(f'Event{role}Team') in ('Home', 'Away')}
    skaters -= analysis.goalkeeper_ids
    for index, row in enumerate(analysis.rows):
        if row['EventType'] != 'Pass':
            continue
        passer, interceptor = row.get('EventPrimaryPlayerId'), row.get('EventSecondaryPlayerId')
        side, other = row.get('EventPrimaryTeam'), row.get('EventSecondaryTeam')
        result = {'id': f'row-{index + 1}-interceptions', 'metric_id': 'interceptions',
                  'source_row': index + 1, 'timestamp': row['Timestamp'], 'period': int(row['Period']),
                  'passer_id': passer, 'interceptor_id': interceptor, 'player_id': interceptor,
                  'team': other, 'pass_result': row.get('PassResult'), 'eligible': False,
                  'value': None, 'exclusion_reason': None}
        if row.get('PassResult') != 'Intercepted':
            result['exclusion_reason'] = 'not_intercepted'
        else:
            result['eligible'] = True
            if not passer or not interceptor:
                result['exclusion_reason'] = 'unidentified_players'
            elif side not in ('Home', 'Away') or other not in ('Home', 'Away') or side == other or passer == interceptor:
                result['exclusion_reason'] = 'incompatible_players_or_teams'
            elif interceptor in analysis.goalkeeper_ids:
                result['exclusion_reason'] = 'goalkeeper_interception'
            else:
                result['value'] = 1
                grouped[interceptor].append(result)
        results.append(result)
    players = {pid: {'interceptions': len(grouped[pid]), 'ranking_eligible': True,
                     'event_ids': [event['id'] for event in grouped[pid]]} for pid in sorted(skaters)}
    eligible = sum(event['eligible'] for event in results)
    evaluated = sum(event['value'] is not None for event in results)
    return {'parameters': {'pass_result': 'Intercepted', 'credited_role': 'Secondary',
                           'zones': 'all', 'goalkeepers_excluded': True},
            'events': results, 'players': players, 'eligible_events': eligible, 'evaluated_events': evaluated,
            'coverage': evaluated / eligible if eligible else None,
            'exclusions': dict(Counter(e['exclusion_reason'] for e in results if e['exclusion_reason']))}
