"""Tests for Directus CMS materials syncing, R2 URL allowlist, and detail rendering."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from cms_materials import (
    CMS_MATERIALS_PATH, is_approved_cms_media_url, render_cms_detail,
    render_cms_home_section, validate_cms_materials,
)
from common import load_data
from sync_cms_materials import normalize_records, sync_to_disk


class CmsMaterialsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config, cls.prompts = load_data()

    def sample_raw(self):
        return [
            {
                "id": "c6ce066a-8200-4eef-b07a-a366797b9219",
                "title": "Kingfisher Dive Photo",
                "prompt": "Ultra-photorealistic kingfisher diving into clear water.",
                "status": "ready",
                "author_x_url": "https://x.com/NovaXCode",
                "source_post_url": "https://x.com/NovaXCode/status/2118381855166881928",
                "source_published_at": "2026-11-26T08:00:00Z",
                "tags": ["wildlife", "photo"],
                "notes": "Creator-reported GPT Image 2.6.",
                "date_created": "2026-11-27T08:02:38.906Z",
                "image_url": "https://awesome.raphael.app/materials/15bc5239-2b24-4534-bba1-33239f1c38d5.jpg",
                "r2_object_key": "materials/15bc5239-2b24-4534-bba1-33239f1c38d5.jpg",
            }
        ]

    def test_r2_allowlist_blocks_third_party_hotlinks(self):
        self.assertTrue(is_approved_cms_media_url("https://awesome.raphael.app/materials/abc.jpg", self.config))
        self.assertFalse(is_approved_cms_media_url("https://pbs.twimg.com/media/abc.jpg", self.config))
        self.assertFalse(is_approved_cms_media_url("http://awesome.raphael.app/materials/abc.jpg", self.config))

    def test_normalize_and_render_detail_and_home(self):
        items, total = normalize_records(self.sample_raw(), self.config, {})
        self.assertEqual(total, 1)
        self.assertEqual(items[0]["id"], "cms-c6ce066a")
        self.assertEqual(items[0]["author"], "@NovaXCode")
        self.assertEqual(items[0]["image_url"], "https://awesome.raphael.app/materials/15bc5239-2b24-4534-bba1-33239f1c38d5.jpg")

        en_detail = render_cms_detail(items[0], self.config, "en")
        zh_detail = render_cms_detail(items[0], self.config, "zh-CN")
        self.assertIn("Ultra-photorealistic kingfisher", en_detail)
        self.assertIn("https://awesome.raphael.app/materials/15bc5239-2b24-4534-bba1-33239f1c38d5.jpg", zh_detail)
        self.assertIn("cases/cms-c6ce066a/README.md", "\n".join(render_cms_home_section(self.config, items, "en")))
        self.assertIn("README.md#cms-latest", "\n".join(render_cms_home_section(self.config, items, "ja-JP")))

    def test_cms_items_increment_readme_category_counts_and_render_in_category(self):
        from build_readme import render_readme
        items, _ = normalize_records(self.sample_raw(), self.config, {})
        with patch("homepage.read_cases", return_value=[]), patch("homepage.read_cms_materials", return_value=items):
            en_text = render_readme(self.config, [], "en")
        nav = en_text.split('<a id="categories"></a>', 1)[1].split('<a id="contents"></a>', 1)[0]
        self.assertIn("[All (1)](#all-cases)", nav)
        self.assertIn(f"(#category-{items[0]['category']})", nav)
        self.assertIn(" (1)](", nav)
        cat_section = en_text.split(f'<a id="category-{items[0]["category"]}"></a>', 1)[1]
        self.assertIn("cases/cms-c6ce066a/README.md", cat_section)

    def test_sync_skips_timestamp_churn_when_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "content").mkdir()
            (root / "site.config.json").write_text(json.dumps(self.config), encoding="utf-8")
            (root / "content" / "prompts.json").write_text("[]", encoding="utf-8")
            with (
                patch("sync_cms_materials.ROOT", root),
                patch("cms_materials.ROOT", root),
                patch("common.ROOT", root),
                patch("sync_cms_materials.read_cases", return_value=[]),
                patch("sync_cms_materials.fetch_all_materials", return_value=self.sample_raw()),
            ):
                changed1, count1, total1 = sync_to_disk(
                    "https://raphael-cms.colorepistle.com",
                    "token-123",
                    now=datetime(2026, 11, 27, 8, 0, tzinfo=timezone.utc),
                )
                self.assertTrue(changed1)
                self.assertEqual((count1, total1), (1, 1))
                changed2, _, _ = sync_to_disk(
                    "https://raphael-cms.colorepistle.com",
                    "token-123",
                    now=datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc),
                )
                self.assertFalse(changed2)
                stored = json.loads((root / CMS_MATERIALS_PATH).read_text(encoding="utf-8"))
                self.assertEqual(stored["synced_at"], "2026-11-27T08:00:00Z")

    def test_validator_rejects_unapproved_remote_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "content").mkdir()
            bad_store = {
                "collection": "materials",
                "cms_base_url": "https://raphael-cms.colorepistle.com",
                "media_base_url": "https://awesome.raphael.app/materials/",
                "synced_at": "2026-11-27T08:00:00Z",
                "total_cms_records": 1,
                "items": [{
                    "id": "cms-deadbeef",
                    "cms_id": "deadbeef",
                    "title": "Bad",
                    "prompt": "Prompt",
                    "category": "characters-consistency",
                    "tags": [],
                    "image_url": "https://pbs.twimg.com/media/not-allowed.jpg",
                    "r2_object_key": None,
                    "author": "@test",
                    "author_url": "https://x.com/test",
                    "source_url": "https://x.com/test/status/1",
                    "source_published_at": None,
                    "added_at": "2026-11-27",
                    "date_created": "2026-11-27T08:00:00Z",
                    "status": "ready",
                    "notes": None,
                    "matched_curated_case_id": None,
                }],
            }
            (root / CMS_MATERIALS_PATH).write_text(json.dumps(bad_store), encoding="utf-8")
            errors = []
            with patch("cms_materials.ROOT", root), patch("common.ROOT", root):
                validate_cms_materials(self.config, [], [], errors)
            self.assertTrue(any("approved R2 prefix" in err for err in errors))


if __name__ == "__main__":
    unittest.main()
