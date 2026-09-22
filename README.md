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
The finished MP4s land in `output/videos/<date>/` for you to post manually to both
Telegram channels.

## Running pieces standalone (for testing)

```
python scripts/build_text_overlay.py --draft output/drafts/2026-09-22_news_draft.json --lang en --out output/videos/2026-09-22/overlay_en.png
python scripts/fetch_weather.py --cities-file data/tournaments_today.json
```
