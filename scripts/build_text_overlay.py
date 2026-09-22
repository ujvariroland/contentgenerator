"""Render a transparent PNG text overlay (title + headlines) for the news reel.

Style: one rounded white box per line item (title, then each headline), black text
inside, stacked top-to-bottom, left-aligned. Boxes are sized to their own text (not
full-width) so the background clip stays visible around them. No animation - this
overlay is composited once and burned in for the whole clip duration.

Usage:
    python scripts/build_text_overlay.py --draft output/drafts/2026-09-22_news_draft.json --lang en --out output/videos/2026-09-22/overlay_en.png

Can also be imported and called as build_overlay(...) from render_video.py.
"""

from __future__ import annotations

import argparse
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


def _box_size(draw: ImageDraw.ImageDraw, lines: list[str], font: ImageFont.FreeTypeFont, line_height: int, t: dict) -> tuple[float, float]:
    pad_x, pad_y = t["box_padding_x"], t["box_padding_y"]
    text_width = max((draw.textlength(line, font=font) for line in lines), default=0)
    return text_width + 2 * pad_x, len(lines) * line_height + 2 * pad_y


def _draw_box(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    line_height: int,
    t: dict,
    align: str = "left",
) -> int:
    """Draw one rounded white box containing the given lines. Returns box height."""
    pad_x, pad_y = t["box_padding_x"], t["box_padding_y"]
    box_width, box_height = _box_size(draw, lines, font, line_height, t)

    draw.rounded_rectangle(
        [(x, y), (x + box_width, y + box_height)],
        radius=t["box_radius_px"],
        fill=tuple(t["box_fill_color"]),
    )

    text_fill = tuple(t["fill_color"])
    cursor_y = y + pad_y
    for line in lines:
        if align == "center":
            line_width = draw.textlength(line, font=font)
            line_x = x + (box_width - line_width) / 2
        else:
            line_x = x + pad_x
        draw.text((line_x, cursor_y), line, font=font, fill=text_fill)
        cursor_y += line_height

    return box_height


def build_overlay(draft: dict, lang: str, config: dict) -> Image.Image:
    v = config["video"]
    t = config["text"]

    width, height = v["width"], v["height"]
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_path = project_path(t["font_dir"], t["font_file"])
    headline_font = ImageFont.truetype(str(font_path), t["headline_font_size"])
    title_font = ImageFont.truetype(str(font_path), t["title_font_size"])

    max_text_width = t["max_text_width_px"]
    title_max_width = t["title_max_width_px"]
    headline_line_height = int(t["headline_font_size"] * t["line_height_multiplier"])
    title_line_height = int(t["title_font_size"] * t["line_height_multiplier"])

    x = t["margin_left_px"]
    safe_bottom = t["safe_bottom_px"]
    gap = t["box_gap_px"]

    # Title: centered horizontally, pinned near the top.
    title_text = t["title_text"].get(lang, t["title_text"]["en"])
    title_lines = _wrap_text(draw, title_text, title_font, title_max_width)
    title_box_width, title_box_height = _box_size(draw, title_lines, title_font, title_line_height, t)
    title_x = (width - title_box_width) / 2
    title_y = t["title_top_px"]
    _draw_box(draw, title_lines, title_font, title_x, title_y, title_line_height, t, align="center")

    # Headlines: left-aligned, stacked below the title, narrower so the clip stays visible.
    cursor_y = title_y + title_box_height + gap * 2
    for h in draft.get("headlines", []):
        text = h.get(lang, h.get("en", ""))
        lines = _wrap_text(draw, text, headline_font, max_text_width)
        box_height = len(lines) * headline_line_height + 2 * t["box_padding_y"]
        if cursor_y + box_height > safe_bottom:
            break
        cursor_y += _draw_box(draw, lines, headline_font, x, cursor_y, headline_line_height, t)
        cursor_y += gap

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
