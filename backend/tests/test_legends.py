import math
import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import db, main
from app.content import get_content


class LegendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(db, 'DB_PATH', Path(self.tmp.name) / 'test.sqlite3')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        db.init_db()
        self.content = get_content()
        # After the tournament, so every club has all its cards.
        self.user = {**db.get_or_create_user(f'u{random.random()}')[0], 'stage': 'post'}
        self.uid = self.user['id']
        self.available = self.content.available(self.content.tournament.played('post'))

    def legends_of(self, team):
        return {cid for cid, c in self.content.cards.items() if c['type'] == 'legend' and c['player']['team'] == team}

    def owned_legends(self, team):
        return self.legends_of(team) & set(db.owned_cards(self.uid))

    def test_every_team_has_three_legends(self):
        for team in main.TEAMS:
            self.assertEqual(len(self.legends_of(team)), 3, team)

    def test_one_legend_per_threshold_and_all_at_100_percent(self):
        team = 'HC Davos'
        club = self.content.club_cards(team, self.available)
        steps = [math.ceil(t * len(club)) for t in self.content.legend_thresholds]
        for i, cid in enumerate(club, start=1):
            db.grant_card(self.uid, cid, 'standard')
            awarded = main.award_legends(self.user)
            expected = sum(i >= n for n in steps)
            self.assertEqual(len(self.owned_legends(team)), expected, f'after {i} of {len(club)} cards')
            self.assertEqual(len(awarded), 1 if i in steps else 0)
            self.assertTrue(all(c['player']['team'] == team for c in awarded))
        self.assertEqual(self.owned_legends(team), self.legends_of(team))
        self.assertEqual(main.award_legends(self.user), [])

    def test_legends_stay_when_the_collection_shrinks(self):
        team = 'HIFK'
        self.user['stage'] = 'pre'  # before the tournament the club is its base cards
        club = self.content.club_cards(team, self.content.available(set()))
        db.grant_cards(self.uid, club)
        main.award_legends(self.user)
        self.assertEqual(len(self.owned_legends(team)), 3)
        db.remove_copies(self.uid, club[:12])
        self.assertEqual(main.award_legends(self.user), [])
        self.assertEqual(len(self.owned_legends(team)), 3)

    def test_daily_card_reports_legend_in_pack(self):
        team = 'Team Canada'
        club = self.content.club_cards(team, self.available)
        need = math.ceil(self.content.legend_thresholds[0] * len(club))
        db.grant_cards(self.uid, club[: need - 1])
        with mock.patch.object(main.random, 'choice', return_value=club[need - 1]):
            pack = main.daily_claim(self.user)['pack']
        self.assertEqual([c['type'] for c in pack], ['base', 'base', 'base', 'legend'])

    def test_legends_are_never_traded_for(self):
        db.grant_cards(self.uid, list(self.content.cards)[:5])
        pool = main.tradeable_cards(self.user, [])
        self.assertFalse(any(self.content.cards[cid]['type'] == 'legend' for cid in pool))

    def test_club_grows_with_the_games_it_plays(self):
        team = 'HC Davos'
        sizes = [len(self.content.club_cards(team, self.content.available(self.content.tournament.played(stage))))
                 for stage in self.content.tournament.stages]
        self.assertEqual(sizes[0], 22)  # before the tournament: the base cards only
        self.assertEqual(sizes, sorted(sizes))
        self.assertGreater(sizes[-1], sizes[0])

    def test_locked_legend_hides_the_player(self):
        cid = next(iter(self.legends_of('HC Davos')))
        summary = self.content.card_summary(self.content.cards[cid])
        self.assertEqual(summary['player']['image_url'], None)
        self.assertEqual(summary['player']['last_name'], '')


if __name__ == '__main__':
    unittest.main()
