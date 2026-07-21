import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "xianyu-publish" / "scripts"))
import deep_read_listings as deep  # noqa: E402


class DeepReadListingsTest(unittest.TestCase):
    def test_summary_is_compact_and_uses_engagement_as_supporting_data(self):
        rows = [
            {
                "item_id": "1", "title": "个人闲置 X-S10", "price": "¥6500",
                "want_count": "20", "browse_count": "200", "collect_count": "10",
                "status": "在售", "description": "A" * 500, "image_count": "9",
                "image_urls": ["https://example.com/1.jpg"],
            },
            {
                "item_id": "2", "title": "自用 X-S10 套机", "price": "¥6900",
                "want_count": "30", "browse_count": "300", "collect_count": "12",
                "status": "已售", "description": "描述", "image_count": "8",
                "image_urls": ["https://example.com/2.jpg"],
            },
        ]
        result = deep.summarize(rows, description_chars=120)
        self.assertEqual(result["price_summary"]["median"], 6700.0)
        self.assertEqual(result["want_view_ratio_summary"]["median"], 0.1)
        self.assertEqual(result["status_counts"], {"在售": 1, "已售": 1})
        self.assertEqual(len(result["items"][0]["description_excerpt"]), 120)
        self.assertNotIn("image_urls", result["items"][0])
        self.assertIn("not verified transaction prices", result["note"])


if __name__ == "__main__":
    unittest.main()
