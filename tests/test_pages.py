"""Verify the differentiated GitHub Pages cheat sheet generator."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_pages import build_site


class PagesTests(unittest.TestCase):
    def test_build_site_outputs_differentiated_cheat_sheet_with_repo_backlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            build_site(out)
            html_text = (out / "index.html").read_text(encoding="utf-8")
            robots = (out / "robots.txt").read_text(encoding="utf-8")
            sitemap = (out / "sitemap.xml").read_text(encoding="utf-8")
            self.assertTrue((out / ".nojekyll").is_file())
            self.assertIn("Prompt &amp; API Cheat Sheet", html_text)
            self.assertIn("ChatGPT Images 2.6", html_text)
            self.assertIn("gpt-image-2.6-flare", html_text)
            self.assertIn("gpt-image-2.6-sunburst", html_text)
            self.assertIn("https://github.com/RaphaelAI-OpenLab/awesome-gpt-image-2.6-prompts", html_text)
            self.assertIn("https://raphaelai-openlab.github.io/awesome-gpt-image-2.6-prompts/sitemap.xml", robots)
            self.assertIn("<loc>https://raphaelai-openlab.github.io/awesome-gpt-image-2.6-prompts/</loc>", sitemap)


if __name__ == "__main__":
    unittest.main()
