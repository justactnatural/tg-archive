# tg-archive Workflow (Sync + Build)

This is a minimal zsh workflow to sync the database and build the static site.

## One-time setup (optional)
```zsh
cd /Users/nathanmalitz/Code/tele-rippz/tg-archive
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

## Run tests
```zsh
cd /Users/nathanmalitz/Code/tele-rippz/tg-archive
source .venv/bin/activate
python3 -m unittest discover -s tests
```

## Set API credentials (recommended)
```zsh
cd /Users/nathanmalitz/Code/tele-rippz/tg-archive
if [ ! -f .env ]; then
  cat <<'EOF' > .env
API_ID=
API_HASH=
DATA_PATH=/Volumes/HD1/tg-archive/data.sqlite
EOF
fi
set -a
source .env
set +a
```

## Sync the database
```zsh
cd /Users/nathanmalitz/Code/tele-rippz/tg-archive
python3 -m tgarchive --sync \
  --config /Users/nathanmalitz/Code/tele-rippz/tg-archive/tgarchive/example/config.yaml \
  --session /Users/nathanmalitz/Code/tele-rippz/tg-archive/session.session \
  --data /Volumes/HD1/tg-archive/data.sqlite
```

## Build the static site (with media migration)
```zsh
cd /Users/nathanmalitz/Code/tele-rippz/tg-archive
python3 -m tgarchive --build \
  --config /Users/nathanmalitz/Code/tele-rippz/tg-archive/tgarchive/example/config.yaml \
  --data /Volumes/HD1/tg-archive/data.sqlite \
  --template /Users/nathanmalitz/Code/tele-rippz/tg-archive/tgarchive/example/template.html \
  --media-template /Users/nathanmalitz/Code/tele-rippz/tg-archive/tgarchive/example/media_template.html \
  --migrate-media
```
Note: both `--template` and `--media-template` are required.

## Build without migration (routine rebuilds)
```zsh
cd /Users/nathanmalitz/Code/tele-rippz/tg-archive
python3 -m tgarchive --build \
  --config /Users/nathanmalitz/Code/tele-rippz/tg-archive/tgarchive/example/config.yaml \
  --data /Volumes/HD1/tg-archive/data.sqlite \
  --template /Users/nathanmalitz/Code/tele-rippz/tg-archive/tgarchive/example/template.html \
  --media-template /Users/nathanmalitz/Code/tele-rippz/tg-archive/tgarchive/example/media_template.html
```

## Shut down the local site preview
If you started a local server (for example, `python3 -m http.server`), stop it with:
```zsh
Ctrl+C
```

## Run tests
```zsh
cd /Users/nathanmalitz/Code/tele-rippz/tg-archive
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests
```
