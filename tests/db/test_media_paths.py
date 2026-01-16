import os
import tempfile
import unittest

try:
    import yaml  # noqa: F401
except Exception as e:  # pragma: no cover
    raise unittest.SkipTest("missing dependencies: {}".format(e))

from tgarchive.db import DB, Media


class DBMediaPathsTests(unittest.TestCase):
    def test_update_media_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "data.sqlite")
            db = DB(db_path)

            media = Media(id=10, type="photo", url="old.jpg", title="old.jpg", description=None, thumb="t.jpg")
            db.insert_media(media)
            db.commit()

            db.update_media_paths(10, "new.jpg", "t2.jpg")
            db.commit()

            cur = db.conn.cursor()
            cur.execute("SELECT url, thumb FROM media WHERE id = 10")
            url, thumb = cur.fetchone()
            self.assertEqual(url, "new.jpg")
            self.assertEqual(thumb, "t2.jpg")


if __name__ == "__main__":
    unittest.main()
