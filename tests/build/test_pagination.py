import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock

try:
    import yaml  # noqa: F401
    import jinja2  # noqa: F401
except Exception as e:  # pragma: no cover
    raise unittest.SkipTest("missing dependencies: {}".format(e))

from tgarchive.build import Build
from tgarchive.db import Month


class DummyDB:
    def __init__(self):
        self.calls = []

    def get_timeline(self):
        date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        return [Month(date=date, slug="2024-01", label="Jan 2024", count=3)]

    def get_dayline(self, year, month, limit=500):
        date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        return [mock.Mock(slug="2024-01-01", date=date, count=3, page=1)]

    def get_message_count(self, year, month):
        return 3

    def get_messages_page(self, year, month, offset=0, limit=500):
        self.calls.append((offset, limit))
        return []


class BuildPaginationTests(unittest.TestCase):
    def test_build_uses_page_offsets(self):
        with tempfile.TemporaryDirectory() as base_dir:
            prev_cwd = os.getcwd()
            os.chdir(base_dir)
            os.makedirs("static", exist_ok=True)
            with open(os.path.join("static", "placeholder.txt"), "w", encoding="utf8") as f:
                f.write("x")

            config = {
                "publish_dir": "site",
                "static_dir": "static",
                "per_page": 2,
                "publish_rss_feed": False,
                "rss_feed_entries": 10,
                "publish_media_index": False,
                "media_dir": "media",
            }
            db = DummyDB()
            b = Build(config, db, symlink=False)

            tmpl_path = os.path.join(base_dir, "template.html")
            with open(tmpl_path, "w", encoding="utf8") as f:
                f.write("ok")
            b.load_template(tmpl_path)
            try:
                b.build()
                self.assertEqual(db.calls, [(0, 2), (2, 2)])
            finally:
                os.chdir(prev_cwd)


if __name__ == "__main__":
    unittest.main()
