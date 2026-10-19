import unittest
from app.event_kpis import EventAnalysis, expected_assists
from test_event_kpis import row


class ExpectedAssistTests(unittest.TestCase):
    def pass_row(self, ts, pid='a'):
        p=row(ts,event='Pass');p['EventPrimaryPlayerId']=pid;p['EventSecondaryPlayerId']='s';return p

    def shot(self, ts=5000, xg='0.2', period=1):
        s=row(ts,period,event='Shot');s['EventPrimaryPlayerId']='s';s['ShotXG']=xg;return s

    def calculate(self, rows):
        return expected_assists(EventAnalysis(rows,set()))

    def test_last_pass_once_and_inclusive_window(self):
        result=self.calculate([self.pass_row(1000),self.pass_row(2000,'b'),self.shot()])
        self.assertEqual(result['events'][0]['passer_id'],'b')
        self.assertEqual(result['players']['b']['total'],0.2)
        self.assertEqual(self.calculate([self.pass_row(1000),self.shot()])['events'][0]['value'],0.2)

    def test_opponent_control_cancels_but_new_pass_restores(self):
        control=row(2500);control['PuckControlState']='AwayControl'
        self.assertEqual(self.calculate([self.pass_row(1000),control,self.shot()])['events'][0]['exclusion_reason'],'opponent_control')
        self.assertEqual(self.calculate([self.pass_row(1000),control,self.pass_row(3000,'b'),self.shot()])['events'][0]['passer_id'],'b')
        control['PuckControlState']='Contested'
        self.assertEqual(self.calculate([self.pass_row(1000),control,self.shot()])['events'][0]['value'],0.2)

    def test_missing_xg_failed_pass_period_and_window(self):
        self.assertIsNone(self.calculate([self.pass_row(1000),self.shot(xg='')])['events'][0]['value'])
        self.assertIsNone(self.calculate([self.pass_row(999),self.shot()])['events'][0]['value'])
        self.assertIsNone(self.calculate([self.pass_row(1000),self.shot(period=2)])['events'][0]['value'])
        p=self.pass_row(1000);p['PassResult']='Failed'
        self.assertIsNone(self.calculate([p,self.shot()])['events'][0]['value'])

    def test_goal_row_not_counted_and_zero_xg_valid(self):
        goal=row(5100,event='Goal')
        result=self.calculate([self.pass_row(1000),self.shot(xg='0'),goal])
        self.assertEqual(len(result['events']),1)
        self.assertEqual(result['events'][0]['value'],0)
