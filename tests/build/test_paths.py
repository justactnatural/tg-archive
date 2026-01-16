import unittest

try:
    import yaml  # noqa: F401
    import jinja2  # noqa: F401
    import feedgen  # noqa: F401
except Exception as e:  # pragma: no cover
    raise unittest.SkipTest("missing dependencies: {}".format(e))

from tgarchive.build import Build


class DummyDB:
    def get_media_messages(self):
        return []


class BuildPathTests(unittest.TestCase):
    def _make_build(self, publish_dir):
        config = {
            "publish_dir": publish_dir,
            "media_pages_dir": "media-pages",
            "publish_media_hashtags": True,
            "media_dir": "media",
        }
        return Build(config, DummyDB(), symlink=False)

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

    def test_build_media_pages_rejects_escape(self):
        config = {
            "publish_dir": "site",
            "media_pages_dir": "../escape",
            "publish_media_hashtags": True,
            "media_dir": "media",
        }
        b = Build(config, DummyDB(), symlink=False)
        b.media_template = object()
        with self.assertRaises(ValueError):
            b._build_media_pages()


if __name__ == "__main__":
    unittest.main()
