# Draft JSON schemas

Phase A (the daily scheduled routine) writes these files. Phase B (human review + render)
reads them. Keeping the shape documented here means `render_video.py` and `fetch_weather.py`
never need to guess at what Claude wrote.

## News draft — `output/drafts/<date>_news_draft.json`

```json
{
  "date": "2026-09-22",
  "headlines": [
    {
      "en": "Sinner overcomes early break to reach Beijing quarterfinals",
      "hu": "Sinner egy korai brék ellenére is bejutott a pekingi negyeddöntőbe",
      "source_url": "https://www.atptour.com/en/news/..."
    }
  ],
  "background_file": "tennis_loop_01.mp4",
  "status": "pending",
  "instagram_caption": {
    "en": "🎾 TENNIS NEWS YOU MIGHT'VE MISSED TODAY 🎾\n\n...long, engaging caption with a hook, one paragraph per headline, a call-to-action, and a follow prompt...\n\n#Tennis #ATP #WTA #TennisNews",
    "hu": "🎾 EZEKET A TENISZHÍREKET VALÓSZÍNŰLEG LEMARADTAD MA 🎾\n\n...ugyanaz magyarul, nem szó szerinti fordítás, hanem természetes stílusban...\n\n#Tenisz #ATP #WTA #TeniszHirek"
  }
}
```

- `headlines`: 4-6 entries, ordered by importance. Both `en` and `hu` are required.
- `source_url`: optional but recommended, kept for the user's own reference (not shown on video).
- `background_file`: filename inside `assets/backgrounds/`; defaults to
  `config/settings.yaml -> video.default_background` if omitted.
- `status`: `"pending"` until the user approves in Phase B; scripts don't rely on this field,
  it's for human/Claude bookkeeping only.
- `instagram_caption`: written by Claude (not a script) alongside the headlines, one per
  language. Always long-form and algorithm-friendly: an attention-grabbing hook line, one
  short paragraph per headline (not just a bare repeat of the on-video bullet — add a little
  context or stakes), a comment/save call-to-action, a follow prompt, and 8-12 relevant
  hashtags at the end (mix of broad tennis tags and specific ones like player/event names).
  The Hungarian version is a natural rewrite for the audience, not a literal translation.
- Alongside the JSON, also write each caption as its own plain-text sibling file with real
  line breaks (not `\n` escapes), so it can be copy-pasted straight into Instagram:
  `output/drafts/<date>_instagram_caption_en.txt` and `..._hu.txt`. The JSON field is the
  source of truth for automation/history; the `.txt` files are for the human to copy from.
- `title_override` (optional): `{"en": "...", "hu": "..."}`. If present, `build_text_overlay.py`
  uses this instead of `config/settings.yaml -> text.title_text` for the on-video title.
  Used by the weekly recap draft (see below) to say "This week in tennis" instead of the
  daily title, while reusing this same schema and the same render/publish scripts unchanged.

## Weather draft — `output/drafts/<date>_weather_draft.json`

Written only when `fetch_weather.py` reports at least one anomaly. There is no video render
step for this feature — it's informational, for the user to decide whether/how to post.

```json
{
  "date": "2026-09-22",
  "anomalies": [
    {
      "tournament": "China Open",
      "city": "Beijing",
      "type": "extreme_heat",
      "severity": "moderate",
      "detail": "Forecast high 37°C, well above the 35°C threshold",
      "suggested_angle_en": "Extreme heat in Beijing could favor players with strong conditioning...",
      "suggested_angle_hu": "A pekingi extrém hőség azoknak a játékosoknak kedvezhet, akik jobb fizikai állapotban vannak..."
    }
  ]
}
```

- `type`: one of `heavy_rain`, `high_wind`, `extreme_heat`, `extreme_cold`.
- `severity`: free-text label (`mild` / `moderate` / `severe`) set by whoever writes the
  draft (Claude, based on how far past threshold the reading is).
- `suggested_angle_en` / `_hu`: short paragraph Claude drafts explaining the possible
  betting/performance impact — the user decides whether to turn it into a post.

## Quote draft — `output/drafts/<date>_quote_draft.json`

A standalone image post (no video) - one short, attributed tennis quote on a branded card.
Written only when a genuinely notable, recent (last few days), real quote is found - never
invent or paraphrase-as-verbatim a quote. Skip this file entirely on days with nothing
worth quoting rather than force one.

```json
{
  "date": "2026-09-22",
  "quote": {
    "en": "I am taking this time to reset and heal so when I return I am 100% ready to go.",
    "hu": "Ezt az időt arra használom, hogy helyreálljak és gyógyuljak, hogy amikor visszatérek, 100%-osan készen álljak."
  },
  "attribution": "Jack Draper",
  "context": {
    "en": "on ending his 2026 season",
    "hu": "a 2026-os szezonja lezárásáról"
  },
  "source_url": "https://www.atptour.com/en/news/draper-announcement-september-2026",
  "status": "pending"
}
```

