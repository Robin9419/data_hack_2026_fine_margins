import unittest
from app.event_kpis import EventAnalysis, blc_xg, controlled_zone_exits
from app.content import Content
from test_event_kpis import row

DIRECTIONS = {(1, 'Home'): 1, (1, 'Away'): -1, (2, 'Home'): -1, (2, 'Away'): 1}


def crossing(ts, side='Home', x=7.2, outcome='PossessionMaintained', movement='TowardsOpponent', period=1, pid='p'):
    r = row(ts, period, 'BluelineCrossing')
    r.update(EventPrimaryTeam=side, EventPrimaryPlayerId=pid, EventStartCoordinate=f'{x},0',
             BluelineCrossingResult=outcome, BluelineCrossingDirection=movement)
    return r


def shot(ts, xg='0.2', side='Home', zone='AwayTeamZone'):
    r = row(ts, event='Shot')
    r.update(ShotXG=xg, EventPrimaryTeam=side, EventPosition=zone)
    return r


def control(ts, zone='AwayTeamZone', state='HomeControl'):
    r = row(ts)
    r.update(PuckControlEndZone=zone, PuckControlState=state)
    return r


class ZoneKpiTests(unittest.TestCase):
    def blc(self, rows, **kwargs):
        return blc_xg(EventAnalysis(rows, {'g'}), attack_directions=DIRECTIONS, **kwargs)

    def exits(self, rows, directions=DIRECTIONS):
        return controlled_zone_exits(EventAnalysis(rows, {'g'}), attack_directions=directions)

    def test_recovery_rebounds_and_goal_not_double_counted(self):
        rows = [crossing(100), shot(200), control(300, state='AwayControl'),
                shot(350, '0.9', 'Away'), control(400), shot(500, '0.3'),
                row(510, event='Goal'), shot(520, '0.8')]
        result = self.blc(rows)['events'][0]
        self.assertAlmostEqual(result['value'], 0.5)
        self.assertEqual(result['shot_source_rows'], [2, 6])
        self.assertEqual(result['end_source_row'], 7)
        self.assertEqual(result['end_reason'], 'stoppage')

    def test_departure_reentry_and_first_outside_shot_excluded(self):
        rows = [crossing(100), shot(200), control(300, 'NeutralZone'), shot(400),
                crossing(500, pid='b'), shot(600, '0.3'), shot(700, '0.8', zone='NeutralZone')]
        result = self.blc(rows)
        self.assertAlmostEqual(result['events'][0]['value'], 0.2)
        self.assertAlmostEqual(result['events'][1]['value'], 0.3)
        self.assertEqual(result['events'][1]['end_source_row'], 7)

    def test_either_team_crossing_can_end_sequence(self):
        for departure in [crossing(200, movement='TowardsHome'), crossing(200, side='Away'),
                          crossing(200, side='Away', x=-7.1)]:
            events = self.blc([crossing(100), departure, shot(300)])['events']
            self.assertEqual(events[0]['value'], 0)
            self.assertEqual(events[0]['end_reason'], 'zone_departure')

    def test_missing_invalid_xg_and_unclosed_not_zero(self):
        for xg in ['', 'nan', 'inf', '-0.1', '1.1']:
            result = self.blc([crossing(100), shot(200, xg), row(300, event='StoppageOfPlay')])
            self.assertIsNone(result['events'][0]['value'])
            self.assertEqual(result['events'][0]['missing_xg_source_rows'], [2])
            self.assertEqual(result['players']['p']['evaluated_entries'], 0)
        self.assertIsNone(self.blc([crossing(100), shot(200)])['events'][0]['value'])
        zero = self.blc([crossing(100), shot(200, '0'), row(300, event='Faceoff')])['events'][0]
        self.assertEqual(zero['value'], 0)

    def test_side_period_orientation_and_nonentry_exclusions(self):
        rows = [crossing(100, side='Away', x=-7.1), shot(200, side='Away', zone='HomeTeamZone'),
                row(300, event='StoppageOfPlay'), crossing(400, x=-7.1, period=2),
                row(500, period=2, event='StoppageOfPlay')]
        events = self.blc(rows)['events']
        self.assertEqual([e['value'] for e in events], [0.2, 0])
        self.assertEqual(events[1]['attack_direction'], -1)
        self.assertFalse(self.blc([crossing(100, x=-7.1)])['events'][0]['eligible'])
        period_change = self.blc([crossing(100), row(200, period=2, event='StoppageOfPlay')])
        self.assertIsNone(period_change['events'][0]['value'])

    def test_preserve_occurrences_without_double_credit(self):
        entry = crossing(100)
        result = self.blc([entry, dict(entry), shot(200), row(300, event='StoppageOfPlay')])
        self.assertNotEqual(result['events'][0]['id'], result['events'][1]['id'])
        self.assertEqual(result['events'][1]['exclusion_reason'], 'overlapping_entry_without_departure')
        self.assertEqual(result['players']['p']['total'], 0.2)
        self.assertEqual(result['players']['p']['coverage'], 0.5)

    def test_known_outcomes_and_zero_entry_denominator(self):
        rows = [crossing(100, outcome='PossessionLost'), row(200, event='StoppageOfPlay'),
                crossing(300, outcome='PuckDumpedIn'), shot(400), row(500, event='StoppageOfPlay')]
        stats = self.blc(rows, min_evaluated=2)['players']['p']
        self.assertEqual(stats['evaluated_entries'], 2)
        self.assertEqual(stats['mean'], 0.1)
        self.assertTrue(stats['ranking_eligible'])
        self.assertFalse(self.blc(rows, min_evaluated=3)['players']['p']['ranking_eligible'])

    def test_none_crossing_and_penalty_do_not_end_sequence(self):
        rows = [crossing(100), crossing(200, side='Away', outcome='None'),
                dict(row(300, event='Penalty'), EventPosition='NeutralZone'), shot(400),
                row(500, event='StoppageOfPlay')]
        self.assertEqual(self.blc(rows)['events'][0]['value'], 0.2)

    def test_exit_successes_failures_and_supporting_subset(self):
        rows = [crossing(i * 100, x=-7.1, outcome=outcome) for i, outcome in enumerate(
            ['PossessionMaintained', 'PossessionLost', 'PuckDumpedIn', 'None', ''], 1)]
        stats = self.exits(rows)['players']['p']
        self.assertEqual(stats['attempted_exits'], 3)
        self.assertEqual(stats['eligible_exits'], 5)
        self.assertEqual(stats['coverage'], 0.6)
        self.assertEqual(stats['controlled_exits'], 1)
        self.assertAlmostEqual(stats['success_share'], 1 / 3)
        self.assertEqual(stats['controlled_event_ids'], ['row-1-controlled_zone_exits'])
        self.assertEqual(len(stats['event_ids']), 3)

    def test_unknown_direction_coordinates_players_and_goalkeepers(self):
        self.assertEqual(self.exits([crossing(100, x=-7.1)], {})['events'][0]['exclusion_reason'], 'unknown_attack_direction')
        for pid in ['', 'g']:
            self.assertFalse(self.exits([crossing(100, x=-7.1, pid=pid)])['events'][0]['eligible'])
        r = crossing(100, x=-7.1); r['EventStartCoordinate'] = ''
        self.assertEqual(self.exits([r])['events'][0]['exclusion_reason'], 'missing_crossing_coordinates')
        stats = self.exits([crossing(100, x=-7.1, outcome='None')])['players']['p']
        self.assertIsNone(stats['controlled_exits'])
        self.assertFalse(stats['ranking_eligible'])
        with self.assertRaises(ValueError):
            self.exits([], {(1, 'Home'): 0})
        with self.assertRaises(ValueError):
            self.blc([], min_evaluated=0)

    def test_unsorted_input_and_equal_timestamp_source_order(self):
        result = self.blc([shot(200), crossing(100), row(200, event='StoppageOfPlay')])
        self.assertEqual(result['events'][0]['shot_source_rows'], [1])
        self.assertEqual(result['events'][0]['value'], 0.2)


class ZoneContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = Content()

    def test_awards_ranked_from_real_events_and_category_registered(self):
        content = self.content
        for category in content.award_categories:
            if category['id'] != 'zone-entries-exits':
                continue
            for award in category['awards']:
                card = content.cards[award['id']]
                self.assertEqual(card['category_id'], category['id'])
                calculation = content.derived_kpis[award['derived']]
                candidates = [(pid, s) for pid, s in calculation['players'].items()
                              if s['ranking_eligible'] and s[award['aggregate']] is not None and s[award['aggregate']] > 0]
                winner = max(candidates, key=lambda item: (item[1][award['aggregate']], item[1][award['tie_break_aggregate']], item[0]))
                self.assertEqual(card['attributes'][0]['value'], winner[1][award['aggregate']])
                self.assertEqual(content.events.player_id(card['player']['team'], card['player']['jersey']), winner[0])
                moment_ids = {m['id'] for m in card['moments']}
                self.assertTrue(set(card['attributes'][0]['moment_ids']) <= moment_ids)
                self.assertEqual(card['attributes'][0]['match_rank'], 1)
                self.assertEqual(content.card_game[card['id']], content.tournament.final['id'])

    def test_sequence_video_window_and_total_audit(self):
        content = self.content
        shots = []
        for event in content.derived_kpis['blc_xg']['events']:
            if event['value'] is None:
                continue
            expected = sum(float(content.event_rows[i - 1]['ShotXG']) for i in event['shot_source_rows'])
            self.assertAlmostEqual(event['value'], expected)
            shots.extend(event['shot_source_rows'])
            moment = next(m for m in content.events.moments(event['player_id']) if m['id'] == event['id'])
            self.assertEqual(moment['clip_window'][0], -3)
            self.assertGreaterEqual(moment['clip_window'][1], (int(event['end_timestamp']) - int(event['timestamp'])) / 1000)
            self.assertIsNone(moment['broadcast'])
        self.assertEqual(len(shots), len(set(shots)))

    def test_cutter_unions_sequence_windows_and_skips_other_games(self):
        from types import SimpleNamespace
        from scripts.cut_clips import event_windows
        content = SimpleNamespace(recording={'windows': {'zone_entry': [-3, 8], 'shot': [-6, 3]}},
            event_rows=[{'Timestamp': '100'}], cards={
                'a': {'moments': [{'timestamp': '100', 'kind': 'zone_entry', 'clip_window': [-3, 45]}]},
                'b': {'moments': [{'timestamp': '100', 'kind': 'shot'}]},
                'base': {}, 'test': {'test_game': 'other', 'moments': [
                    {'timestamp': '100', 'kind': 'zone_entry', 'clip_window': [-9, 90]}]}})
        self.assertEqual(event_windows(content), {'100': (-6, 45)})
