
![favicon](https://user-images.githubusercontent.com/547147/111869334-eb48f100-89a4-11eb-9c0c-bc74cdee197a.png)


**tg-archive** is a tool for exporting Telegram group chats into static websites, preserving chat history like mailing list archives.

**IMPORTANT:** I'm no longer actively maintaining or developing this tool. Can review and merge PRs (as long as they're not massive and are clearly documented).

## Preview
The [@fossunited](https://tg.fossunited.org) Telegram group archive.

![image](https://user-images.githubusercontent.com/547147/111869398-44188980-89a5-11eb-936f-01d98276ba6a.png)


## How it works
tg-archive uses the [Telethon](https://github.com/LonamiWebs/Telethon) Telegram API client to periodically sync messages from a group to a local SQLite database (file), downloading only new messages since the last sync. It then generates a static archive website of messages to be published anywhere.

## Features
- Periodically sync Telegram group messages to a local DB.
- Download user avatars locally.
- Download and embed media (files, documents, photos).
- Renders poll results.
- Use emoji alternatives in place of stickers.
- Single file Jinja HTML template for generating the static site.
- Year / Month / Day indexes with deep linking across pages.
- "In reply to" on replies with links to parent messages across pages.
- RSS / Atom feed of recent messages.
- Optional media index pages grouped by forum topics and hashtags.

## Install
- Get [Telegram API credentials](https://my.telegram.org/auth?to=apps). Normal user account API and not the Bot API.
  - If this page produces an alert stating only "ERROR", disconnect from any proxy/vpn and try again in a different browser.

- Install with: `uv pip install tg-archive` (tested with Python 3.13.2).

- Optional: For media MIME detection in RSS, install `libmagic`:
  - macOS: `brew install libmagic`
  - Debian/Ubuntu: `apt-get install libmagic1`

### Usage

1. `tg-archive --new --path=mysite` (creates a new site. `cd` into mysite and edit `config.yaml`).
1. `tg-archive --sync` (syncs data into `data.sqlite`).
  Note: First time connection will prompt for your ph,pm. one number + a Telegram auth code sent to the app. On successful auth, a `session.session` file is created. DO NOT SHARE this session file publicly as it contains the API autorization for your account.
1. `tg-archive --build` (builds the static site into the `site` directory, which can be published)

### Customization
Edit the generated `template.html` and static assets in the `./static` directory to customize the site.

To enable the media index, set `publish_media_index: true` in `config.yaml` and provide
`media_template.html` alongside your main template (or pass `--media-template`).
Use `media_pages_dir` to control where the pages are written and `publish_media_hashtags`
to toggle hashtag pages.

To organize downloaded media into topic subfolders, enable `media_by_topic: true`.
To migrate existing media into those folders, set `migrate_media_by_topic: true` or run
`tg-archive --build --migrate-media`.

Example media config:
```yaml
publish_media_index: true
media_pages_dir: "media-pages"
publish_media_hashtags: true
media_by_topic: true
```

### Forum topics
Topic grouping uses Telegram forum topics (available on supergroups with topics enabled).
If your group does not have topics enabled, all media will fall under a single "general" topic.

### Topic filtering
To sync only specific forum topics, set either `topic_ids` or `topic_titles` in `config.yaml`.
Titles resolve to IDs at sync time. If multiple topics share a title, you will be prompted to
choose IDs (non-interactive runs should use IDs directly). Messages outside topics will be
included as "general" when `include_general: true`.

### Message filtering
To sync only specific messages, set `message_ids` in `config.yaml` or pass `--id`.
When present, only those message IDs are fetched.

### Author filtering
To sync only specific authors, set `author_ids` or `author_usernames` in `config.yaml`.
When present, only messages from those authors are fetched.

### Multi-group configs
For multiple groups, use the `defaults` + `groups` + `build` structure shown in
`config.example.yaml`. Each group syncs into its own DB and media directory, and the
build step combines them into a single site.
### Note
- The sync can be stopped (Ctrl+C) any time to be resumed later.
- Setup a cron job to periodically sync messages and re-publish the archive.
- Downloading large media files and long message history from large groups continuously may run into Telegram API's rate limits. Watch the debug output.

### TODO
- Add config validation for required keys (api_id, api_hash, group).
- Add unit tests for fork-specific changes (media indexing and migration).

Licensed under the MIT license.
