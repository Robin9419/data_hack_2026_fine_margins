import copy
import unittest
from unittest import mock
from app import main
from app.content import Content
from app.event_kpis import EventAnalysis, interceptions
from app.events import clip_window_kind
from test_event_kpis import row


def passed(ts, passer='p', defender='d', side='Home', other='Away', result='Intercepted', period=1):
    r = row(ts, period, 'Pass')
    r.update(EventPrimaryPlayerId=passer, EventSecondaryPlayerId=defender,
             EventPrimaryTeam=side, EventSecondaryTeam=other, PassResult=result)
    return r


class InterceptionTests(unittest.TestCase):
    def calculate(self, rows):
        return interceptions(EventAnalysis(rows, {'g'}))

    def test_credit_opponent_both_directions_and_periods(self):
        result = self.calculate([passed(100), passed(200, 'd', 'p', 'Away', 'Home', period=2)])
        self.assertEqual(result['players']['d']['interceptions'], 1)
        self.assertEqual(result['players']['p']['interceptions'], 1)
        self.assertEqual(result['events'][0]['player_id'], 'd')
        self.assertEqual(result['events'][1]['period'], 2)
        self.assertEqual(result['coverage'], 1)

    def test_other_pass_outcomes_do_not_count(self):
        for outcome in ['Successful', 'Failed', '', 'Unknown']:
            result = self.calculate([passed(100, result=outcome)])
            self.assertEqual(result['players']['d']['interceptions'], 0)
            self.assertEqual(result['players']['d']['event_ids'], [])
            self.assertIsNone(result['events'][0]['value'])
            self.assertFalse(result['events'][0]['eligible'])
        self.assertIsNone(result['coverage'])

    def test_unknown_players_same_team_and_goalkeepers_excluded(self):
        result = self.calculate([passed(100, defender=''), passed(200, passer=''),
            passed(300, other='Home'), passed(400, other=''), passed(500, defender='p'), passed(600, defender='g')])
        self.assertEqual(result['eligible_events'], 6)
        self.assertEqual(result['evaluated_events'], 0)
        self.assertEqual(result['coverage'], 0)
        self.assertTrue(all(event['value'] is None for event in result['events']))
        self.assertNotIn('g', result['players'])
        self.assertEqual(result['events'][-1]['exclusion_reason'], 'goalkeeper_interception')

    def test_occurrences_preserved_nonpasses_ignored(self):
        p = passed(100)
        result = self.calculate([p, dict(p), row(150, event='Shot'), row(200)])
        self.assertEqual(len(result['events']), 2)
        self.assertNotEqual(result['events'][0]['id'], result['events'][1]['id'])
        self.assertEqual(result['players']['d']['interceptions'], 2)
        self.assertEqual(self.calculate([])['players'], {})


class DefendingContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = Content()

    def test_winners_match_kpis_and_explicit_tie_breaks(self):
        c = self.content
        counts = c.derived_kpis['interceptions']['players']
        pcw = {c.events.player_id(r['Team'], int(r['Jersey'])): int(r['PCW']) for r in c.rows}
        for cid, key in [('puck-hunter', lambda pid: (pcw[pid], counts[pid]['interceptions'], pid)),
                         ('passing-lane-guardian', lambda pid: (counts[pid]['interceptions'], pcw[pid], pid))]:
            expected = max(pcw, key=key)
            card = c.cards[cid]
            self.assertEqual(c.events.player_id(card['player']['team'], card['player']['jersey']), expected)
            self.assertEqual(card['attributes'][0]['value'], key(expected)[0])
            self.assertEqual(card['attributes'][0]['match_rank'], 1)
        self.assertIsNone(c.cards['puck-hunter']['attributes'][0]['moment_ids'])
        self.assertIsNone(c.cards['puck-hunter']['video'])
        self.assertEqual(c.cards['puck-hunter']['source'], c.match['source'])

    def test_79_interceptions_and_supporting_video_roles(self):
        c = self.content
        calculation = c.derived_kpis['interceptions']
        self.assertEqual(calculation['evaluated_events'], 79)
        self.assertEqual(sum(s['interceptions'] for s in calculation['players'].values()), 79)
        self.assertEqual(calculation['coverage'], 1)
        card = c.cards['passing-lane-guardian']
        pid = c.events.player_id(card['player']['team'], card['player']['jersey'])
        ids = card['attributes'][0]['moment_ids']
        self.assertEqual(len(ids), calculation['players'][pid]['interceptions'])
        moments = {m['id']: m for m in card['moments']}
        for id in ids:
            m = moments[id]
            self.assertEqual(m['kind'], 'interception')
            self.assertEqual(m['kpi']['interceptor_id'], pid)
            self.assertEqual(m['timestamp'], c.event_rows[m['kpi']['source_row'] - 1]['Timestamp'])
            self.assertIsNone(m['broadcast'])
        self.assertEqual(clip_window_kind('interception'), 'pass')

    def test_defending_category_and_final_availability(self):
        c = self.content
        category = next(cat for cat in c.award_categories if cat['id'] == 'defending')
        self.assertIn('Shot Blocker', category['existing_awards'])
        for cid in ['puck-hunter', 'passing-lane-guardian']:
            self.assertEqual(c.cards[cid]['category_id'], 'defending')
            self.assertEqual(c.card_game[cid], c.tournament.final['id'])
        blockers = [card for card in c.cards.values() if card['title'] == 'Shot Blocker']
        self.assertTrue(blockers)
        self.assertTrue(all(card['category_id'] == 'defending' for card in blockers))

    def candidate_content(self, value):
        c = copy.copy(self.content)
        c.cards = {}
        c.award_categories = [cat for cat in c.award_categories if cat['id'] == 'defending']
        c.rows = [{**r, 'PCW': str(value)} for r in c.rows]
        c.derived_kpis = copy.deepcopy(c.derived_kpis)
        for stats in c.derived_kpis['interceptions']['players'].values():
            stats['interceptions'] = value
        return c

    def test_no_positive_performance_omits_cards(self):
        c = self.candidate_content(0)
        c._add_category_cards()
        self.assertEqual(c.cards, {})

    def test_equal_counts_resolve_by_player_id_without_mutating_analysis(self):
        c = self.candidate_content(1)
        before = copy.deepcopy(c.derived_kpis['interceptions'])
        expected = max(c.events.player_id(r['Team'], int(r['Jersey'])) for r in c.rows)
        c._add_category_cards()
        for cid in ['puck-hunter', 'passing-lane-guardian']:
            card = c.cards[cid]
            self.assertEqual(c.events.player_id(card['player']['team'], card['player']['jersey']), expected)
        self.assertEqual(c.derived_kpis['interceptions'], before)

    def test_analysis_endpoint_and_independent_category_policy(self):
        with mock.patch.object(main, 'get_content', return_value=self.content):
            self.assertIs(main.interception_analysis({}), self.content.derived_kpis['interceptions'])
            self.assertEqual(main.award_categories({})['selection_policy'], 'independent_awards')
