import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from app import db, main, shootout


class ShootoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(db, 'DB_PATH', Path(self.tmp.name) / 'test.sqlite3')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        db.init_db()
        self.game = shootout.get_shootout()

    def test_final_cards_use_real_data(self):
        wall = self.game.profiles['brick-wall']
        self.assertTrue(wall['real'])
        # Gajan stopped every high-danger chance but let in a long-range goal worth 0.012 xG.
        self.assertIn('close', wall['strengths'])
        self.assertIn('long', wall['weaknesses'])
        self.assertIn('long', self.game.profiles['game-winner']['strengths'])
        self.assertIn('blocking', self.game.profiles['mccartthy']['strengths'])

    def test_other_games_are_sampled_and_stable(self):
        sampled = [p for p in self.game.profiles.values() if not p['real']]
        self.assertTrue(sampled)
        self.assertTrue(all(t['evidence'] is None for p in sampled for t in p['traits'].values()))
        again = shootout.Shootout(self.game.content).profiles
        self.assertEqual({k: p['traits'] for k, p in again.items()}, {k: p['traits'] for k, p in self.game.profiles.items()})

    def test_attacks_start_at_the_blue_line(self):
        rng = random.Random(1)
        seen = []
        for _ in range(10):
            index, s = self.game.scenario('2v2', rng, seen)
            self.assertNotIn(index, seen)
            seen.append(index)
            self.assertLess(abs(s['carrier'][0] - shootout.BLUE_LINE), 6)
            self.assertTrue(s['support'] and s['defender'])
            self.assertIn('zone entry', s['source'])

    def test_every_play_is_explained(self):
        p = self.game.profiles
        rng = random.Random(5)
        for _ in range(30):
            _, s = self.game.scenario('2v2', rng, [])
            result = shootout.simulate(s, {'carrier': p['game-winner'], 'support': p['corvi']},
                                       {'goalie': p['brick-wall'], 'defender': p['mccartthy']}, rng)
            why = result['why']
            self.assertTrue(why['headline'] and 0 <= why['chance']['value'] <= 1 and 0 <= why['base'] <= 1)
            self.assertLessEqual(len(why['reasons']), 3)
            self.assertTrue(all(r['text'] for r in why['reasons']))

    def test_long_shooter_beats_a_goalie_weak_from_distance(self):
        p = self.game.profiles
        far = (13.0, -4.0)
        sniper = shootout.shot_chance(p['game-winner'], p['brick-wall'], far)[0]
        passer = shootout.shot_chance(p['corvi'], p['brick-wall'], far)[0]
        self.assertGreater(sniper, 2 * passer)

    def test_each_goalie_of_the_final_holds_one_card(self):
        content = self.game.content
        final = content.tournament.final['id']
        goalies = [content.cards[cid] for cid in content.game_cards(final)
                   if content.cards[cid]['player']['position'] == 'Goalkeeper']
        self.assertEqual(sorted((c['player']['last_name'], c['title']) for c in goalies),
                         [('Aeschlimann', 'Shot Stopper'), ('Gajan', 'Brick Wall')])
        # Man of the Match and Game Winner stand next to the player's profile card.
        titles = {c['title'] for cid in content.game_cards(final) for c in [content.cards[cid]]
                  if c['player']['last_name'] == 'Tambellini'}
        self.assertEqual(titles, {'Sniper', 'Man of the Match'})
        self.assertTrue(self.game.profiles['aeschlimann']['real'])

    def test_bot_only_picks_real_players(self):
        for role in ('skater', 'goalie'):
            pool = shootout.bot_pool(role)
            self.assertTrue(pool)
            self.assertTrue(all(self.game.profiles[cid]['real'] for cid in pool))
        rng = random.Random(2)
        for mode in ('1v1', '2v2'):
            duel = shootout.new_duel(mode, rng)
            self.assertTrue(all(self.game.profiles[cid]['real'] for cid in duel['bot_picks'].values()))

    def test_players_without_data_are_weaker(self):
        sampled = [p for p in self.game.profiles.values() if not p['real']]
        types = {self.game.content.cards[p['card_id']]['type'] for p in sampled}
        self.assertTrue({'base', 'legend', 'special'} <= types)
        self.assertTrue(all(t['value'] <= shootout.SAMPLED_MAX for p in sampled for t in p['traits'].values()))

    def test_duels_finish(self):
        skaters = [cid for cid, p in self.game.profiles.items() if p['role'] == 'skater']
        goalies = [cid for cid, p in self.game.profiles.items() if p['role'] == 'goalie']
        for seed in range(40):
            rng = random.Random(seed)
            mode = '2v2' if seed % 2 else '1v1'
            duel = shootout.new_duel(mode, rng)
            while not duel['finished']:
                taken = {self.game.profiles[c]['who'] for c in (duel['bot_picks'] or {}).values()}
                free = [c for c in skaters if self.game.profiles[c]['who'] not in taken]
                rng.shuffle(free)
                picks = {}
                for slot in shootout.slots(mode, duel['attacker'] == 'you'):
                    picks[slot] = rng.choice(goalies) if slot == 'goalie' else free.pop()
                result = shootout.play_turn(duel, picks, rng)
                self.assertTrue(result['frames'] and result['steps'])
            self.assertLessEqual(duel['round'], shootout.MAX_ROUNDS)
            if duel['winner']:
                loser = 'bot' if duel['winner'] == 'you' else 'you'
                self.assertGreater(duel['score'][duel['winner']], duel['score'][loser])

    def test_api_every_duel_pays_out(self):
        client = TestClient(main.app)
        token = client.post('/api/login', json={'username': f'duel{random.random()}'}).json()['token']
        headers = {'Authorization': f'Bearer {token}'}
        client.post('/api/tournament/stage', json={'stage': 'post'}, headers=headers)
        players = client.get('/api/duel/players', headers=headers).json()['players']
        self.assertGreater(len(players), 200)
        goalie = next(e['card']['id'] for e in players if e['role'] == 'goalie')
        skater = next(e['card']['id'] for e in players if e['role'] == 'skater')
        rewarded = 0
        for _ in range(4):
            duel = client.post('/api/duel/start', json={'mode': '1v1'}, headers=headers).json()
            while not duel['finished']:
                turn = duel['turn']
                # The same player can play every turn.
                picks = {'goalie': goalie} if 'goalie' in turn['slots'] else {'carrier': skater}
                data = client.post(f"/api/duel/{duel['id']}/play", json={'picks': picks}, headers=headers).json()
                duel = data['duel']
            if 'pack' in data:
                rewarded += 1
                specials = [c for c in data['pack'] if c['type'] == 'special']
                self.assertEqual(len(data['pack']) >= 10, duel['winner'] == 'you')
                if duel['winner'] == 'you':
                    self.assertTrue(specials)
        self.assertEqual(rewarded, 4)

    def test_api_drops_a_duel_with_removed_cards(self):
        client = TestClient(main.app)
        token = client.post('/api/login', json={'username': f'duel{random.random()}'}).json()['token']
        headers = {'Authorization': f'Bearer {token}'}
        duel = client.post('/api/duel/start', json={'mode': '1v1'}, headers=headers).json()
        user = db.user_for_token(token)
        duel_id, state = db.get_duel(user['id'])
        state['bot_picks'] = {'goalie': 'no-longer-a-card'}  # e.g. the old Gajan Shot Stopper card
        db.save_duel(duel_id, state)
        res = client.get('/api/duel', headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.json()['active'])
        res = client.post(f"/api/duel/{duel['id']}/play", json={'picks': {'carrier': 'corvi'}}, headers=headers)
        self.assertEqual(res.status_code, 409)

    def test_api_rejects_used_or_wrong_cards(self):
        client = TestClient(main.app)
        token = client.post('/api/login', json={'username': f'duel{random.random()}'}).json()['token']
        headers = {'Authorization': f'Bearer {token}'}
        duel = client.post('/api/duel/start', json={'mode': '2v2'}, headers=headers).json()
        res = client.post(f"/api/duel/{duel['id']}/play", json={'picks': {'carrier': 'brick-wall', 'support': 'corvi'}},
                          headers=headers)
        self.assertEqual(res.status_code, 400)  # a goalie can't skate
        res = client.post(f"/api/duel/{duel['id']}/play", json={'picks': {'carrier': 'player-of-the-match', 'support': 'base-hcd-19'}},
                          headers=headers)
        self.assertEqual(res.status_code, 400)


if __name__ == '__main__':
    unittest.main()
