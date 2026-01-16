import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock

try:
    import yaml  # noqa: F401
    import jinja2  # noqa: F401
    import feedgen  # noqa: F401
except Exception as e:  # pragma: no cover
    raise unittest.SkipTest("missing dependencies: {}".format(e))

from tgarchive.build import Build
from tgarchive.db import Message, Media, User


class DummyDB:
    def __init__(self, messages):
        self._messages = messages

    def get_media_messages(self):
        return self._messages


class BuildRssTests(unittest.TestCase):
    def _make_msg(self, media_dir):
        media_path = os.path.join(media_dir, "100.jpg")
        with open(media_path, "w", encoding="utf8") as f:
            f.write("x")

        user = User(id=1, username="u", first_name=None, last_name=None, tags=[], avatar=None)
        media = Media(id=10, type="photo", url="100.jpg", title="100.jpg", description=None, thumb=None)
        return Message(
            id=100,
            type="message",
            date=datetime.now(timezone.utc),
            edit_date=None,
            content="test",
            reply_to=None,
            user=user,
            media=media,
            topic_id=None,
            topic_title=None,
        )

    def test_build_rss_without_magic(self):
        import tgarchive.build as build_mod

        with tempfile.TemporaryDirectory() as tmpdir:
            media_dir = os.path.join(tmpdir, "media")
            os.makedirs(media_dir, exist_ok=True)
            msg = self._make_msg(media_dir)

            config = {
                "publish_dir": tmpdir,
                "media_dir": media_dir,
                "site_url": "https://example.com",
                "site_name": "x",
                "site_description": "x",
                "group": "x",
                "publish_rss_feed": True,
                "rss_feed_entries": 10,
            }
            b = Build(config, DummyDB([msg]), symlink=False)
            b.page_ids = {100: "2020-01.html"}

            old_magic = build_mod.magic
            build_mod.magic = None
            try:
                b._build_rss([msg], "index.xml", "index.atom")
            finally:
                build_mod.magic = old_magic

            self.assertTrue(os.path.exists(os.path.join(tmpdir, "index.xml")))

    def test_build_rss_with_magic_calls_from_file(self):
        import tgarchive.build as build_mod

        with tempfile.TemporaryDirectory() as tmpdir:
            media_dir = os.path.join(tmpdir, "media")
            os.makedirs(media_dir, exist_ok=True)
            msg = self._make_msg(media_dir)

            config = {
                "publish_dir": tmpdir,
                "media_dir": media_dir,
                "site_url": "https://example.com",
                "site_name": "x",
                "site_description": "x",
                "group": "x",
                "publish_rss_feed": True,
                "rss_feed_entries": 10,
            }
            b = Build(config, DummyDB([msg]), symlink=False)
            b.page_ids = {100: "2020-01.html"}

            fake_magic = mock.Mock()
            fake_magic.from_file.return_value = "image/jpeg"

            old_magic = build_mod.magic
            build_mod.magic = fake_magic
            try:
                b._build_rss([msg], "index.xml", "index.atom")
            finally:
                build_mod.magic = old_magic

            fake_magic.from_file.assert_called()


if __name__ == "__main__":
    unittest.main()
