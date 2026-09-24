"""Render a static (non-interactive) Story image mirroring the daily Telegram poll -
Instagram's official API doesn't support interactive poll stickers, so this is a
visual-only companion: the question as a centered title, then one box per player with a
real flag icon (pasted image, not a text glyph - see flag_utils.py) plus their name.

Usage:
    python scripts/build_poll_card.py --draft output/drafts/2026-09-24_poll_draft.json --lang en --out output/poll_cards/2026-09-24_poll_en.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from utils import load_config, project_path, read_json
from flag_utils import get_flag_image


def _player_box_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, flag_size: int, t: dict) -> tuple[int, int]:
    pad_x, pad_y = t["box_padding_x"], t["box_padding_y"]
    text_width = draw.textlength(text, font=font)
    gap = 16
    width = pad_x + flag_size + gap + text_width + pad_x
    height = max(flag_size, int(t["headline_font_size"] * t["line_height_multiplier"])) + 2 * pad_y
    return int(width), int(height)


def _draw_player_box(img: Image.Image, draw: ImageDraw.ImageDraw, x: int, y: int, flag_emoji: str, text: str, font: ImageFont.FreeTypeFont, t: dict) -> int:
    pad_x, pad_y = t["box_padding_x"], t["box_padding_y"]
    flag_size = int(t["headline_font_size"] * 1.1)
    gap = 16
    box_width, box_height = _player_box_size(draw, text, font, flag_size, t)

    draw.rounded_rectangle(
        [(x, y), (x + box_width, y + box_height)],
        radius=t["box_radius_px"],
        fill=tuple(t["box_fill_color"]),
        outline=tuple(t["box_border_color"]),
        width=t["box_border_width"],
    )

    flag_y = y + (box_height - flag_size) // 2
    flag_img = get_flag_image(flag_emoji, size=flag_size)
    img.alpha_composite(flag_img, (x + pad_x, flag_y))

    text_y = y + (box_height - int(t["headline_font_size"] * t["line_height_multiplier"])) // 2
    draw.text((x + pad_x + flag_size + gap, text_y), text, font=font, fill=tuple(t["fill_color"]))

    return box_height


def build_poll_card(draft: dict, lang: str, config: dict) -> Image.Image:
    v = config["video"]
    t = config["text"]
    bg_color = tuple(config["quote_card"]["background_color"])

    img = Image.new("RGBA", (v["width"], v["height"]), bg_color)
    draw = ImageDraw.Draw(img)

    font_path = project_path(t["font_dir"], t["font_file"])
    title_font = ImageFont.truetype(str(font_path), t["title_font_size"])
    headline_font = ImageFont.truetype(str(font_path), t["headline_font_size"])

    # Title (the poll question), centered near the top - same layout convention as the
    # daily news reel's title box.
    question = draft["question"].get(lang, draft["question"]["en"])
    pad_x, pad_y = t["box_padding_x"], t["box_padding_y"]
    title_width = draw.textlength(question, font=title_font) + 2 * pad_x
    title_height = int(t["title_font_size"] * t["line_height_multiplier"]) + 2 * pad_y
    title_x = (v["width"] - title_width) / 2
    title_y = t["title_top_px"]
    draw.rounded_rectangle(
        [(title_x, title_y), (title_x + title_width, title_y + title_height)],
        radius=t["box_radius_px"],
        fill=tuple(t["box_fill_color"]),
        outline=tuple(t["box_border_color"]),
        width=t["box_border_width"],
    )
    draw.text((title_x + pad_x, title_y + pad_y), question, font=title_font, fill=tuple(t["fill_color"]))

    # Player boxes, stacked left-aligned below the title.
    cursor_y = title_y + title_height + t["title_headline_gap_px"]
    x = t["margin_left_px"]
    for player in (draft["match"]["player_a"], draft["match"]["player_b"]):
        box_height = _draw_player_box(img, draw, x, cursor_y, player["flag"], player["short"], headline_font, t)
        cursor_y += box_height + t["box_gap_px"]

    if draft.get("tournament"):
        lines_height = int(t["headline_font_size"] * t["line_height_multiplier"]) + 2 * pad_y
        draw.rounded_rectangle(
            [(x, cursor_y), (x + draw.textlength(draft["tournament"], font=headline_font) + 2 * pad_x, cursor_y + lines_height)],
            radius=t["box_radius_px"],
            fill=tuple(t["box_fill_color"]),
            outline=tuple(t["box_border_color"]),
            width=t["box_border_width"],
        )
        draw.text((x + pad_x, cursor_y + pad_y), draft["tournament"], font=headline_font, fill=tuple(t["fill_color"]))

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

    img = build_poll_card(draft, args.lang, config)

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = project_path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out_path)
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
