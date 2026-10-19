import unittest
from app.event_kpis import EventAnalysis, pass_packing, infer_attack_directions
from test_event_kpis import row


class PackingTests(unittest.TestCase):
    def calculate(self, start, end, sign=1, opponent='5,0'):
        origin = row(1000, event='Pass', players=[('p','Home',f'{start},0'),('o','Away',opponent),('g','Away','5,0'),('t','Home','5,0')])
        # Opponent movement after release must not affect packing.
        reception = row(2000,players=[('r','Home',f'{end},0'),('o','Away','100,0')])
        return pass_packing(EventAnalysis([origin,reception],{'g'}), {(1,'Home'):sign}, min_evaluated=1)

    def test_forward_backward_sideways_and_boundaries(self):
        self.assertEqual(self.calculate(0,10)['events'][0]['value'],1)
        self.assertEqual(self.calculate(10,0)['events'][0]['value'],-1)
        self.assertEqual(self.calculate(0,0)['events'][0]['value'],0)
        self.assertEqual(self.calculate(0,10,opponent='0,0')['events'][0]['value'],0)
        self.assertEqual(self.calculate(0,10,opponent='10,0')['events'][0]['value'],0)
        self.assertEqual(self.calculate(10,0,sign=-1)['events'][0]['value'],1)

    def test_missing_positions_excluded_from_denominator(self):
        result=self.calculate(0,10,opponent='')
        self.assertIsNone(result['events'][0]['value'])
        self.assertEqual(result['players']['p']['evaluated_passes'],0)
        self.assertIsNone(result['players']['p']['mean'])

    def test_direction_inference_and_unknown(self):
        rows=[row(1000,players=[('h','Home','-26,0'),('a','Away','26,0')]),
              row(2000,period=2,players=[('h','Home','26,0'),('a','Away','-26,0')])]
        self.assertEqual(infer_attack_directions(EventAnalysis(rows,{'h','a'})),
                         {(1,'Home'):1,(1,'Away'):-1,(2,'Home'):-1,(2,'Away'):1})
        p=row(1000,event='Pass',players=[('p','Home','0,0')])
        result=pass_packing(EventAnalysis([p],set()),{})['events'][0]
        self.assertEqual(result['exclusion_reason'],'unknown_attack_direction')

    def test_window_period_duplicates_and_success(self):
        p=row(1000,event='Pass',players=[('p','Home','0,0')])
        for later in [row(3001,players=[('r','Home','10,0')]),row(2000,period=2,players=[('r','Home','10,0')])]:
            result=pass_packing(EventAnalysis([p,later],set()),{(1,'Home'):1})
            self.assertEqual(result['events'][0]['exclusion_reason'],'no_reception_snapshot')
        rows=[p,dict(p),row(3000,players=[('r','Home','10,0')])]
        result=pass_packing(EventAnalysis(rows,set()),{(1,'Home'):1},min_evaluated=1)
        self.assertEqual(result['players']['p']['evaluated_passes'],2)
        self.assertNotEqual(result['events'][0]['id'],result['events'][1]['id'])
        p['PassResult']='Failed'
        self.assertFalse(pass_packing(EventAnalysis([p],set()),{})['events'][0]['eligible'])
