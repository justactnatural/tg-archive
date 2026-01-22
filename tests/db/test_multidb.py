import os
import tempfile
import unittest
from datetime import datetime, timezone

try:
    import yaml  # noqa: F401
except Exception as e:  # pragma: no cover
    raise unittest.SkipTest("missing dependencies: {}".format(e))

from tgarchive.db import DB, Media, Message, MultiDB, User


class MultiDBTests(unittest.TestCase):
    def _make_db(self, base_dir, name):
        db_path = os.path.join(base_dir, "{}.sqlite".format(name))
        return DB(db_path)

    def _insert_msg(self, db, msg_id, date, topic_id=None, topic_title=None):
        user = User(id=1, username="u", first_name=None, last_name=None, tags=[], avatar=None)
        db.insert_user(user)
        if topic_id and topic_title:
            db.insert_topic(topic_id, topic_title)
        msg = Message(
            id=msg_id,
            type="message",
            date=date,
            edit_date=None,
            content="hello",
            reply_to=None,
            user=user,
            media=None,
            topic_id=topic_id,
            topic_title=topic_title,
        )
        db.insert_message(msg)
        db.commit()

    def test_multidb_merges_counts_and_messages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db1 = self._make_db(tmpdir, "g1")
            db2 = self._make_db(tmpdir, "g2")

            self._insert_msg(db1, 1, datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
            self._insert_msg(db2, 1, datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc))

            groups = [
                {"db": db1, "key": "g1", "media_prefix": ""},
                {"db": db2, "key": "g2", "media_prefix": ""},
            ]
            mdb = MultiDB(groups, tz="UTC")

            self.assertEqual(mdb.get_message_count(2024, 1), 2)
            messages = list(mdb.get_messages_page(2024, 1, 0, 10))
            self.assertEqual([m.id for m in messages], ["g1-1", "g2-1"])

            dayline = list(mdb.get_dayline(2024, 1, limit=10))
            self.assertEqual(len(dayline), 2)

    def test_multidb_media_prefix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db1 = self._make_db(tmpdir, "g1")
            user = User(id=1, username="u", first_name=None, last_name=None, tags=[], avatar=None)
            db1.insert_user(user)
            msg = Message(
                id=1,
                type="message",
                date=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
                edit_date=None,
                content="hello",
                reply_to=None,
                user=user,
                media=Media(id=1, type="photo", url="v/1.mp4", title="v", description=None, thumb="t.jpg"),
                topic_id=None,
                topic_title=None,
            )
            db1.insert_media(msg.media)
            db1.insert_message(msg)
            db1.commit()

            groups = [{"db": db1, "key": "g1", "media_prefix": "media/g1"}]
            mdb = MultiDB(groups, tz="UTC")
            media = list(mdb.get_media_messages())[0].media
            self.assertEqual(media.url, "media/g1/v/1.mp4")
            self.assertEqual(media.thumb, "media/g1/t.jpg")

    def test_multidb_topics_include_group_label(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db1 = self._make_db(tmpdir, "g1")
            self._insert_msg(db1, 1, datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
            self._insert_msg(db1, 2, datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
                             topic_id=9, topic_title="Movies")

            groups = [{"db": db1, "key": "g1", "label": "Group A", "media_prefix": ""}]
            mdb = MultiDB(groups, tz="UTC")
            messages = list(mdb.get_messages_page(2024, 1, 0, 10))

            self.assertEqual(messages[0].topic_id, "g1-general")
            self.assertEqual(messages[0].topic_title, "Group A / General")
            self.assertEqual(messages[1].topic_id, "g1-9")
            self.assertEqual(messages[1].topic_title, "Group A / Movies")


if __name__ == "__main__":
    unittest.main()
