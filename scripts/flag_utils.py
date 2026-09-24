"""Fetch and cache country flag images for pasting into Pillow-rendered cards.

Regular TTF fonts (like our branded Archivo Black) can't render color flag emoji glyphs -
Pillow's basic text drawing has no color-emoji font fallback - so flags are pasted as small
PNGs instead of drawn as text. Uses the open (CC-BY 4.0) Twemoji icon set, cached locally
after the first download so later renders (including the unattended local scheduled jobs)
don't need network access.
"""

from __future__ import annotations

import requests
from PIL import Image

from utils import project_path

TWEMOJI_BASE = "https://cdn.jsdelivr.net/gh/jdecked/twemoji@16.0.1/assets/72x72"


def _codepoints(flag_emoji: str) -> str:
    return "-".join(f"{ord(c):x}" for c in flag_emoji)


def get_flag_image(flag_emoji: str, size: int = 64) -> Image.Image:
    cache_dir = project_path("assets", "flags")
    cache_dir.mkdir(parents=True, exist_ok=True)
    codepoints = _codepoints(flag_emoji)
    cache_path = cache_dir / f"{codepoints}.png"
    if not cache_path.exists():
        url = f"{TWEMOJI_BASE}/{codepoints}.png"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        cache_path.write_bytes(resp.content)
    img = Image.open(cache_path).convert("RGBA")
    return img.resize((size, size), Image.LANCZOS)