- `quote`: keep it short (1-2 sentences) and verbatim in `en` as actually reported by a
  news source - never fabricated. `hu` is a faithful translation, not a rewrite.
- `attribution`: just the person's name, unchanged in both languages.
- `context`: a short phrase (not a full sentence) explaining the situation, in both
  languages.
- `source_url`: required - always cite where the quote was reported.
- Rendered via `scripts/build_quote_card.py` (a single PNG image, not a video) and posted
  as an image post via `scripts/publish_meta.py --lang <lang> --quote`.

## Poll draft — `output/drafts/<date>_poll_draft.json`

A daily Telegram poll about that day's most notable match. Written only when there's a
genuinely competitive/notable match to feature - skip entirely on a day without one rather
than force a poll on an obscure or lopsided pairing.

```json
{
  "date": "2026-09-24",
  "match": {
    "player_a": {"name": "Alexander Zverev", "short": "Zverev A.", "flag": "🇩🇪"},
    "player_b": {"name": "Carlos Alcaraz", "short": "Alcaraz C.", "flag": "🇪🇸"}
  },
  "tournament": "Laver Cup",
  "question": {"en": "Who wins today?", "hu": "Ki nyer ma?"},
  "status": "pending"
}
```

- Pick the match using ranking first (the two most notable/highest-ranked players playing
  that day), then among comparably notable candidates prefer the closest/most competitive
  one (similar rankings or current form) over a lopsided mismatch.
- `short`: `"LastName F."` format (surname, space, first-initial with a period).
- `flag`: the player's country flag emoji. Used as-is in both languages - only `question`
  is translated, the poll options (`short` + `flag`) are identical in EN and HU.
- Posted via `scripts/publish_poll.py`: a native interactive poll on both Telegram
  channels (`sendPoll`), plus a static (non-interactive - the Graph API has no support for
  poll stickers) companion image posted as an Instagram Story on both accounts via
  `scripts/build_poll_card.py`.

## On this day in tennis draft — `output/drafts/<date>_onthisday_draft.json`

A standalone Story image (not a video) with 1-3 genuinely notable tennis history facts for
today's calendar date. Optional exactly like the quote draft: skip entirely if nothing
real and notable turns up for the date - never invent an event.

```json
{
  "date": "2026-09-24",
  "facts": [
    {"en": "...", "hu": "...", "year": 2008, "source_url": "..."}
  ],
  "status": "pending"
}
```

- Check `data/onthisday_history.json` first (flat list of `{date_used, event_key}`) so the
  same fact isn't reused on the same calendar date in a future year.
- Each fact must cite a real `source_url` - same sourcing rule as the quote draft.
- Rendered via `scripts/build_onthisday_card.py` (reuses `build_text_overlay.py`'s
  `build_overlay()` treating `facts` like `headlines`, with `title_override` set to
  `{"en": "On this day in tennis", "hu": "Ezen a napon a teniszben"}`, composited onto a
  solid navy background - a Story image, not an ffmpeg video) and posted via
  `scripts/auto_publish_onthisday_story.py`.

## Weekly stats draft — `output/drafts/<date_range>_weekly_stats_draft.json`

A standalone Story image (not a video) showing that week's tipping performance. Unlike the
other drafts, this one is **not gathered automatically** - the user reports these numbers
directly in chat each week (Claude has no access to the actual tip results), and Claude
writes this file from what the user says.

```json
{
  "date_range": "2026.09.10-17",
  "record": "27/22",
  "profit_units": "+14.5",
  "hit_rate": "55%",
  "status": "pending"
}
```

- `date_range`: display string for the week covered, in whatever format the user gives it.
- `record`, `profit_units`, `hit_rate`: display strings, shown as-is (not recalculated).
- Rendered via `scripts/build_weekly_stats_card.py` (reuses `build_text_overlay.py`'s
  `build_overlay()`, treating each stat line as a `headlines` entry, with a
  `title_override` of `{"en": "Weekly Results", "hu": "Heti eredmény"}`) and posted via
  `scripts/publish_weekly_stats.py` as an Instagram Story on both accounts, plus a Facebook
  Story for HU. This is human-triggered each week (the user runs the publish script when
  ready) and not wired into any automatic schedule, since the input itself is manual.

## Tournaments cache — `data/tournaments_today.json`

Ephemeral, overwritten daily. Input to `fetch_weather.py`.

```json
{
  "date": "2026-09-22",
  "tournaments": [
    {
      "name": "China Open",
      "city": "Beijing",
      "country": "CN",
      "surface": "hard",
      "indoor": false
    }
  ]
}
```

Only entries with `"indoor": false` are checked for weather anomalies.
