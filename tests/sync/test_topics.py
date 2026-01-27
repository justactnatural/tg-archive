import unittest
from unittest.mock import patch

try:
    import yaml  # noqa: F401
    import telethon  # noqa: F401
except Exception as e:  # pragma: no cover
    raise unittest.SkipTest("missing dependencies: {}".format(e))

import tgarchive.sync as syncmod
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

    def test_should_exclude_general_when_disabled(self):
        s = Sync.__new__(Sync)
        s.allowed_topic_ids = {1}
        s.include_general = False
        self.assertFalse(s._should_include_topic(None))

    def test_get_forum_topics_uses_peer_argument(self):
        s = Sync.__new__(Sync)
        def fake_client(req):
            self.assertIn("peer", req)
            self.assertNotIn("channel", req)
            return type(
                "Result",
                (),
                {"topics": [type("Topic", (), {"id": 1, "title": "Movies"})()]},
            )()

        s.client = fake_client

        with patch.object(syncmod.tl_functions.channels, "GetForumTopics", None, create=True), patch.object(
            syncmod.tl_functions.channels, "GetForumTopicsRequest", None, create=True
        ), patch.object(
            syncmod.tl_functions.messages,
            "GetForumTopicsRequest",
            lambda **kwargs: kwargs,
        ):
            topics = s._get_forum_topics(123)

        self.assertEqual(topics, [{"id": 1, "title": "Movies"}])


if __name__ == "__main__":
    unittest.main()
