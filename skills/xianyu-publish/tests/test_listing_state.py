import stat
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import listing_state as state_api  # noqa: E402


UTC = timezone.utc


class ListingStateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.temp.name) / ".xianyu-publish"
        self.start = datetime(2026, 7, 17, 0, 0, tzinfo=UTC)
        self.state = state_api.create_state(
            "123456", "测试商品", 1000, 900, 950, 850, trial_days=7, at=self.start,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_private_state_permissions_and_gitignore(self):
        state_api.save_state(self.state_dir, self.state)
        path = state_api.item_path(self.state_dir, "123456")
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertTrue((self.state_dir / ".gitignore").exists())

    def test_snapshots_and_digest_delta(self):
        state_api.add_snapshot(
            self.state,
            {"status": "在售", "price": "¥1000", "browse_count": "10", "want_count": "2", "collect_count": "1"},
            self.start,
        )
        state_api.add_snapshot(
            self.state,
            {"status": "在售", "price": "¥1000", "browse_count": "18", "want_count": "3", "collect_count": "2"},
            self.start + timedelta(days=1),
        )
        digest = state_api.digest_state(self.state, self.start + timedelta(days=1))
        self.assertEqual(digest["views_delta"], 8)
        self.assertEqual(digest["wants_delta"], 1)
        self.assertEqual(digest["conclusion"], "continue_observing")

    def test_snapshot_parses_wan_amounts(self):
        state_api.add_snapshot(
            self.state,
            {"status": "在售", "price": "1.2万", "browse_count": "1.1万"},
            self.start,
        )
        snapshot = self.state["snapshots"][-1]
        self.assertEqual(snapshot["price"], 12000.0)
        self.assertEqual(snapshot["views"], 11000.0)

    def test_inquiry_hold_expires(self):
        state_api.set_inquiry_hold(self.state, 48, self.start)
        self.assertEqual(self.state["phase"], "negotiation_hold")
        state_api.refresh_phase(self.state, self.start + timedelta(hours=49))
        self.assertEqual(self.state["phase"], "active")

    def test_experiment_due_conclusion_and_baseline(self):
        state_api.add_snapshot(
            self.state, {"status": "在售", "price": "1000", "browse_count": "5"}, self.start,
        )
        state_api.start_experiment(self.state, "title", "新标题", True, hours=72, at=self.start)
        self.assertEqual(self.state["experiment"]["baseline_snapshot_at"], state_api.iso(self.start))
        early = state_api.digest_state(self.state, self.start + timedelta(hours=24))
        self.assertEqual(early["conclusion"], "continue_observing")
        due = state_api.digest_state(self.state, self.start + timedelta(hours=73))
        self.assertEqual(due["conclusion"], "experiment_evaluation_due")

    def test_sold_removes_private_floor(self):
        state_api.add_snapshot(self.state, {"status": "已售"}, self.start)
        self.assertEqual(self.state["phase"], "sold")
        self.assertNotIn("private_floor", self.state["pricing"])
        self.assertIsNotNone(self.state["retention_until"])

    def test_paused_is_not_sold(self):
        state_api.add_snapshot(self.state, {"status": "已下架"}, self.start)
        self.assertEqual(self.state["phase"], "paused")
        self.assertIn("private_floor", self.state["pricing"])


if __name__ == "__main__":
    unittest.main()
