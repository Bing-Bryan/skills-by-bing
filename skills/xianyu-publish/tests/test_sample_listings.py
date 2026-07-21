import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import sample_listings as sample  # noqa: E402


class SampleListingsTest(unittest.TestCase):
    def test_parse_price(self):
        self.assertEqual(sample.parse_price("¥7,299"), 7299.0)
        self.assertEqual(sample.parse_price("1.2万"), 12000.0)
        self.assertEqual(sample.parse_price("1万2"), 12000.0)
        self.assertEqual(sample.parse_price("99新 ¥7299"), 7299.0)
        self.assertIsNone(sample.parse_price("面议"))

    def test_adaptive_collection_stops_when_stable(self):
        fixtures = {
            "q1": [
                {"item_id": str(i), "title": f"个人闲置 相机 {i}", "price": 100 + i % 3}
                for i in range(1, 31)
            ] + [{"item_id": "900", "title": "店铺严选 相机", "price": 80}],
            "q2": [
                {"item_id": str(i), "title": f"自用 相机 {i}", "price": 100 + i % 3}
                for i in range(25, 51)
            ],
            "q3": [
                {"item_id": str(i), "title": f"个人闲置 相机 {i}", "price": 150}
                for i in range(51, 70)
            ],
        }

        def searcher(query, limit, min_price, max_price):
            return fixtures[query][:limit]

        result = sample.collect(
            ["q1", "q2", "q3"], searcher, batch_limit=50,
            max_raw=200, min_candidates=40, stability_threshold=0.03,
        )
        self.assertTrue(result["stable"])
        self.assertEqual(result["stopped_reason"], "stable")
        self.assertEqual(result["queries_attempted"], ["q1", "q2"])
        self.assertGreaterEqual(result["candidate_count"], 40)
        self.assertEqual(result["likely_merchant_count"], 1)

    def test_title_exclusions_are_candidates_false(self):
        rows = sample.triage([
            {"item_id": "1", "title": "求购 相机", "price": 1},
            {"item_id": "2", "title": "个人闲置 相机", "price": 100},
        ])
        by_id = {row["item_id"]: row for row in rows}
        self.assertFalse(by_id["1"]["candidate"])
        self.assertTrue(by_id["2"]["candidate"])


if __name__ == "__main__":
    unittest.main()
