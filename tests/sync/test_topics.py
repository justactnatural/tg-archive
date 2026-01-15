import unittest

try:
    import yaml  # noqa: F401
    import telethon  # noqa: F401
except Exception as e:  # pragma: no cover
    raise unittest.SkipTest("missing dependencies: {}".format(e))

from tgarchive.sync import Sync


class SyncTopicTests(unittest.TestCase):
    def test_slugify_fallback_uses_topic_id(self):
        s = Sync.__new__(Sync)
        self.assertEqual(s._slugify("!!!", topic_id=7), "topic-7")
        self.assertEqual(s._slugify("Photos!", topic_id=7), "photos")

    def test_get_topic_dir_prefers_id(self):
        s = Sync.__new__(Sync)
        s.config = {"media_by_topic": True}
        self.assertEqual(s._get_topic_dir(5, "😀"), "topic-5")

    def test_get_topic_id_from_reply_to(self):
        class ReplyTo:
            reply_to_top_id = 99

        class Msg:
            reply_to_top_id = None
            reply_to = ReplyTo()
            action = None

        s = Sync.__new__(Sync)
        self.assertEqual(s._get_topic_id(Msg()), 99)

    def test_get_topic_id_prefers_top_id(self):
        class Msg:
            reply_to_top_id = 123
            reply_to = None
            action = None

        s = Sync.__new__(Sync)
        self.assertEqual(s._get_topic_id(Msg()), 123)

    def test_get_topic_title_prefers_forum_topic(self):
        class ForumTopic:
            title = "Topic A"

        class Msg:
            action = None
            forum_topic = ForumTopic()

        s = Sync.__new__(Sync)
        self.assertEqual(s._get_topic_title(Msg()), "Topic A")


if __name__ == "__main__":
    unittest.main()
