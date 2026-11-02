import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import db, main
from app.content import get_content


class WatchPackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(db, 'DB_PATH', Path(self.tmp.name) / 'test.sqlite3')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        db.init_db()
        content = get_content()
        self.road = content.road_to_final
        # The first game where a star scored or assisted, and the first stage after it.
        self.game_id, self.pointed = next((g['id'], self.road.pointed(g['id'])) for g in content.tournament.games
                                          if self.road.pointed(g['id']))
        self.game = content.tournament.by_id[self.game_id]
        self.stage = next(s for s in content.tournament.stages if s != 'pre' and s > self.game['date'])

    def user(self):
        return db.get_or_create_user(f'u{random.random()}')[0]

    def test_owned_card_with_a_point_earns_a_pack_of_three(self):
        user = self.user()
        star = self.pointed[0]
        db.grant_cards(user['id'], [star['card_id']])
        result = main.set_stage(main.StageRequest(stage=self.stage), user)
        game = next(g for g in result['just_played'] if g['id'] == self.game_id)
        self.assertEqual([w['card_id'] for w in game['watch_packs']], [star['card_id']])
        self.assertGreaterEqual(result['tournament']['packs_waiting'], 1)

        user = {**user, 'stage': self.stage}
        before = result['tournament']['packs_waiting']
        opened = main.open_all_packs(user)
        cards = [c for c in opened['pack'] if c['type'] != 'legend']
        self.assertEqual(len(cards), before * 3)  # prediction packs and Ones to Watch packs both hold three cards
        self.assertEqual(main.tournament_view(user)['packs_waiting'], 0)

    def test_a_pack_for_each_point(self):
        user = self.user()
        star = self.pointed[0]
        db.grant_cards(user['id'], [star['card_id']])
        result = main.set_stage(main.StageRequest(stage=self.stage), user)
        game = next(g for g in result['just_played'] if g['id'] == self.game_id)
        points = star['goals'] + star['assists']
        self.assertEqual([(w['card_id'], w['packs']) for w in game['watch_packs']], [(star['card_id'], points)])
        self.assertEqual(result['tournament']['packs_waiting'], points)

    def test_no_pack_without_the_card(self):
        user = self.user()
        result = main.set_stage(main.StageRequest(stage=self.stage), user)
        self.assertTrue(all(not g['watch_packs'] for g in result['just_played']))

    def test_a_game_pays_out_once(self):
        user = self.user()
        db.grant_cards(user['id'], [self.pointed[0]['card_id']])
        main.set_stage(main.StageRequest(stage=self.stage), user)
        main.set_stage(main.StageRequest(stage='pre'), user)
        result = main.set_stage(main.StageRequest(stage=self.stage), user)
        self.assertEqual(result['just_played'], [])
        self.assertEqual(sum(len(g) for g in db.watch_packs(user['id']).values()), 1)

    def test_each_ticket_pack_rolls_its_own_special_chance(self):
        user = {**self.user(), 'stage': 'pre'}
        last_cards, special = 0, 0
        for _ in range(30):
            db.clear_cards(user['id'])
            cards = main.bonus_tickets(main.TicketBonusRequest(tickets=20), user)['pack']
            # Every 5-card pack ends with its own roll: 20 packs a purchase, 600 rolls over 30 purchases at 10% each.
            last_cards += len(cards) // main.CARDS_PER_TICKET
            special += sum(c['type'] == 'special' or c.get('kind') == 'road'
                           for c in cards[main.CARDS_PER_TICKET - 1::main.CARDS_PER_TICKET])
        # One roll per purchase would give about 3 specials here, per pack about 60.
        self.assertGreater(special, 30)


if __name__ == '__main__':
    unittest.main()
