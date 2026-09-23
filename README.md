# Content Generator — Tennis Telegram Social Automation

Semi-automated content pipeline for two tennis-tips Telegram channels (EN + HU).

## Features

1. **Daily tennis news reel** — "Probably you missed these tennis news today". A fixed
   background video loop with today's top headlines burned in as white text, rendered in
   both English and Hungarian.
2. **Tournament weather-anomaly watch** — flags rain/heat/wind/cold anomalies at today's
   outdoor ATP/WTA tournament cities, with a suggested post angle.

Both features are human-in-the-loop: Claude gathers and drafts, you review and approve
before anything renders, and posting to Telegram stays manual.

See `config/draft_schema.md` for the JSON shapes Claude writes and the scripts read, and
the plan file this project was built from for full architecture rationale.

## One-time setup

1. Install [ffmpeg](https://www.gyan.dev/ffmpeg/builds/) and confirm it's on PATH:
   ```
   winget install --id=Gyan.FFmpeg -e
   ffmpeg -version
   ```
2. Install Python 3.11+, then create a venv and install dependencies:
   ```
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
3. Get a free API key at [openweathermap.org/api](https://openweathermap.org/api)
   (Current Weather + 5 day / 3 hour Forecast are enough). Copy `.env.example` to `.env`
   and paste the key in as `OPENWEATHERMAP_API_KEY`.
4. Add 3-5 royalty-free vertical (9:16) tennis loop clips (15-30s each) to
   `assets/backgrounds/`. Set the default one in `config/settings.yaml` under
   `video.default_background`.
5. Download a bold Google Font `.ttf` (e.g. Montserrat ExtraBold or Poppins Bold — good
   Hungarian diacritic coverage) into `assets/fonts/` and update `config/settings.yaml`
   `text.font_file` if the filename differs.
6. `git init` and make your first commit.

## Instagram/Facebook publishing setup

Both languages publish via a Facebook Page's linked Instagram Business Account, using the
Meta Graph API. Do this once per language (EN and HU each need their own Page + app, or can
share one Meta app with two Pages):

1. Make sure the Instagram account is a **Business or Creator account**, and that it's
   linked to a Facebook Page (Page → Settings → Linked Accounts → Instagram). If you don't
   have a Page yet, create one at [facebook.com/pages/create](https://www.facebook.com/pages/create)
   with the *same* Facebook account you'll use for developer access below, to avoid
   cross-account permission headaches.
2. Register as a developer and create a Business-type app at
   [developers.facebook.com/apps](https://developers.facebook.com/apps/).
3. In the app dashboard, add the **Instagram** product (Add Product → Instagram → Set up).
4. In [Graph API Explorer](https://developers.facebook.com/tools/explorer/), select your
   app, click **Permissions**, and check: `pages_show_list`, `pages_read_engagement`,
   `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`,
   `business_management`. Generate an access token.
5. Call `GET /me/accounts` with that token to get the Page ID + a Page Access Token.
6. Call `GET /{page-id}?fields=instagram_business_account` with the Page Access Token to get
   the Instagram Business Account ID.
7. Save all three per language into `.env` as `META_<LANG>_PAGE_ID`,
   `META_<LANG>_IG_BUSINESS_ACCOUNT_ID`, `META_<LANG>_PAGE_ACCESS_TOKEN` (see
   `.env.example`). Page Access Tokens obtained this way are long-lived (~60 days) but do
   eventually expire and need regenerating.
8. Clone the public media-hosting repo as a sibling folder next to this project (see
   `config/settings.yaml -> publishing.media_repo_path`):
   ```
   git clone <your contentmedia repo url> ../contentmedia
   ```
   This repo only ever holds videos that are moments away from being posted publicly - the
   Graph API needs a public HTTPS URL to fetch the video from, it can't accept a direct
   upload. `scripts/publish_meta.py` pushes to it automatically.
9. (Optional but recommended) Create a Telegram bot via **@BotFather** (`/newbot`), add it
   as admin to both Telegram channels, send a test message in each, then check
   `https://api.telegram.org/bot<token>/getUpdates` to find each channel's chat ID. Save as
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_EN_CHAT_ID`, `TELEGRAM_HU_CHAT_ID` in `.env`. Once set,
   `publish_meta.py` automatically posts an announcement with the new post's link to the
   matching Telegram channel right after a successful publish.

## Daily workflow

**Phase A (gather — automatic, once a day via a scheduled routine):**
Claude searches for today's top tennis headlines and today's outdoor tournament cities,
runs `scripts/fetch_weather.py` against them, translates headlines to Hungarian, and writes
draft JSON files to `output/drafts/`. You get a notification that a digest is ready.

**Phase B (review + render — you, whenever you're ready):**
Open a chat with Claude, review the draft(s), edit/approve, then Claude runs:
```
python scripts/render_video.py --draft output/drafts/2026-09-22_news_draft.json --lang en
python scripts/render_video.py --draft output/drafts/2026-09-22_news_draft.json --lang hu
```
The finished MP4s land in `output/videos/<date>/`, alongside the Instagram captions (in
the draft JSON and as `output/drafts/<date>_instagram_caption_<lang>.txt`), for manual
posting to both Telegram channels.

**Phase C (publish to Instagram/Facebook — only when you explicitly say so):**
```
python scripts/publish_meta.py --draft output/drafts/2026-09-22_news_draft.json --lang en
python scripts/publish_meta.py --draft output/drafts/2026-09-22_news_draft.json --lang hu
```
This actually posts the Reel (plus an Instagram Story, and for HU a Facebook Page video
post — see `config/settings.yaml -> publishing.facebook_post_languages` /
`story_languages`) — there's no further confirmation step inside the script, so only run
it once you've approved that specific day's video and caption. Add `--dry-run` to create
the Reel's media container without publishing anything, useful for testing. If
`TELEGRAM_BOT_TOKEN` and the chat IDs are set, it also announces the new post(s) with their
links in the matching Telegram channel.

## Running pieces standalone (for testing)

```
python scripts/build_text_overlay.py --draft output/drafts/2026-09-22_news_draft.json --lang en --out output/videos/2026-09-22/overlay_en.png
python scripts/fetch_weather.py --cities-file data/tournaments_today.json
```
