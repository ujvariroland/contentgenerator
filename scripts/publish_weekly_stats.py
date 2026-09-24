"""Publish the weekly tipping-stats card to Instagram Story (EN+HU) and Facebook Story
(HU). Human-triggered: the user reports the week's numbers in chat, Claude writes the
draft JSON, then the user runs this script (real API calls, so not run by Claude directly).

Usage:
    python scripts/publish_weekly_stats.py --draft "output/drafts/2026.09.10-17_weekly_stats_draft.json"
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv
import os

from utils import load_config, project_path, read_json, write_json
from build_weekly_stats_card import build_weekly_stats_card
from publish_meta import (
    push_image_to_media_repo,
    create_image_story_container,
    publish_container,
    post_facebook_photo_story,
)


def main() -> int:
    load_dotenv(project_path(".env"))
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", required=True)
    args = parser.parse_args()

    config = load_config()
    draft_path = Path(args.draft)
    if not draft_path.is_absolute():
        draft_path = project_path(args.draft)
    draft = read_json(draft_path)
    if draft is None:
        raise SystemExit(f"Draft not found: {draft_path}")

    if draft.get("status") == "posted_story":
        print("This week's stats card was already posted.")
        return 0

    date_range = draft["date_range"]
    image_dir = project_path("output", "weekly_stats_cards")
    image_dir.mkdir(parents=True, exist_ok=True)
    en_path = image_dir / f"{date_range}_en.png"
    hu_path = image_dir / f"{date_range}_hu.png"
    build_weekly_stats_card(draft, "en", config).convert("RGB").save(en_path)
    build_weekly_stats_card(draft, "hu", config).convert("RGB").save(hu_path)
    print(f"Rendered cards for {date_range}.")

    en_url = push_image_to_media_repo(en_path, date_range, "en", config)
    hu_url = push_image_to_media_repo(hu_path, date_range, "hu", config)
    print(f"Pushed images to media repo: {en_url} / {hu_url}")

    for lang, url in (("en", en_url), ("hu", hu_url)):
        env_prefix = f"META_{lang.upper()}_"
        ig_id = os.environ.get(f"{env_prefix}IG_BUSINESS_ACCOUNT_ID")
        token = os.environ.get(f"{env_prefix}PAGE_ACCESS_TOKEN")
        if not ig_id or not token:
            print(f"Skipping {lang} IG story - missing credentials.")
            continue
        creation_id = create_image_story_container(ig_id, token, url, config)
        publish_container(ig_id, token, creation_id, config)
        print(f"Posted IG story ({lang}).")

    if "hu" in config["publishing"].get("facebook_post_languages", []):
        page_id = os.environ.get("META_HU_PAGE_ID")
        token = os.environ.get("META_HU_PAGE_ACCESS_TOKEN")
        if page_id and token:
            post_facebook_photo_story(page_id, token, hu_url, config)
            print("Posted FB story (hu).")
        else:
            print("Skipping FB story - missing HU credentials.")

    draft["status"] = "posted_story"
    write_json(draft_path, draft)
    print("Marked draft as posted. Remember to save these Stories to your 'Stats' Highlight manually.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
