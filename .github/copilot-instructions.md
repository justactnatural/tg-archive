## Purpose

This file tells an AI coding agent how the project is organised and where to make safe, targeted edits. Keep guidance concise and code-focused — the goal is to get productive edits without guessing runtime secrets.

## High-level architecture

- Single-process CLI: sync (Telegram -> SQLite) and build (SQLite -> static site) are separate modes in the same binary entrypoint [tgarchive/__init__.py](tgarchive/__init__.py).
- Sync uses Telethon to fetch messages and stores normalized rows in the local SQLite DB (`tgarchive/db.py`). Build reads that DB and renders pages with Jinja (`tgarchive/build.py`).

## Key files (start here)

- [tgarchive/__init__.py](tgarchive/__init__.py) — CLI and configuration loading (`get_config`). Flags grouped into `new`, `sync`, and `build`.
- [tgarchive/sync.py](tgarchive/sync.py) — `Sync` class: `new_client()`, `sync()`, `_get_messages()`, `_get_media()` and `_download_media()` are the main touchpoints.
- [tgarchive/db.py](tgarchive/db.py) — `schema` (string) is the source-of-truth for table layout. `DB` exposes `get_last_message_id`, `get_messages`, `get_timeline`, `insert_user`, `insert_media`, `insert_message`.
- [tgarchive/build.py](tgarchive/build.py) — `Build` class: `load_template()`, `load_rss_template()`, `build()` and internal `_render_page()`.
- [tgarchive/example/](tgarchive/example/) — example `config.yaml`, `template.html`, `rss_template.html`, and `static/` used when `--new` is run.

## Project-specific conventions & patterns

- DB-first: change schema only by editing the `schema` variable in `tgarchive/db.py`. There are no automatic migrations — tests or CI won't run schema upgrades; update schema and recreate DB for dev testing.
- Lazy Telethon imports: heavy Telethon imports are intentionally delayed. See the `from .sync import Sync` inside the `--sync` branch of [tgarchive/__init__.py](tgarchive/__init__.py). Avoid importing Telethon at module import time.
- Media filenames: downloaded media are renamed to `<message_id>.<ext>` (see `_download_media()` in [tgarchive/sync.py](tgarchive/sync.py)). Avatars are `avatar_<user_id>.jpg`.
- Config defaults: default config values live in `_CONFIG` in [tgarchive/__init__.py](tgarchive/__init__.py); runtime config merges `config.yaml` over `_CONFIG` via `get_config()`.
- Build output: `Build._create_publish_dir()` clears and recreates `publish_dir`, copies `static_dir`, and copies/symlinks the `media_dir` when present. Use `--symlink` to create relative symlinks instead of copying.

## Developer workflows & concrete commands

- Quick dev run (no install):

  python -c "import tgarchive; tgarchive.main()" -- --help

- Recommended (editable install):

  pip install -e .
  tg-archive --help

- Typical tasks:

  - Initialize project skeleton: `tg-archive --new --path=mysite`
  - Sync messages: `tg-archive --sync --config=mysite/config.yaml --session=session.session --data=mysite/data.sqlite`
  - Build site: `tg-archive --build --config=mysite/config.yaml --data=mysite/data.sqlite`

## Where to make changes safely

- Add/change CLI flags: edit `main()` in [tgarchive/__init__.py](tgarchive/__init__.py). Argument groups: `new`, `sync`, `build`.
- Change DB schema or add fields: edit the `schema` string in [tgarchive/db.py](tgarchive/db.py). Update any read/writes that reference added columns. Recreate DB for testing.
- Media handling: change download logic or naming in `_get_media()` / `_download_media()` in [tgarchive/sync.py](tgarchive/sync.py).
- Template changes: edit `template.html` and `rss_template.html` under [tgarchive/example/](tgarchive/example/) and load them at build time via `--template` / `--rss-template`.

## Integration & dependencies

- Telethon (Telegram client) — heavy dependency; used only in sync mode. Tests or fast CLI invocations should avoid importing it.
- Jinja2 — templating used in build.
- PIL / Pillow — used for avatars.
- feedgen, python-magic — used by `build.py` for RSS and MIME detection.

## Testing & debugging notes

- No automated tests present. Validate changes locally by running the CLI with example config and a throwaway session.
- Increase logging by changing `logging.basicConfig` level in [tgarchive/__init__.py](tgarchive/__init__.py) to `DEBUG` to trace sync/build behavior.

## Small gotchas an agent should know

- `use_takeout` mode requires manual step confirmation on the Telegram account/device; the code calls `input()` while waiting (see `Sync.new_client`).
- `DB._make_message()` expects ISO-like timestamps; `DB` stores timestamps in the schema as `TIMESTAMP` strings.

---

If you'd like, I can: (a) add a short checklist for code reviews in this repo, (b) create a minimal dev-run script, or (c) add example unit-test scaffolding. Which would you prefer?
