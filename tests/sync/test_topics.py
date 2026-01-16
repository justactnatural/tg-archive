import unittest

try:
    import yaml  # noqa: F401
    import telethon  # noqa: F401
except Exception as e:  # pragma: no cover
    raise unittest.SkipTest("missing dependencies: {}".format(e))

from tgarchive.sync import Sync


class SyncTopicTests(unittest.TestCase):
    def test_resolve_topic_ids_by_title(self):
        s = Sync.__new__(Sync)
        topics = [{"id": 1, "title": "Movies"}, {"id": 2, "title": "Photos"}]
        resolved = s._resolve_topic_ids([], ["Movies"], topics, interactive=False, input_func=lambda _: "")
        self.assertEqual(resolved, [1])

    def test_resolve_topic_ids_duplicate_title_noninteractive(self):
        s = Sync.__new__(Sync)
        topics = [{"id": 1, "title": "Movies"}, {"id": 2, "title": "Movies"}]
        with self.assertRaises(ValueError):
            s._resolve_topic_ids([], ["Movies"], topics, interactive=False, input_func=lambda _: "")

    def test_should_include_topic_general(self):
        s = Sync.__new__(Sync)
        s.allowed_topic_ids = {1}
        s.include_general = True
        self.assertTrue(s._should_include_topic(None))
        self.assertTrue(s._should_include_topic(1))
        self.assertFalse(s._should_include_topic(2))


if __name__ == "__main__":
    unittest.main()
