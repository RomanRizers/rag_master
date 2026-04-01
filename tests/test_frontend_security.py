import unittest
from pathlib import Path


class FrontendSecurityTestCase(unittest.TestCase):
    def test_react_frontend_does_not_use_inner_html(self):
        for path in Path("frontend/src").rglob("*"):
            if path.suffix not in {".ts", ".tsx"}:
                continue
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("innerHTML", content, f"Found innerHTML in {path}")


if __name__ == "__main__":
    unittest.main()
