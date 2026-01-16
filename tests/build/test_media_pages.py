import os
import tempfile
import unittest

try:
    import yaml  # noqa: F401
    import jinja2  # noqa: F401
    import feedgen  # noqa: F401
except Exception as e:  # pragma: no cover
    raise unittest.SkipTest("missing dependencies: {}".format(e))

from tgarchive.build import Build
from tgarchive.db import Message, Media, User


class DummyDB:
    def __init__(self, messages):
        self._messages = messages

    def get_media_messages(self):
        return self._messages


class BuildMediaPagesTests(unittest.TestCase):
    def test_hashtag_dedupes_messages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            user = User(id=1, username="u", first_name=None, last_name=None, tags=[], avatar=None)
            media = Media(id=10, type="photo", url="file.jpg", title="file.jpg", description=None, thumb=None)
            msg = Message(
                id=100,
                type="message",
                date=None,
                edit_date=None,
                content="#foo #foo",
                reply_to=None,
                user=user,
                media=media,
                topic_id=None,
                topic_title=None,
            )

            config = {
                "publish_dir": tmpdir,
                "media_pages_dir": "media-pages",
                "publish_media_hashtags": True,
                "media_dir": "media",
                "publish_rss_feed": False,
            }
            b = Build(config, DummyDB([msg]), symlink=False)
            b.page_ids = {100: "2020-01.html"}

            tmpl_path = os.path.join(tmpdir, "media_template.html")
            with open(tmpl_path, "w", encoding="utf8") as f:
                f.write("{% for m in messages %}{{ m.id }}\n{% endfor %}")
            b.load_media_template(tmpl_path)

            b._build_media_pages()

            tag_path = os.path.join(tmpdir, "media-pages", "tag-foo.html")
            with open(tag_path, "r", encoding="utf8") as f:
                content = f.read()

            self.assertEqual(content.count("100"), 1)

    def test_render_media_page_uses_template(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "publish_dir": tmpdir,
                "media_pages_dir": "media-pages",
                "publish_media_hashtags": True,
                "media_dir": "media",
            }
            b = Build(config, DummyDB([]), symlink=False)

            tmpl_path = os.path.join(tmpdir, "media_template.html")
            with open(tmpl_path, "w", encoding="utf8") as f:
                f.write("ok")
            b.load_media_template(tmpl_path)

            out_path = os.path.join(tmpdir, "media-pages", "index.html")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            b._render_media_page(
                out_path,
                view="index",
                title="Media",
                topics=[],
                hashtags=[],
                messages=[],
                root_prefix="../",
            )

            with open(out_path, "r", encoding="utf8") as f:
                self.assertEqual(f.read(), "ok")


if __name__ == "__main__":
    unittest.main()
