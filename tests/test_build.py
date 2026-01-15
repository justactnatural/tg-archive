import os
import tempfile
import unittest
from datetime import datetime, timezone

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


class MigrationDB(DummyDB):
    def __init__(self, messages):
        super().__init__(messages)
        self.updated = []
        self.commits = 0

    def update_media_paths(self, media_id, url, thumb):
        self.updated.append((media_id, url, thumb))

    def commit(self):
        self.commits += 1


class BuildTests(unittest.TestCase):
    def _make_build(self, publish_dir):
        config = {
            "publish_dir": publish_dir,
            "media_pages_dir": "media-pages",
            "publish_media_hashtags": True,
            "media_dir": "media",
        }
        b = Build(config, DummyDB([]), symlink=False)
        return b

    def test_dir_depth_normalization(self):
        b = self._make_build("site")
        self.assertEqual(b._dir_depth("./media-pages"), 1)
        self.assertEqual(b._dir_depth("media/pages"), 2)
        self.assertEqual(b._dir_depth("media/./pages"), 2)
        self.assertEqual(b._dir_depth("media/../pages"), 1)

    def test_is_unsafe_path(self):
        b = self._make_build("site")
        self.assertTrue(b._is_unsafe_path("../media-pages"))
        self.assertTrue(b._is_unsafe_path("/abs/path"))
        self.assertFalse(b._is_unsafe_path("media-pages"))
        self.assertFalse(b._is_unsafe_path("media/../pages"))

    def test_hashtag_dedupes_messages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            user = User(id=1, username="u", first_name=None, last_name=None, tags=[], avatar=None)
            media = Media(id=10, type="photo", url="file.jpg", title="file.jpg", description=None, thumb=None)
            msg = Message(
                id=100,
                type="message",
                date=None,
                edit_date=None,
                content="#foo #foo",
                reply_to=None,
                user=user,
                media=media,
                topic_id=None,
                topic_title=None,
            )

            config = {
                "publish_dir": tmpdir,
                "media_pages_dir": "media-pages",
                "publish_media_hashtags": True,
                "media_dir": "media",
                "publish_rss_feed": False,
            }
            b = Build(config, DummyDB([msg]), symlink=False)
            b.page_ids = {100: "2020-01.html"}

            tmpl_path = os.path.join(tmpdir, "media_template.html")
            with open(tmpl_path, "w", encoding="utf8") as f:
                f.write("{% for m in messages %}{{ m.id }}\n{% endfor %}")
            b.load_media_template(tmpl_path)

            b._build_media_pages()

            tag_path = os.path.join(tmpdir, "media-pages", "tag-foo.html")
            with open(tag_path, "r", encoding="utf8") as f:
                content = f.read()

            self.assertEqual(content.count("100"), 1)

    def test_topic_dir_uses_id(self):
        b = self._make_build("site")
        self.assertEqual(b._topic_dir(123, "Photos!"), "topic-123")

    def test_migrate_media_moves_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            media_dir = os.path.join(tmpdir, "media")
            os.makedirs(media_dir, exist_ok=True)

            old_path = os.path.join(media_dir, "100.jpg")
            thumb_path = os.path.join(media_dir, "thumb_100.jpg")
            with open(old_path, "w", encoding="utf8") as f:
                f.write("x")
            with open(thumb_path, "w", encoding="utf8") as f:
                f.write("x")

            user = User(id=1, username="u", first_name=None, last_name=None, tags=[], avatar=None)
            media = Media(id=10, type="photo", url="100.jpg", title="100.jpg", description=None, thumb="thumb_100.jpg")
            msg = Message(
                id=100,
                type="message",
                date=datetime.now(timezone.utc),
                edit_date=None,
                content="test",
                reply_to=None,
                user=user,
                media=media,
                topic_id=55,
                topic_title="Photos",
            )

            config = {
                "publish_dir": tmpdir,
                "media_pages_dir": "media-pages",
                "publish_media_hashtags": True,
                "media_dir": media_dir,
                "media_by_topic": True,
            }
            db = MigrationDB([msg])
            b = Build(config, db, symlink=False)
            b._migrate_media_by_topic()

            new_path = os.path.join(media_dir, "topic-55", "100.jpg")
            new_thumb = os.path.join(media_dir, "topic-55", "thumb_100.jpg")
            self.assertTrue(os.path.exists(new_path))
            self.assertTrue(os.path.exists(new_thumb))
            self.assertEqual(db.updated[-1][1], "topic-55/100.jpg")

    def test_build_rss_without_magic(self):
        import tgarchive.build as build_mod

        with tempfile.TemporaryDirectory() as tmpdir:
            media_dir = os.path.join(tmpdir, "media")
            os.makedirs(media_dir, exist_ok=True)
            media_path = os.path.join(media_dir, "100.jpg")
            with open(media_path, "w", encoding="utf8") as f:
                f.write("x")

            user = User(id=1, username="u", first_name=None, last_name=None, tags=[], avatar=None)
            media = Media(id=10, type="photo", url="100.jpg", title="100.jpg", description=None, thumb=None)
            msg = Message(
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

    def test_build_media_pages_rejects_escape(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "publish_dir": tmpdir,
                "media_pages_dir": "../escape",
                "publish_media_hashtags": True,
                "media_dir": "media",
            }
            b = Build(config, DummyDB([]), symlink=False)
            tmpl_path = os.path.join(tmpdir, "media_template.html")
            with open(tmpl_path, "w", encoding="utf8") as f:
                f.write("x")
            b.load_media_template(tmpl_path)

            with self.assertRaises(ValueError):
                b._build_media_pages()


if __name__ == "__main__":
    unittest.main()
