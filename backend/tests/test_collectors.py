import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import db, main
from app.content import get_content


class CollectorAnnouncementTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(db, 'DB_PATH', Path(self.tmp.name) / 'test.sqlite3')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        db.init_db()
        self.content = get_content()

    def test_a_collector_is_announced_once(self):
        user = db.get_or_create_user(f'u{random.random()}')[0]
        user = {**user, 'stage': self.content.tournament.stages[-1]}
        team, base_ids = next((c['team'], c['requires']) for c in self.content.cards.values()
                              if c['type'] == 'reward' and c.get('kind') == 'collector')
        db.grant_cards(user['id'], base_ids)

        announced = main.award_collectors(user)
        self.assertIn(f'collector-{team.lower().replace(" ", "-")}', [c['id'] for c in announced])
        self.assertTrue(all(c['type'] == 'reward' for c in announced))
        self.assertEqual(main.award_collectors(user), [])


if __name__ == '__main__':
    unittest.main()
