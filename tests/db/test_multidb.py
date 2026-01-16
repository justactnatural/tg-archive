import os
import tempfile
import unittest
from datetime import datetime, timezone

try:
    import yaml  # noqa: F401
except Exception as e:  # pragma: no cover
    raise unittest.SkipTest("missing dependencies: {}".format(e))

from tgarchive.db import DB, MultiDB, Message, User


class MultiDBTests(unittest.TestCase):
    def _make_db(self, base_dir, name):
        db_path = os.path.join(base_dir, "{}.sqlite".format(name))
        return DB(db_path)

    def _insert_msg(self, db, msg_id, date):
        user = User(id=1, username="u", first_name=None, last_name=None, tags=[], avatar=None)
        db.insert_user(user)
        msg = Message(
            id=msg_id,
            type="message",
            date=date,
            edit_date=None,
            content="hello",
            reply_to=None,
            user=user,
            media=None,
            topic_id=None,
            topic_title=None,
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


if __name__ == "__main__":
    unittest.main()
