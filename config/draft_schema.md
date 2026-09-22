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
  "status": "pending"
}
```

- `headlines`: 4-6 entries, ordered by importance. Both `en` and `hu` are required.
- `source_url`: optional but recommended, kept for the user's own reference (not shown on video).
- `background_file`: filename inside `assets/backgrounds/`; defaults to
  `config/settings.yaml -> video.default_background` if omitted.
- `status`: `"pending"` until the user approves in Phase B; scripts don't rely on this field,
  it's for human/Claude bookkeeping only.

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
