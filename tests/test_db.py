import os
import tempfile
import unittest

try:
    import yaml  # noqa: F401
except Exception as e:  # pragma: no cover
    raise unittest.SkipTest("missing dependencies: {}".format(e))

from tgarchive.db import DB, Media, Message, User


class DBTests(unittest.TestCase):
    def test_topics_table_and_media_messages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "data.sqlite")
            db = DB(db_path)

            cur = db.conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='topics'")
            self.assertIsNotNone(cur.fetchone())

            db.insert_topic(55, "Topic A")
            user = User(id=1, username="u", first_name=None, last_name=None, tags=[], avatar=None)
            db.insert_user(user)
            media = Media(id=10, type="photo", url="file.jpg", title="file.jpg", description=None, thumb=None)
            db.insert_media(media)
            msg = Message(
                id=100,
                type="message",
                date=db._parse_date("2024-01-01T00:00:00+0000"),
                edit_date=None,
                content="test",
                reply_to=None,
                user=user,
                media=media,
                topic_id=55,
                topic_title="Topic A",
            )
            db.insert_message(msg)
            db.commit()

            msgs = list(db.get_media_messages())
            self.assertEqual(len(msgs), 1)
            self.assertEqual(msgs[0].topic_id, 55)
            self.assertEqual(msgs[0].topic_title, "Topic A")


if __name__ == "__main__":
    unittest.main()
