import unittest

from app.content import get_content


class TestDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.testdata = get_content().testdata

    def card(self, special_type, game_id):
        return self.testdata.cards.get(f"test-{special_type}-{game_id}")

    def test_all_eleven_games_and_results(self):
        games = {g["id"]: g for g in self.testdata.summaries()}
        self.assertEqual(len(games), 11)
        final = games["2025-12-31_us-collegiate-selects_hc-davos"]
        self.assertEqual((final["home_score"], final["away_score"], final["has_wisehockey"]), (3, 6, True))
        self.assertEqual(games["2025-12-26_hc-fribourg-gotteron_hc-sparta-praha"]["home_score"], 5)

    def test_game_winner_is_the_goal_after_which_the_loser_never_drew_level(self):
        card = self.card("gamewinner", "2025-12-26_hc-fribourg-gotteron_hc-sparta-praha")  # 5:2, third Fribourg goal
        self.assertEqual((card["player"]["last_name"], card["player"]["team"]), ("Borgström", "HC Fribourg-Gottéron"))
        self.assertIn("3–0", card["explanation"])

    def test_player_of_the_match_comes_from_the_winning_team(self):
        for game in self.testdata.games:
            card = self.card("motm", game["id"])
            if card:
                winner = game["home_team"] if game["home_score"] > game["away_score"] else game["away_team"]
                self.assertEqual(card["player"]["team"], winner)

    def test_record_breaker_needs_an_earlier_game(self):
        self.assertIsNone(self.card("recordbreaker", "2025-12-26_hc-fribourg-gotteron_hc-sparta-praha"))
        card = self.card("recordbreaker", "2025-12-30_us-collegiate-selects_hc-sparta-praha")
        self.assertEqual(card["player"]["last_name"], "Pohlkamp")
        self.assertEqual(card["attributes"][0]["display_value"], "164.3")

    def test_final_only_gets_a_record_breaker_and_test_cards_stay_out_of_the_set(self):
        final = "2025-12-31_us-collegiate-selects_hc-davos"
        self.assertEqual([c["special_type"] for c in self.testdata.cards_for([final])], [])
        content = get_content()
        self.assertFalse(set(self.testdata.cards) & set(content.cards))
        self.assertTrue(all(c["test"] for c in self.testdata.cards.values()))

    def test_goalkeeper_card_is_ranked_among_goalkeepers(self):
        wall = next(c for c in self.testdata.cards.values() if c["special_type"] == "wall")
        self.assertEqual(wall["player"]["position"], "Goalkeeper")
        self.assertEqual(wall["attributes"][0]["rank_pool"], "goalkeepers")


class RoadToFinalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.road = get_content().road_to_final
        cls.all_games = [g["id"] for g in get_content().testdata.games]

    def stages(self, game_ids):
        return {c["player"]["team"]: c["road"]["stage"] for c in self.road.cards_for(game_ids)}

    def test_nothing_without_a_switched_on_game(self):
        self.assertEqual(self.road.cards_for([]), [])

    def test_stage_follows_how_far_the_team_got(self):
        stages = self.stages(self.all_games)
        self.assertEqual(stages["HC Davos"], 4)  # won the final
        self.assertEqual(stages["U.S. Collegiate Selects"], 3)  # lost the final
        self.assertEqual(stages["HC Fribourg-Gottéron"], 2)  # lost the semi-final
        self.assertEqual(stages["Team Canada"], 2)

    def test_card_only_for_teams_of_switched_on_games(self):
        first = self.all_games[0]  # Fribourg - Sparta
        cards = self.road.cards_for([first])
        self.assertEqual({c["player"]["team"] for c in cards}, {"HC Fribourg-Gottéron", "HC Sparta Praha"})
        self.assertTrue(all(c["road"]["stage"] == 1 and c["road"]["played"] == 1 for c in cards))

    def test_form_chart_has_a_slot_per_team_game_and_the_card_grows(self):
        davos = lambda ids: next(c for c in self.road.cards_for(ids) if c["player"]["team"] == "HC Davos")
        few = davos([g for g in self.all_games if "hc-davos_us-collegiate-selects" in g])
        many = davos(self.all_games)
        self.assertEqual(len(few["road"]["games"]), 5)
        self.assertEqual([s["mr"] is not None for s in few["road"]["games"]].count(True), 2)  # that game and the final
        self.assertEqual(few["road"]["stage"], 2)
        self.assertEqual(many["road"]["stage"], 4)
        self.assertIsNotNone(many["road"]["trend"])


if __name__ == "__main__":
    unittest.main()
