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


class MigrationDB:
    def __init__(self, messages):
        self._messages = messages
        self.updated = []
        self.commits = 0

    def get_media_messages(self):
        return self._messages

    def update_media_paths(self, media_id, url, thumb):
        self.updated.append((media_id, url, thumb))

    def commit(self):
        self.commits += 1


class BuildMigrationTests(unittest.TestCase):
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

    def test_topic_dir_uses_id(self):
        config = {
            "publish_dir": "site",
            "media_pages_dir": "media-pages",
            "publish_media_hashtags": True,
            "media_dir": "media",
        }
        b = Build(config, MigrationDB([]), symlink=False)
        self.assertEqual(b._topic_dir(123, "Photos!"), "topic-123")


if __name__ == "__main__":
    unittest.main()
