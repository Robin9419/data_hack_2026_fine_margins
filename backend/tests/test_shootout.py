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
        sampled = [p for p in self.game.profiles.values() if not p['real'] and not p.get('stand_in')]
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
        sampled = [p for p in self.game.profiles.values() if not p['real'] and not p.get('stand_in')]
        types = {self.game.content.cards[p['card_id']]['type'] for p in sampled if p['card_id'] in self.game.content.cards}
        self.assertTrue({'base', 'legend', 'special'} <= types)
        content = self.game.content
        special = lambda p: content.cards.get(p['card_id'], {'type': 'special'})['type'] in ('special', 'legend')
        self.assertTrue(all(t['value'] <= shootout.SAMPLED_MAX for p in sampled if not special(p) for t in p['traits'].values()))
        legend = lambda p: content.cards.get(p['card_id'], {})['type'] == 'legend' if p['card_id'] in content.cards else False
        self.assertTrue(all(t['value'] <= shootout.SPECIAL_MAX for p in sampled if special(p) and not legend(p) for t in p['traits'].values()))
        self.assertTrue(all(t['value'] <= shootout.LEGEND_MAX for p in sampled if legend(p) for t in p['traits'].values()))
        mean = lambda ps: sum(t['value'] for p in ps for t in p['traits'].values()) / sum(len(p['traits']) for p in ps)
        # Special cards are stronger than base cards, and a forward is still better up close than a defender.
        self.assertGreater(mean([p for p in sampled if special(p)]), mean([p for p in sampled if not special(p)]) + 8)
        fw = [p for p in sampled if special(p) and p['position'] == 'Forward']
        df = [p for p in sampled if special(p) and p['position'] == 'Defender']
        close = lambda ps: sum(p['traits']['close']['value'] for p in ps) / len(ps)
        self.assertGreater(close(fw), close(df))

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
        user = db.user_for_token(token)
        db.grant_cards(user['id'], ['brick-wall', 'corvi'])
        players = client.get('/api/duel/players', headers=headers).json()['players']
        ids = {e['card']['id'] for e in players}
        self.assertLess(len(players), 50)  # only the user's collection, not every card
        self.assertTrue({'brick-wall', 'corvi'} <= ids)
        goalie, skater = 'brick-wall', 'corvi'
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

    def test_api_only_picks_from_your_collection(self):
        client = TestClient(main.app)
        token = client.post('/api/login', json={'username': f'duel{random.random()}'}).json()['token']
        headers = {'Authorization': f'Bearer {token}'}
        client.post('/api/tournament/stage', json={'stage': 'post'}, headers=headers)
        user = db.user_for_token(token)
        owned = main.owned_now(user)
        self.assertNotIn('corvi', owned)
        shown = {e['card']['id'].removeprefix(shootout.STAND_IN) for e in client.get('/api/duel/players', headers=headers).json()['players']}
        self.assertTrue(shown <= set(owned) | set(main.road_cards_for(user)))
        duel = client.post('/api/duel/start', json={'mode': '1v1'}, headers=headers).json()
        slot = 'goalie' if 'goalie' in duel['turn']['slots'] else 'carrier'
        card = 'brick-wall' if slot == 'goalie' else 'corvi'
        res = client.post(f"/api/duel/{duel['id']}/play", json={'picks': {slot: card}}, headers=headers)
        self.assertEqual(res.status_code, 400)

    def test_no_goalkeeper_puts_a_skater_in_goal(self):
        client = TestClient(main.app)
        token = client.post('/api/login', json={'username': f'duel{random.random()}'}).json()['token']
        headers = {'Authorization': f'Bearer {token}'}
        user = db.user_for_token(token)
        owned = main.owned_now(user)
        profiles = self.game.profiles
        for cid in [c for c in owned if profiles.get(c, {}).get('role') == 'goalie']:
            self.skipTest('starter pack had a goalkeeper')
        db.grant_cards(user['id'], ['corvi'])
        players = client.get('/api/duel/players', headers=headers).json()['players']
        goalies = [e for e in players if e['role'] == 'goalie']
        self.assertEqual(len(goalies), 1)
        stand_in = goalies[0]
        self.assertTrue(stand_in['profile']['stand_in'])
        self.assertTrue(all(t['value'] <= 18 for t in stand_in['profile']['traits'].values()))
        again = client.get('/api/duel/players', headers=headers).json()['players']
        self.assertEqual([e['card']['id'] for e in again if e['role'] == 'goalie'], [stand_in['card']['id']])
        duel = client.post('/api/duel/start', json={'mode': '1v1'}, headers=headers).json()
        while not duel['finished']:
            slot = 'goalie' if 'goalie' in duel['turn']['slots'] else 'carrier'
            card = stand_in['card']['id'] if slot == 'goalie' else 'corvi'
            res = client.post(f"/api/duel/{duel['id']}/play", json={'picks': {slot: card}}, headers=headers)
            if res.status_code == 400:  # the stand-in may be Corvi himself or the bot may already hold the player
                break
            duel = res.json()['duel']

    def test_ones_to_watch_cards_can_play(self):
        client = TestClient(main.app)
        token = client.post('/api/login', json={'username': f'duel{random.random()}'}).json()['token']
        headers = {'Authorization': f'Bearer {token}'}
        user = db.user_for_token(token)
        road = next(c for c in main.road_cards_for(user).values() if c['player']['position'] != 'Goalkeeper')
        self.assertIn(road['id'], self.game.profiles)
        db.grant_cards(user['id'], [road['id']])
        players = client.get('/api/duel/players', headers=headers).json()['players']
        self.assertIn(road['id'], {e['card']['id'] for e in players})
        # No collector or context (reward) cards are ever playable.
        self.assertFalse([e for e in players if e['card']['type'] == 'reward'])
        duel = client.post('/api/duel/start', json={'mode': '1v1'}, headers=headers).json()
        if 'carrier' in duel['turn']['slots']:
            res = client.post(f"/api/duel/{duel['id']}/play", json={'picks': {'carrier': road['id']}}, headers=headers)
            self.assertEqual(res.status_code, 200, res.text)

    def test_ones_to_watch_only_have_data_once_the_final_is_played(self):
        client = TestClient(main.app)
        token = client.post('/api/login', json={'username': f'duel{random.random()}'}).json()['token']
        headers = {'Authorization': f'Bearer {token}'}
        user = db.user_for_token(token)
        # A star who played the final (a few stars did not, they never have data).
        road = next(c for c in main.road_cards_for(user) if self.game.final_profiles[c]['real'])
        db.grant_cards(user['id'], [road])
        for stage, real in (('pre', False), ('post', True)):
            client.post('/api/tournament/stage', json={'stage': stage}, headers=headers)
            players = client.get('/api/duel/players', headers=headers).json()['players']
            entry = next(e for e in players if e['card']['id'] == road)
            self.assertEqual(entry['real'], real)
            traits = entry['profile']['traits'].values()
            self.assertEqual(all(t['evidence'] for t in traits), real)
            self.assertEqual(bool(entry['profile']['game']), real)

    def test_players_are_sorted_by_rarity(self):
        client = TestClient(main.app)
        token = client.post('/api/login', json={'username': f'duel{random.random()}'}).json()['token']
        headers = {'Authorization': f'Bearer {token}'}
        client.post('/api/tournament/stage', json={'stage': 'post'}, headers=headers)
        user = db.user_for_token(token)
        road = next(iter(main.road_cards_for(user)))
        db.grant_cards(user['id'], [road, 'corvi', 'brick-wall'])
        players = client.get('/api/duel/players', headers=headers).json()['players']
        ranks = [main.duel_rarity(e['card']) for e in players]
        self.assertEqual(ranks, sorted(ranks, reverse=True))
        self.assertGreater(len(set(ranks)), 1)

    def test_bot_picks_only_available_cards(self):
        early = main.get_content().available(set())  # no game played yet: no real-data cards exist
        for role in ('skater', 'goalie'):
            pool = shootout.bot_pool(role, available=early)
            self.assertTrue(pool)
            self.assertTrue(all(cid in early for cid in pool))
        # Once the final is played its real-data cards are available and the bot prefers them.
        final = main.get_content().tournament.final['id']
        late = main.get_content().available({final})
        for role in ('skater', 'goalie'):
            pool = shootout.bot_pool(role, available=late)
            self.assertTrue(all(cid in late and self.game.profiles[cid]['real'] for cid in pool))
        # A duel from an early stage works end to end.
        duel = shootout.new_duel('2v2', random.Random(3), early)
        self.assertTrue(all(cid in early for cid in duel['bot_picks'].values()))


if __name__ == '__main__':
    unittest.main()
