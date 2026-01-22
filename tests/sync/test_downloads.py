import os
import tempfile
import unittest
from unittest import mock

try:
    import yaml  # noqa: F401
    import telethon  # noqa: F401
except Exception as e:  # pragma: no cover
    raise unittest.SkipTest("missing dependencies: {}".format(e))

from tgarchive.sync import Sync


class SyncDownloadTests(unittest.TestCase):
    def test_download_media_uses_topic_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "orig.jpg")
            with open(fpath, "w", encoding="utf8") as f:
                f.write("x")

            s = Sync.__new__(Sync)
            s.config = {"media_dir": tmpdir}

            fake_client = mock.Mock()
            fake_client.download_media.return_value = fpath
            s.client = fake_client

            msg = mock.Mock()
            msg.id = 123
            msg.media = object()

            with mock.patch("tgarchive.sync.shutil.move") as move_mock, \
                    mock.patch("tgarchive.sync.os.makedirs") as makedirs_mock:
                basename, rel_name, thumb = s._download_media(msg, "topic-9")

            self.assertEqual(basename, "orig.jpg")
            self.assertEqual(rel_name, "topic-9/123.jpg")
            self.assertIsNone(thumb)
            makedirs_mock.assert_called()
            move_mock.assert_called()


if __name__ == "__main__":
    unittest.main()
