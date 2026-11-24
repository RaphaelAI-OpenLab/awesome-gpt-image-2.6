from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import sys
from unittest import TestCase
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from sync_cms_stats import CmsStats, fetch_material_count, replace_readme_stats


class CmsStatsTests(TestCase):
    def test_refresh_updates_only_cms_count_and_time(self):
        before = (
            "| 📝 Total prompts | **129** |\n"
            "| 🗂️ CMS materials | **—** |\n"
            "| 🔄 Last updated | **2026-11-20 UTC 12:00:00** |\n\n"
            "<!-- cms-stats pending -->\n\n"
            "## All cases\n\nCase content.\n"
        )
        stats = CmsStats(42, datetime(2026, 11, 24, 8, 17, tzinfo=timezone.utc))
        self.assertEqual(
            replace_readme_stats(before, "en", stats),
            before.replace("**—**", "**42**")
            .replace("2026-11-20 UTC 12:00:00", "2026-11-24 UTC 08:17:00")
            .replace("cms-stats pending", "cms-stats 42 2026-11-24T08:17:00Z"),
        )

    def test_no_count_is_not_treated_as_zero(self):
        with patch("sync_cms_stats.urlopen", return_value=BytesIO(b'{"data":[{"count":{"id":"0"}}]}')) as open_url:
            self.assertEqual(fetch_material_count("https://cms.example.com", "test-token"), 0)
            self.assertEqual(open_url.call_args.args[0].get_header("User-agent"), "Raphael-CMS-Stats/1.0")
        with patch("sync_cms_stats.urlopen", return_value=BytesIO(b'{"data":[{"count":{}}]}')):
            with self.assertRaises(KeyError):
                fetch_material_count("https://cms.example.com", "test-token")
