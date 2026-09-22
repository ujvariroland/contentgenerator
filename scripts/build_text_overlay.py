"""Render a transparent PNG text overlay (title + headlines) for the news reel.

Usage:
    python scripts/build_text_overlay.py --draft output/drafts/2026-09-22_news_draft.json --lang en --out output/videos/2026-09-22/overlay_en.png

Can also be imported and called as build_overlay(...) from render_video.py.
"""

from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from utils import load_config, project_path, read_json


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Word-wrap text to fit max_width, using actual glyph measurement (Pillow textlength)."""
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


def build_overlay(draft: dict, lang: str, config: dict) -> Image.Image:
    v = config["video"]
    t = config["text"]

    width, height = v["width"], v["height"]
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_path = project_path(t["font_dir"], t["font_file"])
    headline_font = ImageFont.truetype(str(font_path), t["headline_font_size"])
    title_font = ImageFont.truetype(str(font_path), t["title_font_size"])

    max_width = t["max_text_width_px"]
    line_height = int(t["headline_font_size"] * t["line_height_multiplier"])
    title_line_height = int(t["title_font_size"] * t["line_height_multiplier"])

    fill = tuple(t["fill_color"])
    stroke_fill = tuple(t["stroke_color"])
    stroke_width = t["stroke_width"]
    scrim_color = tuple(t["scrim_color"])
    scrim_padding = t["scrim_padding_px"]

    x = t["margin_left_px"]
    max_text_width = width - t["margin_left_px"] - t["margin_right_px"]
    max_text_width = min(max_text_width, max_width)

    # Build the full block of lines first (title + headlines) so we can size the scrim.
    title_text = t["title_text"].get(lang, t["title_text"]["en"])
    title_lines = _wrap_text(draw, title_text, title_font, max_text_width)

    headline_lines: list[str] = []
    for h in draft.get("headlines", []):
        text = h.get(lang, h.get("en", ""))
        bullet = f"• {text}"
        headline_lines.extend(_wrap_text(draw, bullet, headline_font, max_text_width))
        if len(headline_lines) >= t["max_lines"] * 2:
            break

    block_height = len(title_lines) * title_line_height + 30 + len(headline_lines) * line_height
    safe_top = t["safe_top_px"]
    safe_bottom = t["safe_bottom_px"]
    available = safe_bottom - safe_top
    y = safe_top + max(0, (available - block_height) // 2)

    scrim_top = y - scrim_padding
    scrim_bottom = y + block_height + scrim_padding
    draw.rectangle(
        [(0, max(0, scrim_top)), (width, min(height, scrim_bottom))],
        fill=scrim_color,
    )

    cursor_y = y
    for line in title_lines:
        draw.text((x, cursor_y), line, font=title_font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
        cursor_y += title_line_height
    cursor_y += 30
    for line in headline_lines:
        draw.text((x, cursor_y), line, font=headline_font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
        cursor_y += line_height

    return img


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

    img = build_overlay(draft, args.lang, config)

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = project_path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
