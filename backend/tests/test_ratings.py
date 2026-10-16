import unittest

from app.ratings import goalie_ratings, skater_ratings, tier_of

COLUMNS = ["G", "xGsum", "S", "A", "Passes", "Pass-%", "SPD TOP (km/h)", "Sprint SPD-Z DIST (m)", "PCW",
           "BKS", "TOI (s)", "Dist (m)", "FOW", "FOW-%"]


def skater(jersey, base, **stats):
    """Every KPI column at `base`, so a higher base beats a lower one in every KPI."""
    return {**{c: base for c in COLUMNS}, "All passes": 20, "No. FO": 20, "Team": "T", "Jersey": str(jersey), **stats}


class RatingTests(unittest.TestCase):
    def test_tier_boundaries(self):
        self.assertEqual([tier_of(mr) for mr in (40, 79, 80, 89, 90, 96, 97, 99)],
                         ["bronze", "bronze", "silver", "silver", "gold", "gold", "elite", "elite"])

    def test_best_and_worst_of_the_pool(self):
        ratings = skater_ratings([skater(1, 1), skater(2, 2), skater(3, 3)])
        self.assertEqual([ratings[("T", j)]["mr"] for j in (1, 2, 3)], [40, 40 + int(59 * 0.5 + 0.5), 99])

    def test_ties_share_the_best_rank(self):
        ratings = skater_ratings([skater(1, 2), skater(2, 2), skater(3, 1)])
        self.assertEqual([ratings[("T", j)]["mr"] for j in (1, 2, 3)], [99, 99, 40])

    def test_faceoffs_only_count_from_five_attempts(self):
        rows = [skater(1, 1, FOW=1, **{"FOW-%": 0.5}),
                skater(2, 0, FOW=6, **{"FOW-%": 0.6}),
                skater(3, 0, FOW=9, **{"FOW-%": 1.0, "No. FO": 1})]
        ratings = skater_ratings(rows)
        self.assertEqual((ratings[("T", 2)]["type"], ratings[("T", 2)]["mr"]), ("Faceoff Ace", 99))
        self.assertNotEqual(ratings[("T", 3)]["type"], "Faceoff Ace")

    def test_goalie_rating_ignores_empty_net_goals(self):
        def shot(result, xg, goalie="#1 G One"):
            return {"EventType": "Shot", "ShotResult": result, "ShotXG": str(xg), "EventSecondaryPlayerName": goalie,
                    "EventSecondaryTeam": "Home"}
        rows = [shot("Saved", 0.3), shot("Saved", 0.05), shot("Goal", 0.2), shot("Goal", 0.9, goalie="")]
        rating = goalie_ratings(rows, {"Home": "T"})[("T", 1)]
        self.assertEqual(rating["type"], "Goalie")
        # 2 of 3 saved (below 80 %), 1 of 2 high-danger saved, xG 0.55 against 1 goal
        self.assertEqual(rating["mr"], 40 + int(59 * (0.35 * 0.5 + 0.2 * ((0.55 - 1 + 2) / 4)) + 0.5))


if __name__ == "__main__":
    unittest.main()
