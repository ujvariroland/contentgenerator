"""Render a standalone quote-card image (no video) - one attributed tennis quote on a
branded background. Meant to be posted as a plain Instagram/Facebook image post.

Usage:
    python scripts/build_quote_card.py --quote "I am taking this time to reset and heal." \\
        --attribution "Jack Draper" --context "on ending his 2026 season" \\
        --out output/quote_cards/2026-09-23_draper_en.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from utils import load_config, project_path


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def build_quote_card(quote: str, attribution: str, context: str | None, config: dict) -> Image.Image:
    c = config["quote_card"]
    font_path = project_path(config["text"]["font_dir"], config["text"]["font_file"])

    width, height = c["width"], c["height"]
    img = Image.new("RGBA", (width, height), tuple(c["background_color"]))
    draw = ImageDraw.Draw(img)

    mark_font_size = 220
    mark_font = ImageFont.truetype(str(font_path), mark_font_size)
    quote_font = ImageFont.truetype(str(font_path), c["quote_font_size"])
    attribution_font = ImageFont.truetype(str(font_path), c["attribution_font_size"])

    max_width = c["max_text_width_px"]
    quote_line_height = int(c["quote_font_size"] * c["line_height_multiplier"])
    attribution_line_height = int(c["attribution_font_size"] * c["line_height_multiplier"])

    quote_lines = _wrap_text(draw, f"“{quote}”", quote_font, max_width)
    attribution_text = attribution if not context else f"{attribution} — {context}"
    attribution_lines = _wrap_text(draw, attribution_text, attribution_font, max_width)

    quote_block_height = len(quote_lines) * quote_line_height
    attribution_block_height = len(attribution_lines) * attribution_line_height
    mark_block_height = int(mark_font_size * 0.75)
    gap_mark_to_quote = 30
    gap_quote_to_attribution = 45

    total_height = mark_block_height + gap_mark_to_quote + quote_block_height + gap_quote_to_attribution + attribution_block_height

    safe_top = c.get("safe_top_px", 0)
    safe_bottom = c.get("safe_bottom_px", height)
    x = c["margin_x_px"]
    y = safe_top + max(0, (safe_bottom - safe_top - total_height) // 2)

    draw.text((x - 15, y - int(mark_font_size * 0.28)), "“", font=mark_font, fill=tuple(c["mark_color"]))
    y += mark_block_height + gap_mark_to_quote

    for line in quote_lines:
        draw.text((x, y), line, font=quote_font, fill=tuple(c["quote_color"]))
        y += quote_line_height

    y += gap_quote_to_attribution
    for line in attribution_lines:
        draw.text((x, y), line, font=attribution_font, fill=tuple(c["attribution_color"]))
        y += attribution_line_height

    return img


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quote", required=True)
    parser.add_argument("--attribution", required=True, help="Who said it, e.g. 'Jack Draper'")
    parser.add_argument("--context", default=None, help="Optional context, e.g. 'on ending his 2026 season'")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    config = load_config()
    img = build_quote_card(args.quote, args.attribution, args.context, config)

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = project_path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out_path)
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
