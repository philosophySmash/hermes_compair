import re
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from asgi_test_helper import request

UI_PATH = ROOT / "src" / "hermes_compair" / "static" / "index.html"
README_PATH = ROOT / "README.md"


class LocalDashboardArtifactTests(unittest.TestCase):
    def test_static_ui_artifact_exists_with_required_safety_warning(self):
        self.assertTrue(UI_PATH.exists(), "Expected static local UI artifact to exist")
        html = UI_PATH.read_text(encoding="utf-8")

        self.assertIn("Local prototype", html)
        self.assertIn("review only", html.lower())
        self.assertIn("does not approve", html.lower())
        self.assertIn("contract", html.lower())
        self.assertIn("does not provide legal advice", html.lower())

    def test_static_ui_contains_required_read_only_sections_and_api_endpoints(self):
        html = UI_PATH.read_text(encoding="utf-8")
        required_text = [
            "Document register",
            "Proposal list",
            "Timeline data",
            "Graph data",
            "/documents",
            "/proposals",
            "/timeline",
            "/graph",
        ]
        for text in required_text:
            with self.subTest(text=text):
                self.assertIn(text, html)

    def test_static_ui_does_not_use_external_assets_or_authority_wording(self):
        html = UI_PATH.read_text(encoding="utf-8")

        self.assertNotRegex(html, r"https?://")
        self.assertNotRegex(html, r"//[^\s'\"]+")
        self.assertNotIn("cdn", html.casefold())

        forbidden_patterns = [
            r"\bcan\s+apply\s+contract\s+changes\b",
            r"\bcan\s+approve\s+contract\s+changes\b",
            r"\bauthorized\s+to\s+approve\b",
            r"\bproduction-ready\b",
        ]
        for pattern in forbidden_patterns:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, html, flags=re.IGNORECASE))

    def test_generated_user_facing_text_avoids_unicode_dashes(self):
        html = UI_PATH.read_text(encoding="utf-8")
        readme = README_PATH.read_text(encoding="utf-8")
        combined = html + "\n" + readme

        self.assertNotIn(chr(8212), combined)
        self.assertNotIn(chr(8211), combined)

    def test_api_serves_static_dashboard_without_mutating_database(self):
        from hermes_compair.api import create_app

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "missing" / "project.db"
            response = request(create_app(db_path), "GET", "/ui")

            self.assertEqual(response.status_code, 200)
            self.assertIn("Local prototype", response.text)
            self.assertIn("/documents", response.text)
            self.assertFalse(db_path.exists())


if __name__ == "__main__":
    unittest.main()
