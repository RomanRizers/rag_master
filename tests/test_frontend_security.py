import unittest
from pathlib import Path


class FrontendSecurityTestCase(unittest.TestCase):
    def test_results_rendering_does_not_use_inner_html(self):
        app_js_path = Path("app/static/js/app.js")
        content = app_js_path.read_text(encoding="utf-8")

        self.assertNotIn("innerHTML", content)


if __name__ == "__main__":
    unittest.main()
