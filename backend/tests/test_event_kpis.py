import unittest
from app.event_kpis import EventAnalysis, pass_body_pressure


def row(ts, period=1, event='PuckControl', players=()):
    r = dict(Timestamp=str(ts), Period=str(period), EventType=event, PassResult='Successful',
             EventPrimaryPlayerId='p', EventSecondaryPlayerId='r', EventPrimaryTeam='Home', EventSecondaryTeam='Home')
    for i, (pid, team, xy) in enumerate(players, 1):
        r.update({f'StartPlayerId{i}': pid, f'StartPlayerTeam{i}': team, f'StartPlayerCoordinates{i}': xy})
    return r


class PressureTests(unittest.TestCase):
    def calculate(self, rows):
        return pass_body_pressure(EventAnalysis(rows, {'g'}), min_evaluated=1)

    def test_opponents_boundary_goalkeeper_and_same_snapshot(self):
        first = row(1000, event='Pass', players=[('p','Home','0,0'),('r','Home','10,0'),
                    ('o','Away','3,0'),('g','Away','0,0'),('t','Home','0,0')])
        later = row(3000, players=[('r','Home','20,0'),('o','Away','10,0'),('g','Away','20,0')])
        result = self.calculate([first, later])['events'][0]
        self.assertEqual((result['pbp_pg'], result['pbp_pe'], result['value']), (1,0,1))
        self.assertEqual(result['reception_source_row'], 2)

    def test_window_period_and_equal_timestamp(self):
        first = row(1000, event='Pass', players=[('p','Home','0,0')])
        for later in [row(1000, players=[('r','Home','0,0')]),
                      row(3001, players=[('r','Home','0,0')]),
                      row(2000, period=2, players=[('r','Home','0,0')])]:
            self.assertEqual(self.calculate([first,later])['events'][0]['exclusion_reason'], 'no_reception_snapshot')

    def test_missing_opponent_is_not_zero(self):
        first = row(1000, event='Pass', players=[('p','Home','0,0'),('o','Away','')])
        later = row(2000, players=[('r','Home','0,0')])
        result = self.calculate([first,later])
        self.assertIsNone(result['events'][0]['value'])
        self.assertEqual(result['players']['p']['evaluated_passes'], 0)

    def test_first_valid_snapshot_and_preserve_occurrences(self):
        first = row(1000, event='Pass', players=[('p','Home','0,0')])
        rows = [first, dict(first), row(1500,players=[('r','Home','')]), row(1800,players=[('r','Home','0,0')])]
        results = self.calculate(rows)['events']
        self.assertEqual(len(results),2)
        self.assertNotEqual(results[0]['id'],results[1]['id'])
        self.assertEqual(results[0]['reception_timestamp'],'1800')

    def test_failed_pass_excluded(self):
        first = row(1000,event='Pass');first['PassResult']='Intercepted'
        self.assertFalse(self.calculate([first])['events'][0]['eligible'])


if __name__ == '__main__':
    unittest.main()
