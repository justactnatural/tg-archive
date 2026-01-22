import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock

try:
    import yaml  # noqa: F401
except Exception as e:  # pragma: no cover
    raise unittest.SkipTest("missing dependencies: {}".format(e))

from tgarchive.db import DB, Message, User


class DBMessagesTests(unittest.TestCase):
    def test_message_timezone_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "data.sqlite")
            db = DB(db_path, tz="UTC")

            user = User(id=1, username="u", first_name=None, last_name=None, tags=[], avatar=None)
            db.insert_user(user)
            msg = Message(
                id=200,
                type="message",
                date=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
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

            fetched = list(db.get_messages(2024, 1, 0, 10))
            self.assertEqual(len(fetched), 1)
            self.assertEqual(fetched[0].id, 200)

    def test_db_commit_called(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "data.sqlite")
            db = DB(db_path)
            db.conn = mock.Mock()
            db.commit()
            db.conn.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
