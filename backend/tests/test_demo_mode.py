"""The submission must remain usable without the restricted match exports."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import content, db, main, shootout


class DemoModeTests(unittest.TestCase):
    def test_missing_and_partial_datasets_support_the_demo(self):
        for partial in (False, True):
            with self.subTest(partial=partial), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                if partial:
                    # A lone export must not be read or combined with fallback data.
                    (root / content._load_json('match.json')['stats_file']).write_text('incomplete export')
                with patch.object(content, 'DATA_DIR', root), patch.object(db, 'DB_PATH', root / 'demo.sqlite3'):
                    content.get_content.cache_clear()
                    shootout.get_shootout.cache_clear()
                    try:
                        with TestClient(main.app) as client:
                            status = client.get('/api/data-status').json()
                            self.assertTrue(status['demo_mode'])
                            self.assertEqual(len(status['missing_files']), 1 if partial else 2)
                            login = client.post('/api/login', json={'username': 'jury'})
                            self.assertEqual(login.status_code, 200, login.text)
                            client.headers['Authorization'] = 'Bearer ' + login.json()['token']
                            for stage in content.get_content().tournament.stages:
                                response = client.post('/api/tournament/stage', json={'stage': stage})
                                self.assertEqual(response.status_code, 200, response.text)
                                for endpoint in ('/api/cards', '/api/activities', '/api/tournament', '/api/duel/players'):
                                    response = client.get(endpoint)
                                    self.assertEqual(response.status_code, 200, response.text)
                            final = content.get_content().tournament.final['id']
                            self.assertTrue(content.get_content().game_cards(final))
                            # The final's specials and moment card exist without the data, with random values.
                            demo_final = content._load_json('demo_final_cards.json')
                            cards = content.get_content().cards
                            for spec in demo_final['specials']:
                                self.assertIsNone(cards[spec['id']]['video'])
                                self.assertIn(spec['id'], content.get_content().game_cards(final))
                            self.assertIn('No video', cards[demo_final['moment']['id']]['text'])
                            quiz = client.post('/api/quiz/start', json={'venue': 'home'})
                            self.assertEqual(quiz.status_code, 200, quiz.text)
                            self.assertTrue(quiz.json()['questions'])
                            for mode in ('1v1', '2v2'):
                                duel = client.post('/api/duel/start', json={'mode': mode})
                                self.assertEqual(duel.status_code, 200, duel.text)
                                self.assertIn('Simulated demo', duel.json()['turn']['scenario']['source'])
                            self.assertFalse(content.get_content().event_rows)
                    finally:
                        content.get_content.cache_clear()
                        shootout.get_shootout.cache_clear()
