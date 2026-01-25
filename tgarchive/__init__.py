import argparse
import logging
import os
import shutil
import sys
import yaml

from .db import DB

from .__metadata__ import __version__

logging.basicConfig(format="%(asctime)s: %(message)s",
                    level=logging.INFO)

_CONFIG = {
    "api_id": os.getenv("API_ID", ""),
    "api_hash": os.getenv("API_HASH", ""),
    "group": "",
    "download_avatars": True,
    "avatar_size": [64, 64],
    "download_media": False,
    "media_dir": "media",
    "media_mime_types": [],
    "media_by_topic": False,
    "migrate_media_by_topic": False,
    "topic_ids": [],
    "topic_titles": [],
    "include_general": True,
    "message_ids": [],
    "author_ids": [],
    "author_usernames": [],
    "proxy": {
        "enable": False,
    },
    "fetch_batch_size": 2000,
    "fetch_wait": 5,
    "fetch_limit": 0,

    "publish_rss_feed": True,
    "rss_feed_entries": 100,

    "publish_dir": "site",
    "site_url": "https://mysite.com",
    "static_dir": "static",
    "telegram_url": "https://t.me/{id}",
    "per_page": 1000,
    "show_sender_fullname": False,
    "timezone": "",
    "site_name": "@{group} (Telegram) archive",
    "site_description": "Public archive of @{group} Telegram messages.",
    "meta_description": "@{group} {date} Telegram message archive.",
    "page_title": "{date} - @{group} Telegram message archive.",
    "publish_media_index": False,
    "media_pages_dir": "media-pages",
    "publish_media_hashtags": True
}

def _merge_dict(base, override):
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge_dict(out[k], v)
        else:
            out[k] = v
    return out


def _slugify(s):
    out = []
    for ch in s.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in ("-", "_"):
            out.append(ch)
        else:
            out.append("-")
    slug = "".join(out).strip("-")
    return slug or "group"


def _media_prefix(media_dir, media_root):
    if not media_dir:
        return ""
    if os.path.isabs(media_dir):
        return os.path.basename(media_dir)
    if not media_root:
        return media_dir
    try:
        rel = os.path.relpath(media_dir, media_root)
    except ValueError:
        return os.path.basename(media_dir)
    return rel if rel != "." else ""


def get_config(path):
    with open(path, "r") as f:
        raw = yaml.safe_load(f.read()) or {}

    if "groups" not in raw:
        merged = _merge_dict(_CONFIG, raw)
        if "media_dir" not in raw and merged.get("group"):
            merged["media_dir"] = os.path.join("media", _slugify(str(merged["group"])))
        if (merged.get("topic_ids") or merged.get("topic_titles")) and not merged.get("media_by_topic", False):
            merged["media_by_topic"] = True
        return merged

    defaults = raw.get("defaults", {})
    groups = []
    for g in raw.get("groups", []):
        merged = _merge_dict(_merge_dict(_CONFIG, defaults), g)
        if not merged.get("group"):
            raise ValueError("group is required for each entry in groups")
        if not merged.get("data"):
            merged["data"] = os.path.join("data", "{}.sqlite".format(_slugify(str(merged["group"]))))
        if not merged.get("media_dir"):
            merged["media_dir"] = os.path.join("media", _slugify(str(merged["group"])))
        if (merged.get("topic_ids") or merged.get("topic_titles")) and not merged.get("media_by_topic", False):
            merged["media_by_topic"] = True
        groups.append(merged)

    build_cfg = _merge_dict(_CONFIG, raw.get("build", {}))
    build_cfg["groups"] = groups
    if not build_cfg.get("group"):
        build_cfg["group"] = raw.get("group_label", "multiple")
    build_cfg["telegram_url"] = raw.get("telegram_url", build_cfg["telegram_url"])
    build_cfg["show_sender_fullname"] = raw.get("show_sender_fullname", build_cfg["show_sender_fullname"])
    build_cfg["timezone"] = raw.get("timezone", build_cfg["timezone"])
    return build_cfg


