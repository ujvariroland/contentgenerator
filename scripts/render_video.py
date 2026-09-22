"""Render the final reel MP4: fixed background loop + burned-in text overlay.

Usage:
    python scripts/render_video.py --draft output/drafts/2026-09-22_news_draft.json --lang en

Produces output/videos/<date>/news_<lang>.mp4 and archives the draft alongside it after
a successful render for both languages have been requested at least once.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from build_text_overlay import build_overlay
from utils import load_config, project_path, read_json


def find_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit(
            "ffmpeg not found on PATH. Install it (e.g. `winget install --id=Gyan.FFmpeg -e`) "
            "and restart your shell."
        )
    return ffmpeg


def render(draft_path: Path, lang: str, config: dict) -> Path:
    draft = read_json(draft_path)
    if draft is None:
        raise SystemExit(f"Draft not found: {draft_path}")

    date_str = draft.get("date") or draft_path.stem.split("_")[0]
    video_dir = project_path(config["paths"]["videos_dir"], date_str)
    video_dir.mkdir(parents=True, exist_ok=True)

    overlay_path = video_dir / f"overlay_{lang}.png"
    img = build_overlay(draft, lang, config)
    img.save(overlay_path)

    v = config["video"]
    background_file = draft.get("background_file") or v["default_background"]
    background_path = project_path(v["background_dir"], background_file)
    if not background_path.exists():
        raise SystemExit(
            f"Background clip not found: {background_path}\n"
            "Add a clip to assets/backgrounds/ (see README setup checklist)."
        )

    output_path = video_dir / f"news_{lang}.mp4"
    ffmpeg = find_ffmpeg()

    cmd = [
        ffmpeg, "-y",
        "-stream_loop", "-1", "-i", str(background_path),
        "-i", str(overlay_path),
        "-filter_complex", "overlay=0:0",
        "-t", str(v["duration_seconds"]),
        "-r", str(v["fps"]),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", required=True)
    parser.add_argument("--lang", required=True, choices=["en", "hu"])
    args = parser.parse_args()

    config = load_config()
    draft_path = Path(args.draft)
    if not draft_path.is_absolute():
        draft_path = project_path(args.draft)

    output_path = render(draft_path, args.lang, config)
    print(f"Rendered {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
