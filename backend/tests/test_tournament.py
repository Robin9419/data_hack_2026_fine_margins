import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import db, main
from app.content import get_content

FIRST_DAY = '2025-12-26'
FRI_SPA = '2025-12-26_hc-fribourg-gotteron_hc-sparta-praha'  # 5:2, Biasca scored first
FINAL = '2025-12-31_us-collegiate-selects_hc-davos'


class TournamentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(db, 'DB_PATH', Path(self.tmp.name) / 'test.sqlite3')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        db.init_db()
        self.content = get_content()
        self.t = self.content.tournament
        self.user = db.get_or_create_user(f'u{random.random()}')[0]

    def go(self, stage):
        result = main.set_stage(main.StageRequest(stage=stage), self.user)
        self.user = {**self.user, 'stage': stage}
        return result['tournament']

    def predict(self, game_id, question_id, option_id):
        return main.predict(main.PredictionRequest(game_id=game_id, question_id=question_id, option_id=option_id), self.user)

    def test_new_user_starts_before_the_tournament(self):
        self.assertEqual(self.user['stage'], 'pre')
        self.assertEqual(self.t.played('pre'), set())
        self.assertEqual(len(self.t.played('post')), 11)
        self.assertEqual(self.t.played('2025-12-28'), {g['id'] for g in self.t.games if g['date'] < '2025-12-28'})

    def test_game_cards_only_exist_once_the_game_is_played(self):
        cards = lambda: {c['id']: c for c in main.list_cards(self.user)['cards']}
        before = cards()
        self.assertTrue(all(c['type'] in ('base', 'legend') or c.get('context_type') == 'stadium' for c in before.values()))
        self.go('2025-12-27')
        after_day_one = cards()
        self.assertTrue(set(self.content.game_cards(FRI_SPA)) <= set(after_day_one))
        self.assertFalse(set(self.content.game_cards(FINAL)) & set(after_day_one))
        self.assertFalse(any(c.get('kind') == 'road' for c in after_day_one.values()))  # road cards come from packs only
        self.go('post')
        self.assertTrue(set(self.content.game_cards(FINAL)) <= set(cards()))

    def test_unplayed_game_card_is_not_found(self):
        with self.assertRaises(main.HTTPException) as err:
            main.get_card(self.content.game_cards(FINAL)[0], self.user)
        self.assertEqual(err.exception.status_code, 404)

    def test_every_game_has_three_questions_with_a_valid_answer(self):
        for game in self.t.games:
            questions = self.t.questions[game['id']]
            self.assertEqual([q['id'] for q in questions], ['winner', 'goal', 'kpi'])
            for q in questions:
                self.assertIn(q['answer'], {o['id'] for o in q['options']}, (game['id'], q['id']))
        self.assertEqual(self.t.answer_of(FRI_SPA, 'winner'), 'home')
        self.assertEqual(self.t.answer_of(FRI_SPA, 'goal'), 'HC Fribourg-Gottéron#17')

    def test_predictions_only_for_todays_games(self):
        with self.assertRaises(main.HTTPException):
            self.predict(FRI_SPA, 'winner', 'home')  # before the tournament
        self.go(FIRST_DAY)
        view = self.predict(FRI_SPA, 'winner', 'away')
        view = self.predict(FRI_SPA, 'winner', 'home')  # can change until the game is played
        game = next(g for g in view['today'] if g['id'] == FRI_SPA)
        self.assertEqual(game['questions'][0]['prediction'], 'home')
        self.assertNotIn('answer', game['questions'][0])  # no spoilers before the game
        with self.assertRaises(main.HTTPException) as err:
            self.predict(FRI_SPA, 'winner', 'draw')
        self.assertEqual(err.exception.status_code, 400)

    def test_correct_predictions_earn_packs_after_the_game(self):
        self.go(FIRST_DAY)
        self.predict(FRI_SPA, 'winner', 'home')  # right
        self.predict(FRI_SPA, 'goal', 'HC Fribourg-Gottéron#17')  # right
        self.predict(FRI_SPA, 'kpi', 'fast')  # wrong: 159.3 km/h
        view = self.go('2025-12-27')
        result = next(g for g in view['results'] if g['id'] == FRI_SPA)
        self.assertEqual((result['correct'], result['packs'], result['packs_claimed']), (2, 2, False))
        self.assertEqual(view['packs_waiting'], 2)

        opened = main.open_game_packs(FRI_SPA, self.user)
        cards = [c for c in opened['pack'] if c['type'] != 'legend']
        self.assertEqual(len(cards), 6)
        self.assertLessEqual(sum(c['type'] == 'special' for c in cards), 2)  # each pack's third card: 20% a special
        teams = {'HC Fribourg-Gottéron', 'HC Sparta Praha'}
        self.assertTrue(all(c['player']['team'] in teams for c in cards))
        with self.assertRaises(main.HTTPException):
            main.open_game_packs(FRI_SPA, self.user)  # only once

    def test_played_game_locks_its_predictions(self):
        self.go(FIRST_DAY)
        self.go('2025-12-27')
        self.go(FIRST_DAY)  # back in time: the game was already played
        with self.assertRaises(main.HTTPException) as err:
            self.predict(FRI_SPA, 'winner', 'home')
        self.assertEqual(err.exception.status_code, 409)

    def test_trivia_waits_for_the_first_game_and_asks_about_the_latest_day(self):
        self.assertEqual(main.quiz_start(main.QuizStart(venue='home'), self.user)['questions'], [])
        self.go('2025-12-28')
        quiz = main.quiz_start(main.QuizStart(venue='home'), self.user)
        self.assertEqual(len(quiz['questions']), 3)
        latest = {g['id'] for g in self.t.games if g['date'] == '2025-12-27'}
        asked = [db.get_question(self.user['id'], q['id'])['card_id'] for q in quiz['questions']]
        self.assertTrue(all(self.content.card_game[cid] in latest for cid in asked))

    def test_game_trivia_options_are_players_of_that_game(self):
        rng = random.Random(4)
        for cid in self.content.game_cards(FRI_SPA):
            card = self.content.cards[cid]
            question = self.content.build_question(cid, rng)
            self.assertEqual(len(question['option_ids']), 3)
            teams = {self.content.cards[o]['player']['team'] for o in question['option_ids']}
            self.assertTrue(teams <= {'HC Fribourg-Gottéron', 'HC Sparta Praha'})
            goalie = card['player']['position'] == 'Goalkeeper'
            for o in question['option_ids']:
                self.assertEqual(self.content.cards[o]['player']['position'] == 'Goalkeeper', goalie)

    def test_trivia_drops_out_once_played_on_the_gameday(self):
        self.go('2025-12-28')
        self.assertGreater(main.activities(self.user)['trivia'], 0)
        main.quiz_start(main.QuizStart(venue='home'), self.user)
        self.assertEqual(main.activities(self.user)['trivia'], 0)
        self.go('2025-12-29')  # the next gameday offers its own round again
        self.assertGreater(main.activities(self.user)['trivia'], 0)

    def test_reset_goes_back_before_the_tournament(self):
        self.go(FIRST_DAY)
        self.predict(FRI_SPA, 'winner', 'home')
        self.go('post')
        main.reset(self.user)
        self.assertEqual(db.user_for_token(db.create_session(self.user['id']))['stage'], 'pre')
        self.assertEqual(db.predictions(self.user['id']), {})
        self.assertEqual(db.game_packs(self.user['id']), {})

    def test_goal_and_kpi_questions_vary_between_games(self):
        prompts = lambda i: {self.t.questions[g['id']][i]['prompt'] for g in self.t.games}
        self.assertGreaterEqual(len(prompts(1)), 6)
        self.assertGreaterEqual(len(prompts(2)), 5)

    def test_stage_change_reports_the_games_it_played(self):
        self.go(FIRST_DAY)
        self.predict(FRI_SPA, 'winner', 'home')
        result = main.set_stage(main.StageRequest(stage='2025-12-27'), self.user)
        self.user = {**self.user, 'stage': '2025-12-27'}
        played = {g['id']: g for g in result['just_played']}
        self.assertEqual(set(played), {g['id'] for g in self.t.today(FIRST_DAY)})
        self.assertEqual(played[FRI_SPA]['correct'], 1)
        self.go(FIRST_DAY)
        again = main.set_stage(main.StageRequest(stage='2025-12-27'), self.user)
        self.assertEqual(again['just_played'], [])  # already resolved

    def test_open_all_packs_opens_every_waiting_pack(self):
        self.go(FIRST_DAY)
        self.predict(FRI_SPA, 'winner', 'home')
        self.predict(FRI_SPA, 'goal', 'HC Fribourg-Gottéron#17')
        self.go('2025-12-27')
        self.assertEqual(main.activities(self.user)['packs_waiting'], 2)
        cards = [c for c in main.open_all_packs(self.user)['pack'] if c['type'] != 'legend']
        self.assertEqual(len(cards), 6)
        self.assertEqual(main.activities(self.user)['packs_waiting'], 0)
        with self.assertRaises(main.HTTPException):
            main.open_all_packs(self.user)

    def test_activities_drop_out_once_done(self):
        self.go(FIRST_DAY)
        acts = main.activities(self.user)
        self.assertTrue(acts['daily'])
        self.assertEqual(acts['social']['id'], 'facebook')
        self.assertEqual(acts['predictions'], {'games': 2, 'picks': 0, 'questions': 6})
        main.daily_claim(self.user)
        main.bonus_social(self.user)
        for game in self.t.today(FIRST_DAY):
            for q in self.t.questions[game['id']]:
                self.predict(game['id'], q['id'], q['options'][0]['id'])
        acts = main.activities(self.user)
        self.assertEqual((acts['daily'], acts['social'], acts['predictions']), (False, None, None))
        with self.assertRaises(main.HTTPException):
            main.daily_claim(self.user)
        self.go('2025-12-27')  # a new day: a new daily card and another channel
        acts = main.activities(self.user)
        self.assertTrue(acts['daily'])
        self.assertEqual(acts['social']['id'], 'tiktok')


if __name__ == '__main__':
    unittest.main()
