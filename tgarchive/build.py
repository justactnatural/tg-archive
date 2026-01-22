from collections import OrderedDict, deque
import logging
import math
import os
import re
import shutil
import warnings

try:
    import magic
except Exception:  # pragma: no cover - optional native dependency
    magic = None
    warnings.warn("libmagic not found; media MIME detection will be skipped", RuntimeWarning)

from importlib import metadata

from feedgen.feed import FeedGenerator
from jinja2 import Template

from .db import User, Message


_NL2BR = re.compile(r"\n\n+")


class Build:
    config = {}
    template = None
    media_template = None
    db = None

    def __init__(self, config, db, symlink):
        self.config = config
        self.db = db
        self.symlink = symlink

        self.rss_template: Template = None
        self.media_template: Template = None

        # Map of all message IDs across all months and the slug of the page
        # in which they occur (paginated), used to link replies to their
        # parent messages that may be on arbitrary pages.
        self.page_ids = {}
        self.timeline = OrderedDict()

    def build(self):
        if self.config.get("publish_rss_feed"):
            logging.info("rss media mime detection: {}".format("enabled" if magic else "disabled"))

        if self.config.get("migrate_media_by_topic", False):
            self._migrate_media_by_topic()

        # (Re)create the output directory.
        self._create_publish_dir()

        timeline = list(self.db.get_timeline())
        if len(timeline) == 0:
            logging.info("no data found to publish site")
            quit()

        for month in timeline:
            if month.date.year not in self.timeline:
                self.timeline[month.date.year] = []
            self.timeline[month.date.year].append(month)

        # Queue to store the latest N items to publish in the RSS feed.
        rss_entries = deque([], self.config["rss_feed_entries"])
        fname = None
        for month in timeline:
            # Get the days + message counts for the month.
            dayline = OrderedDict()
            for d in self.db.get_dayline(month.date.year, month.date.month, self.config["per_page"]):
                dayline[d.slug] = d

            # Paginate and fetch messages for the month until the end..
            total = self.db.get_message_count(
                month.date.year, month.date.month)
            total_pages = math.ceil(total / self.config["per_page"])

            for page in range(1, total_pages + 1):
                offset = (page - 1) * self.config["per_page"]
                messages = list(self.db.get_messages_page(month.date.year, month.date.month,
                                                         offset, self.config["per_page"]))

                if len(messages) == 0:
                    continue
                fname = self.make_filename(month, page)

                # Collect the message ID -> page name for all messages in the set
                # to link to replies in arbitrary positions across months, paginated pages.
                for m in messages:
                    self.page_ids[m.id] = fname

                if self.config["publish_rss_feed"]:
                    rss_entries.extend(messages)

                self._render_page(messages, month, dayline,
                                  fname, page, total_pages)

        # The last page chronologically is the latest page. Make it index.
        if fname:
            if self.symlink:
                os.symlink(fname, os.path.join(self.config["publish_dir"], "index.html"))
            else:
                shutil.copy(os.path.join(self.config["publish_dir"], fname),
                            os.path.join(self.config["publish_dir"], "index.html"))

        # Generate RSS feeds.
        if self.config["publish_rss_feed"]:
            self._build_rss(rss_entries, "index.rss", "index.atom")

        if self.config.get("publish_media_index", False):
            self._build_media_pages()

    def load_template(self, fname):
        with open(fname, "r") as f:
            self.template = Template(f.read(), autoescape=True)

    def load_rss_template(self, fname):
        with open(fname, "r") as f:
            self.rss_template = Template(f.read(), autoescape=True)

    def load_media_template(self, fname):
        with open(fname, "r") as f:
            self.media_template = Template(f.read(), autoescape=True)

    def make_filename(self, month, page) -> str:
        fname = "{}{}.html".format(
            month.slug, "_" + str(page) if page > 1 else "")
        return fname

    def _render_page(self, messages, month, dayline, fname, page, total_pages):
        html = self.template.render(config=self.config,
                                    timeline=self.timeline,
                                    dayline=dayline,
                                    month=month,
                                    messages=messages,
                                    page_ids=self.page_ids,
                                    pagination={"current": page,
                                                "total": total_pages},
                                    make_filename=self.make_filename,
                                    nl2br=self._nl2br)

        with open(os.path.join(self.config["publish_dir"], fname), "w", encoding="utf8") as f:
            f.write(html)

    def _build_rss(self, messages, rss_file, atom_file):
        f = FeedGenerator()
        f.id(self.config["site_url"])
        try:
            version = metadata.version("tg-archive")
        except metadata.PackageNotFoundError:
            version = "unknown"
        f.generator("tg-archive {}".format(version))
        f.link(href=self.config["site_url"], rel="alternate")
        f.title(self.config["site_name"].format(group=self.config["group"]))
        f.subtitle(self.config["site_description"])

        for m in messages:
            url = "{}/{}#{}".format(self.config["site_url"],
                                    self.page_ids[m.id], m.id)
            e = f.add_entry()
            e.id(url)
            e.title("@{} on {} (#{})".format(m.user.username, m.date, m.id))
            e.link({"href": url})
            e.published(m.date)

            media_mime = ""
            if m.media and m.media.url:
                media_root = self.config["media_dir"]
                if os.path.isabs(media_root):
                    media_root = os.path.basename(media_root)
                murl = "{}/{}/{}".format(self.config["site_url"], media_root, m.media.url)
                media_path = "{}/{}".format(self.config["media_dir"], m.media.url)
                media_mime = "application/octet-stream"
                media_size = 0

                if "://" in media_path:
                    media_mime = "text/html"
                else:
                    try:
                        media_size = str(os.path.getsize(media_path))
                        if magic:
                            try:
                                media_mime = magic.from_file(media_path, mime=True)
                            except:
                                pass
                    except FileNotFoundError:
                        pass

                e.enclosure(murl, media_size, media_mime)
            e.content(self._make_abstract(m, media_mime), type="html")

        f.rss_file(os.path.join(self.config["publish_dir"], "index.xml"), pretty=True)
        f.atom_file(os.path.join(self.config["publish_dir"], "index.atom"), pretty=True)

    def _make_abstract(self, m, media_mime):
        if self.rss_template:
            return self.rss_template.render(config=self.config,
                                            m=m,
                                            media_mime=media_mime,
                                            page_ids=self.page_ids,
                                            nl2br=self._nl2br)
        out = m.content
        if not out and m.media:
            out = m.media.title
        return out if out else ""

    def _nl2br(self, s) -> str:
        # There has to be a \n before <br> so as to not break
        # Jinja's automatic hyperlinking of URLs.
        return _NL2BR.sub("\n\n", s).replace("\n", "\n<br />")

    def _build_media_pages(self):
        if not self.media_template:
            logging.warning("media_template not loaded; skipping media index")
            return

        media_pages_dir = self.config.get("media_pages_dir", "media-pages")
        if self._is_unsafe_path(media_pages_dir):
            raise ValueError("media_pages_dir must be a relative path inside publish_dir")
        media_pages_path = os.path.join(self.config["publish_dir"], media_pages_dir)
        os.makedirs(media_pages_path, exist_ok=True)
        root_prefix = "../" * self._dir_depth(media_pages_dir)

        media_messages = []
        for m in self.db.get_media_messages():
            if not m.media or not m.media.url:
                continue
            if "://" in m.media.url:
                continue
            media_messages.append(m)

        topics = OrderedDict()
        hashtags = OrderedDict()

        for m in media_messages:
            topic_id = m.topic_id if m.topic_id else 0
            topic_title = m.topic_title if m.topic_title else (
                "General" if topic_id == 0 else "Topic {}".format(topic_id)
            )
            if topic_id not in topics:
                topics[topic_id] = {
                    "id": topic_id,
                    "title": topic_title,
                    "messages": []
                }
            topics[topic_id]["messages"].append(m)

            seen = set()
            for tag in self._extract_hashtags(m.content):
                if tag in seen:
                    continue
                seen.add(tag)
                if tag not in hashtags:
                    hashtags[tag] = []
                hashtags[tag].append(m)

        topic_list = [
            {"id": t["id"], "title": t["title"], "count": len(t["messages"])}
            for t in topics.values()
        ]
        hashtag_list = [
            {"tag": tag, "slug": self._slugify_hashtag(tag), "count": len(msgs)}
            for tag, msgs in hashtags.items()
        ]
        hashtag_list = [h for h in hashtag_list if h["slug"]]

        self._render_media_page(
            os.path.join(media_pages_path, "index.html"),
            view="index",
            title="Media",
            topics=topic_list,
            hashtags=hashtag_list,
            messages=[],
            root_prefix=root_prefix,
        )

        for t in topics.values():
            self._render_media_page(
                os.path.join(media_pages_path, "topic-{}.html".format(t["id"])),
                view="topic",
                title=t["title"],
                topics=topic_list,
                hashtags=hashtag_list,
                messages=t["messages"],
                root_prefix=root_prefix,
            )

        if self.config.get("publish_media_hashtags", True):
            for tag, msgs in hashtags.items():
                slug = self._slugify_hashtag(tag)
                if not slug:
                    continue
                self._render_media_page(
                    os.path.join(media_pages_path, "tag-{}.html".format(slug)),
                    view="hashtag",
                    title=tag,
                    topics=topic_list,
                    hashtags=hashtag_list,
                    messages=msgs,
                    root_prefix=root_prefix,
                )

    def _render_media_page(self, path, view, title, topics, hashtags, messages, root_prefix):
        media_pages_dir = self.config.get("media_pages_dir", "media-pages")
        html = self.media_template.render(
            config=self.config,
            view=view,
            title=title,
            topics=topics,
            hashtags=hashtags,
            messages=messages,
            page_ids=self.page_ids,
            timeline=self.timeline,
            media_pages_dir=media_pages_dir,
            root_prefix=root_prefix,
        )
        with open(path, "w", encoding="utf8") as f:
            f.write(html)

    def _extract_hashtags(self, text):
        if not text:
            return []
        return [t.lower() for t in re.findall(r"#[0-9A-Za-z_]+", text)]

    def _slugify_hashtag(self, tag):
        if not tag:
            return ""
        return re.sub(r"[^0-9A-Za-z_-]+", "", tag.lstrip("#").lower())

    def _dir_depth(self, path):
        norm = os.path.normpath(path)
        parts = [p for p in re.split(r"[\\\\/]+", norm) if p and p != "."]
        depth = 0
        for part in parts:
            if part == "..":
                depth = max(0, depth - 1)
            else:
                depth += 1
        return depth

    def _is_unsafe_path(self, path):
        if os.path.isabs(path):
            return True
        norm = os.path.normpath(path)
        return norm == ".." or norm.startswith("..{}".format(os.sep))

    def _migrate_media_by_topic(self):
        if not self.config.get("media_by_topic", False):
            logging.warning("media_by_topic is disabled; skipping migration")
            return

        media_dir = self.config["media_dir"]
        moved = 0
        for m in self.db.get_media_messages():
            if not m.media or not m.media.url:
                continue
            if "://" in m.media.url:
                continue

            topic_dir = self._topic_dir(m.topic_id, m.topic_title)
            if not topic_dir:
                continue

            basename = os.path.basename(m.media.url)
            new_rel = "{}/{}".format(topic_dir, basename)
            new_path = os.path.join(media_dir, new_rel)

            old_path = os.path.join(media_dir, m.media.url)
            if not os.path.exists(old_path) and os.path.exists(new_path):
                self.db.update_media_paths(m.media.id, new_rel, self._migrate_thumb(m.media.thumb, topic_dir))
                moved += 1
                continue
            if not os.path.exists(old_path):
                logging.warning("media file missing: {}".format(old_path))
                continue

            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            shutil.move(old_path, new_path)

            new_thumb = self._migrate_thumb(m.media.thumb, topic_dir)
            self.db.update_media_paths(m.media.id, new_rel, new_thumb)
            moved += 1

        if moved > 0:
            self.db.commit()
        logging.info("media migration complete: {} file(s) updated".format(moved))

    def _migrate_thumb(self, thumb, topic_dir):
        if not thumb:
            return None
        if "://" in thumb:
            return thumb

        media_dir = self.config["media_dir"]
        basename = os.path.basename(thumb)
        new_rel = "{}/{}".format(topic_dir, basename)
        new_path = os.path.join(media_dir, new_rel)
        old_path = os.path.join(media_dir, thumb)

        if os.path.exists(new_path):
            return new_rel
        if not os.path.exists(old_path):
            logging.warning("thumbnail missing: {}".format(old_path))
            return new_rel

        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        shutil.move(old_path, new_path)
        return new_rel

    def _topic_dir(self, topic_id, topic_title):
        if topic_id:
            return "topic-{}".format(topic_id)
        if topic_title:
            return self._slugify(topic_title, None)
        return "general"

    def _slugify(self, text, topic_id=None):
        slug = re.sub(r"[^0-9A-Za-z]+", "-", text.strip().lower())
        slug = slug.strip("-")
        if slug:
            return slug
        if topic_id:
            return "topic-{}".format(topic_id)
        return "topic"

    def _create_publish_dir(self):
        pubdir = self.config["publish_dir"]

        # Clear the output directory.
        if os.path.exists(pubdir):
            shutil.rmtree(pubdir)

        # Re-create the output directory.
        os.mkdir(pubdir)

        # Copy the static directory into the output directory.
        for f in [self.config["static_dir"]]:
            target = os.path.join(pubdir, f)
            if self.symlink:
                self._relative_symlink(os.path.abspath(f), target)
            elif os.path.isfile(f):
                shutil.copyfile(f, target)
            else:
                shutil.copytree(f, target)

        # If media downloading is enabled, copy/symlink the media directory.
        mediadirs = self.config.get("media_dirs")
        if mediadirs:
            for mediadir in mediadirs:
                target = mediadir
                if os.path.isabs(mediadir):
                    target = os.path.basename(mediadir)
                target = os.path.join(pubdir, target)
                if os.path.exists(mediadir):
                    if self.symlink:
                        self._relative_symlink(os.path.abspath(mediadir), target)
                    else:
                        shutil.copytree(mediadir, target)
        else:
            mediadir = self.config["media_dir"]
            if os.path.exists(mediadir):
                if self.symlink:
                    self._relative_symlink(os.path.abspath(mediadir), os.path.join(
                        pubdir, os.path.basename(mediadir)))
                else:
                    shutil.copytree(mediadir, os.path.join(
                        pubdir, os.path.basename(mediadir)))

    def _relative_symlink(self, src, dst):
        dir_path = os.path.dirname(dst)
        src = os.path.relpath(src, dir_path)
        dst = os.path.join(dir_path, os.path.basename(src))
        return os.symlink(src, dst)
