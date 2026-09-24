"""Render the "On this day in tennis" Story image (no video) - reuses build_text_overlay's
box-stacking layout by adapting the onthisday draft's `facts` list into the shape
build_overlay() already expects (`headlines`), then compositing the transparent overlay
onto a solid navy background instead of a video clip.

Usage:
    python scripts/build_onthisday_card.py --draft output/drafts/2026-09-24_onthisday_draft.json --lang en --out output/onthisday_cards/2026-09-24_onthisday_en.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from utils import load_config, project_path, read_json
from build_text_overlay import build_overlay

TITLE_OVERRIDE = {
    "en": "On this day in tennis",
    "hu": "Ezen a napon a teniszben",
}


def build_onthisday_card(draft: dict, lang: str, config: dict) -> Image.Image:
    # Adapt {facts: [{en, hu, year, source_url}]} into the {headlines: [{en, hu}]} shape
    # build_overlay() already knows how to render, prefixed with the year for context.
    adapted_headlines = []
    for fact in draft.get("facts", []):
        year = fact.get("year", "")
        adapted_headlines.append({
            "en": f"{year}: {fact['en']}" if year else fact["en"],
            "hu": f"{year}: {fact['hu']}" if year else fact["hu"],
        })
    adapted_draft = {"headlines": adapted_headlines, "title_override": TITLE_OVERRIDE}

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

    img = build_onthisday_card(draft, args.lang, config)

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = project_path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out_path)
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
