import unittest

from app.content import get_content


class TestDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.testdata = get_content().testdata

    def card(self, special_type, game_id):
        return self.testdata.cards.get(f"test-{special_type}-{game_id}")

    def test_all_eleven_games_and_results(self):
        games = self.testdata.by_id
        self.assertEqual(len(games), 11)
        final = games["2025-12-31_us-collegiate-selects_hc-davos"]
        self.assertEqual((final["home_score"], final["away_score"], final["has_wisehockey"]), (3, 6, True))
        self.assertEqual(games["2025-12-26_hc-fribourg-gotteron_hc-sparta-praha"]["home_score"], 5)

    def test_every_goal_has_a_highlight_clip(self):
        for game in self.testdata.games:
            video = self.testdata.highlights[game["id"]]
            self.assertEqual(len(video["clips"]), len(game["goals"]), game["id"])
            starts = [c["start"] for c in video["clips"]]
            self.assertEqual(starts, sorted(starts), game["id"])  # the highlights show the goals in game order
            self.assertTrue(all(0 <= c["start"] < c["end"] <= video["duration"] for c in video["clips"]), game["id"])

    def test_three_awards_per_team_and_game_spread_evenly(self):
        awards = [c for c in self.testdata.cards.values() if c["special_type"] != "motm"]
        per_team_game = {}
        for c in awards:
            per_team_game.setdefault((c["test_game"], c["player"]["team"]), []).append(c)
        self.assertEqual(len(per_team_game), 20)
        self.assertTrue(all(len(v) == 3 for v in per_team_game.values()))
        by_award = {}
        for c in awards:
            by_award[c["title"]] = by_award.get(c["title"], 0) + 1
        self.assertEqual(len(by_award), 18)
        self.assertLessEqual(max(v for t, v in by_award.items() if t != "Game Winner") - min(v for t, v in by_award.items() if t != "Game Winner"), 1)
        players = [(c["test_game"], c["player"]["team"], c["player"]["jersey"]) for c in self.testdata.cards.values()]
        self.assertEqual(len(players), len(set(players)))  # one card per player and game

    def test_kept_cards_and_game_winner_only_in_one_goal_games(self):
        cards = self.testdata.cards.values()
        by_name = {(c["player"]["first_name"], c["player"]["last_name"]): c["title"] for c in cards}
        self.assertEqual((by_name[("Niko", "Hovinen")], by_name[("Alex", "Tracy")], by_name[("Mason", "Shaw")]),
                         ("Brick Wall", "Brick Wall", "Game Winner"))
        for c in cards:
            if c["title"] == "Game Winner":
                self.assertEqual(abs(c["match"]["home_score"] - c["match"]["away_score"]), 1)

    def test_awards_fit_the_position(self):
        for c in self.testdata.cards.values():
            if c["title"] in ("Shot Stopper", "Brick Wall"):
                self.assertEqual(c["player"]["position"], "Goalkeeper")
            elif c["title"] in ("Shot Blocker", "Escape Artist", "Progression Master"):
                self.assertEqual(c["player"]["position"], "Defender")
            elif c["title"] in ("Sniper", "Speedster", "Volume Shooter", "Go-To Scorer"):
                self.assertEqual(c["player"]["position"], "Forward")

    def test_player_of_the_match_comes_from_the_winning_team(self):
        for game in self.testdata.games:
            card = self.card("motm", game["id"])
            if card:
                winner = game["home_team"] if game["home_score"] > game["away_score"] else game["away_team"]
                self.assertEqual(card["player"]["team"], winner)

    def test_final_has_no_test_cards_and_test_cards_join_the_set_with_their_game(self):
        final = "2025-12-31_us-collegiate-selects_hc-davos"
        self.assertEqual(self.testdata.game_cards[final], [])
        content = get_content()
        self.assertTrue(set(self.testdata.cards) <= set(content.cards))
        self.assertTrue(all(c["test"] for c in self.testdata.cards.values()))
        self.assertTrue(all(content.card_game[cid] == c["test_game"] for cid, c in self.testdata.cards.items()))

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

    def test_ones_to_watch_from_the_start_of_the_tournament(self):
        cards = self.road.cards_for([])
        self.assertEqual(len(cards), len(self.road.stars))
        self.assertTrue(all(c["road"]["stage"] == 0 and c["road"]["played"] == 0 for c in cards))
        self.assertTrue(all(c["match"] is None and c["rating"]["mr"] is None for c in cards))

    def test_ones_to_watch_back_shows_the_stats_before_the_tournament(self):
        before = {c["id"]: c for c in self.road.cards_for([])}
        self.assertTrue(all(c["pre_tournament"] and c["archetype_kpis"] for c in before.values()))
        davos = next(c for c in before.values() if c["player"]["last_name"] == "Stransky")
        self.assertEqual([k["display_value"] for k in davos["archetype_kpis"]], ["35", "19", "1.03"])
        self.assertEqual(davos["archetype_kpis"][0]["note"], "NL 2025–26 so far · 34 games")
        after = self.road.cards_for(self.all_games)
        self.assertTrue(all(c["archetype_kpis"] is None and c["pre_tournament"] for c in after))  # back: the tournament

    def test_stage_follows_how_far_the_team_got(self):
        stages = self.stages(self.all_games)
        self.assertEqual(stages["HC Davos"], 4)  # won the final
        self.assertEqual(stages["U.S. Collegiate Selects"], 3)  # lost the final
        self.assertEqual(stages["HC Fribourg-Gottéron"], 2)  # lost the semi-final
        self.assertEqual(stages["Team Canada"], 2)

    def test_only_the_teams_that_have_played_get_a_rating(self):
        first = self.all_games[0]  # Fribourg - Sparta
        cards = self.road.cards_for([first])
        played = {c["player"]["team"] for c in cards if c["road"]["played"]}
        self.assertEqual(played, {"HC Fribourg-Gottéron", "HC Sparta Praha"})
        self.assertTrue(all(c["road"]["stage"] == 1 and c["road"]["played"] == 1 for c in cards if c["road"]["played"]))
        self.assertTrue(all(c["road"]["stage"] == 0 for c in cards if c["player"]["team"] not in played))

    def test_form_chart_has_a_slot_per_team_game_and_the_card_grows(self):
        davos = lambda ids: next(c for c in self.road.cards_for(ids) if c["player"]["team"] == "HC Davos")
        few = davos([g for g in self.all_games if "hc-davos_us-collegiate-selects" in g or "us-collegiate-selects_hc-davos" in g])
        many = davos(self.all_games)
        self.assertEqual(len(few["road"]["games"]), 5)
        self.assertEqual([s["mr"] is not None for s in few["road"]["games"]].count(True), 2)  # that game and the final
        self.assertEqual(few["road"]["stage"], 2)
        self.assertEqual(many["road"]["stage"], 4)
        self.assertIsNotNone(many["road"]["trend"])


if __name__ == "__main__":
    unittest.main()
