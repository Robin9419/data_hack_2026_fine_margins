import random
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

from app import db, main
from app.content import get_content


class TradeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(db, 'DB_PATH', Path(self.tmp.name) / 'test.sqlite3')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        db.init_db()
        self.cards = get_content().cards
        self.base = [cid for cid, c in self.cards.items() if c['type'] == 'base']

    def user(self, favorite=None, stage='post'):
        # After the tournament by default, so every special card exists.
        return {**db.get_or_create_user(f'u{random.random()}', favorite)[0], 'stage': stage}

    def test_duplicates_stack_and_trade_takes_copies(self):
        uid = self.user()['id']
        cid = self.base[0]
        self.assertEqual(db.grant_cards(uid, [cid]), {cid})
        self.assertEqual(db.grant_cards(uid, [cid, cid]), set())
        self.assertEqual(db.card_copies(uid)[cid], 3)
        self.assertFalse(db.remove_copies(uid, [cid] * 4))
        self.assertEqual(db.card_copies(uid)[cid], 3)
        self.assertTrue(db.remove_copies(uid, [cid, cid]))
        self.assertEqual(db.card_copies(uid)[cid], 1)
        self.assertTrue(db.remove_copies(uid, [cid]))
        self.assertNotIn(cid, db.owned_cards(uid))

    def test_trade_endpoint_rejects_missing_and_special_cards(self):
        user = self.user()
        db.grant_cards(user['id'], self.base[:2])
        with self.assertRaises(main.HTTPException) as err:
            main.trade(main.TradeRequest(card_ids=[self.base[0], self.base[1], self.base[1]]), user)
        self.assertEqual(err.exception.status_code, 409)
        self.assertEqual(len(db.owned_cards(user['id'])), 2)
        special = next(cid for cid, c in self.cards.items() if c['type'] == 'special')
        with self.assertRaises(main.HTTPException) as err:
            main.trade(main.TradeRequest(card_ids=[special] * 3), user)
        self.assertEqual(err.exception.status_code, 400)

    def test_odds_with_favorite_team(self):
        random.seed(1)
        user = self.user('HC Davos')
        counts = Counter()
        for _ in range(800):
            db.clear_cards(user['id'])
            db.grant_cards(user['id'], [self.base[0]] * 3)
            result = main.trade(main.TradeRequest(card_ids=[self.base[0]] * 3), user)
            card = result['pack'][0]
            counts[result['outcome']] += 1
            if result['outcome'] == 'favorite':
                self.assertEqual(card['player']['team'], 'HC Davos')
            elif result['outcome'] == 'other':
                self.assertNotEqual(card['player']['team'], 'HC Davos')
            else:
                self.assertEqual(card['type'], 'special')
        self.assertAlmostEqual(counts['other'] / 800, 0.5, delta=0.05)
        self.assertAlmostEqual(counts['favorite'] / 800, 0.25, delta=0.05)
        self.assertAlmostEqual(counts['special'] / 800, 0.25, delta=0.05)

    def test_trade_never_gives_a_duplicate(self):
        random.seed(3)
        user = self.user('HC Davos')
        for _ in range(200):
            db.clear_cards(user['id'])
            # Owns every base card plus two spare copies of the first one, so the trade must use a special card.
            db.grant_cards(user['id'], self.base + [self.base[0]] * 2)
            before = set(db.owned_cards(user['id']))
            card = main.trade(main.TradeRequest(card_ids=[self.base[0]] * 3), user)['pack'][0]
            self.assertNotIn(card['id'], before)
            self.assertEqual(card['type'], 'special')

    def test_trade_refuses_when_everything_is_owned(self):
        user = self.user()
        cards = list(self.cards)
        db.grant_cards(user['id'], cards + list(main.road_cards_for(user)) + [self.base[0]] * 2)
        with self.assertRaises(main.HTTPException) as err:
            main.trade(main.TradeRequest(card_ids=[self.base[0]] * 3), user)
        self.assertEqual(err.exception.status_code, 409)
        self.assertEqual(db.card_copies(user['id'])[self.base[0]], 3)

    def test_trade_can_give_a_road_card_when_only_those_are_missing(self):
        user = self.user()
        roads = main.road_cards_for(user)
        db.grant_cards(user['id'], list(self.cards) + [self.base[0]] * 2)
        card = main.trade(main.TradeRequest(card_ids=[self.base[0]] * 3), user)['pack'][0]
        self.assertIn(card['id'], roads)
        self.assertIn(card['id'], db.owned_cards(user['id']))

    def test_no_special_cards_before_their_game(self):
        random.seed(2)
        user = self.user('HC Davos', stage='pre')
        for _ in range(100):
            db.clear_cards(user['id'])
            db.grant_cards(user['id'], [self.base[0]] * 3)
            self.assertEqual(main.trade(main.TradeRequest(card_ids=[self.base[0]] * 3), user)['pack'][0]['type'], 'base')

    def test_odds_without_favorite_team(self):
        self.assertEqual([o['chance'] for o in main.trade_odds(None)], [0.75, 0.25])


if __name__ == '__main__':
    unittest.main()