def main():
    """Run the CLI."""
    p = argparse.ArgumentParser(
        description="A tool for exporting and archiving Telegram groups to webpages.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    p.add_argument("-c", "--config", action="store", type=str, default="config.yaml",
                   dest="config", help="path to the config file")
    p.add_argument("-d", "--data", action="store", type=str, default="data.sqlite",
                   dest="data", help="path to the SQLite data file to store messages")
    p.add_argument("-se", "--session", action="store", type=str, default="session.session",
                   dest="session", help="path to the session file")
    p.add_argument("-v", "--version", action="store_true", dest="version", help="display version")

    n = p.add_argument_group("new")
    n.add_argument("-n", "--new", action="store_true",
                   dest="new", help="initialize a new site")
    n.add_argument("-p", "--path", action="store", type=str, default="example",
                   dest="path", help="path to create the site")

    s = p.add_argument_group("sync")
    s.add_argument("-s", "--sync", action="store_true",
                   dest="sync", help="sync data from telegram group to the local DB")
    s.add_argument("-id", "--id", action="store", type=int, nargs="+",
                   dest="id", help="sync (or update) messages for given ids")
    s.add_argument("-from-id", "--from-id", action="store", type=int,
                   dest="from_id", help="sync (or update) messages from this id to the latest")

    b = p.add_argument_group("build")
    b.add_argument("-b", "--build", action="store_true",
                   dest="build", help="build the static site")
    b.add_argument("-t", "--template", action="store", type=str, default="template.html",
                   dest="template", help="path to the template file")
    b.add_argument("--rss-template", action="store", type=str, default=None,
                   dest="rss_template", help="path to the rss template file")
    b.add_argument("--media-template", action="store", type=str, default="media_template.html",
                   dest="media_template", help="path to the media template file")
    b.add_argument("--migrate-media", action="store_true", dest="migrate_media",
                   help="move existing media into topic folders and update DB paths")
    b.add_argument("--symlink", action="store_true", dest="symlink",
                   help="symlink media and other static files instead of copying")

    args = p.parse_args(args=None if sys.argv[1:] else ['--help'])

    if args.version:
        print("v{}".format(__version__))
        sys.exit()

    # Setup new site.
    elif args.new:
        exdir = os.path.join(os.path.dirname(__file__), "example")
        if not os.path.isdir(exdir):
            logging.error("unable to find bundled example directory")
            sys.exit(1)

        try:
            shutil.copytree(exdir, args.path)
        except FileExistsError:
            logging.error(
                "the directory '{}' already exists".format(args.path))
            sys.exit(1)
        except:
            raise

        logging.info("created directory '{}'".format(args.path))
        
        # make sure the files are writable
        os.chmod(args.path, 0o755)
        for root, dirs, files in os.walk(args.path):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o755)
            for f in files:
                os.chmod(os.path.join(root, f), 0o644)

    # Sync from Telegram.
    elif args.sync:
        # Import because the Telegram client import is quite heavy.
        from .sync import Sync

        # Ensure an asyncio event loop exists (fixes RuntimeError on Python 3.11+)
        import asyncio
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())

        if args.id and args.from_id and args.from_id > 0:
            logging.error("pass either --id or --from-id but not both")
            sys.exit(1)

        cfg = get_config(args.config)

        def run_sync(group_cfg):
            mode = "takeout" if group_cfg.get("use_takeout", False) else "standard"
            logging.info("starting Telegram sync (group={}, batch_size={}, limit={}, wait={}, mode={})".format(
                group_cfg.get("group"),
                group_cfg["fetch_batch_size"],
                group_cfg["fetch_limit"],
                group_cfg["fetch_wait"],
                mode
            ))
            s = Sync(group_cfg, args.session, DB(group_cfg.get("data", args.data)))
            msg_ids = group_cfg.get("message_ids") or args.id
            try:
                s.sync(msg_ids, args.from_id)
            except KeyboardInterrupt:
                if group_cfg.get("use_takeout", False):
                    s.finish_takeout()
                raise

        try:
            if cfg.get("groups"):
                for g in cfg["groups"]:
                    run_sync(g)
            else:
                run_sync(cfg)
        except KeyboardInterrupt as e:
            logging.info("sync cancelled manually")
            sys.exit()
        except:
            raise

    # Build static site.
    elif args.build:
        from .build import Build
        from .db import MultiDB

        logging.info("building site")
        config = get_config(args.config)
        if args.migrate_media:
            config["migrate_media_by_topic"] = True
            config["media_by_topic"] = True

        if config.get("groups"):
            groups = []
            for g in config["groups"]:
                db = DB(g["data"], g.get("timezone", config.get("timezone")))
                groups.append({
                    "db": db,
                    "key": _slugify(str(g["group"])),
                    "label": g.get("name") or str(g.get("group")),
                    "media_dir": g["media_dir"],
                    "media_prefix": _media_prefix(g["media_dir"], config.get("media_dir", "media")),
                })
            config["media_dirs"] = [g["media_dir"] for g in config["groups"]]
            b = Build(config, MultiDB(groups, config.get("timezone")), args.symlink)
        else:
            b = Build(config, DB(args.data, config["timezone"]), args.symlink)
        b.load_template(args.template)
        if args.rss_template:
            b.load_rss_template(args.rss_template)
        if config.get("publish_media_index", False):
            b.load_media_template(args.media_template)
        b.build()

        logging.info("published to directory '{}'".format(config["publish_dir"]))
