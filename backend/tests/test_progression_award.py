import unittest
from unittest.mock import Mock
from app.content import Content


class ProgressionAwardTests(unittest.TestCase):
    def content(self, players):
        c = Content.__new__(Content)
        c.derived_kpis = {'pass_packing': {'players': players, 'parameters': {'min_evaluated': 10}}}
        c.events = Mock(ids={('Team', 1): 'a', ('Team', 2): 'b'})
        c.archetypes, c.archetype_metrics, c.cards = {}, {}, {}
        c.match = {'events_source': 'Events'}
        c._build_card = lambda cfg: {**cfg, 'moments': []}
        return c

    def stats(self, mean, n=10):
        return dict(mean=mean, evaluated_passes=n, eligible_passes=n, total=mean*n, ranking_eligible=n>=10)

    def test_highest_mean_and_sample_threshold(self):
        c=self.content({'a':self.stats(2,9),'b':self.stats(1,10)})
        c._add_progression_card()
        self.assertEqual(c.cards['progression-master']['jersey'],2)
        self.assertIn('packing_positive_share',c.cards['progression-master']['attributes'])

    def test_tie_prefers_sample_then_id(self):
        c=self.content({'a':self.stats(1,11),'b':self.stats(1,10)})
        c._add_progression_card();self.assertEqual(c.cards['progression-master']['jersey'],1)
        c=self.content({'a':self.stats(1),'b':self.stats(1)})
        c._add_progression_card();self.assertEqual(c.cards['progression-master']['jersey'],2)

    def test_nonpositive_means_do_not_award(self):
        c=self.content({'a':self.stats(0),'b':self.stats(-1)})
        c._add_progression_card();self.assertFalse(c.cards)
