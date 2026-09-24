"""Render the weekly tipping-performance Story image (no video) - reuses
build_text_overlay's box-stacking layout, treating each stat line as a `headlines` entry.

Usage:
    python scripts/build_weekly_stats_card.py --draft output/drafts/2026.09.10-17_weekly_stats_draft.json --lang en --out output/weekly_stats_cards/2026.09.10-17_en.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from utils import load_config, project_path, read_json
from build_text_overlay import build_overlay

TITLE_OVERRIDE = {
    "en": "Weekly Results",
    "hu": "Heti eredmény",
}


def build_weekly_stats_card(draft: dict, lang: str, config: dict) -> Image.Image:
    stat_lines = [
        {"en": draft["date_range"], "hu": draft["date_range"]},
        {"en": f"Record: {draft['record']}", "hu": f"Mérleg: {draft['record']}"},
        {"en": f"Profit: {draft['profit_units']} units", "hu": f"Profit: {draft['profit_units']} egység"},
        {"en": f"Hit rate: {draft['hit_rate']}", "hu": f"Találati arány: {draft['hit_rate']}"},
    ]

    adapted_draft = {"headlines": stat_lines, "title_override": TITLE_OVERRIDE}
    overlay = build_overlay(adapted_draft, lang, config)

    v = config["video"]
    bg_color = tuple(config["quote_card"]["background_color"])
    background = Image.new("RGBA", (v["width"], v["height"]), bg_color)
    background.alpha_composite(overlay)
    return background


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", required=True)
    parser.add_argument("--lang", required=True, choices=["en", "hu"])
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    config = load_config()
    draft_path = Path(args.draft)
    if not draft_path.is_absolute():
        draft_path = project_path(args.draft)
    draft = read_json(draft_path)
    if draft is None:
        raise SystemExit(f"Draft not found: {draft_path}")

    img = build_weekly_stats_card(draft, args.lang, config)

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = project_path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out_path)
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
