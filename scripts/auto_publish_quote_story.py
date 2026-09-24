"""Fully autonomous daily job: post today's quote card to Instagram Story (EN+HU) and
Facebook Story (HU), if a quote draft exists for today and hasn't already been posted.

No human approval step - this is meant to run unattended via a local scheduler (Windows
Task Scheduler), using credentials from the local .env file. It pulls the latest changes
first so it can see a quote draft pushed earlier the same morning by the cloud routine.

Usage:
    python scripts/auto_publish_quote_story.py
"""

from __future__ import annotations

import subprocess
import os
from datetime import datetime

from dotenv import load_dotenv

from utils import load_config, project_path, read_json, write_json, today_str
from build_quote_card import build_quote_card
from publish_meta import (
    push_image_to_media_repo,
    create_image_story_container,
    publish_container,
    post_facebook_photo_story,
)


def log(message: str) -> None:
    log_path = project_path("output", "logs", "auto_publish_quote_story.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat(timespec="seconds")
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(message)


def main() -> int:
    load_dotenv(project_path(".env"))
    root = project_path()

    subprocess.run(["git", "pull", "origin", "main"], cwd=root, check=True)

    config = load_config()
    date_str = today_str()
    draft_path = project_path("output", "drafts", f"{date_str}_quote_draft.json")
    if not draft_path.exists():
        log(f"{date_str}: no quote draft today, nothing to do.")
        return 0

    draft = read_json(draft_path)
    if draft.get("status") == "posted_story":
        log(f"{date_str}: quote story already posted, skipping.")
        return 0

    attribution = draft["attribution"]
    quote_en = draft["quote"]["en"]
    quote_hu = draft["quote"]["hu"]
    context_en = draft.get("context", {}).get("en")
    context_hu = draft.get("context", {}).get("hu")

    image_dir = project_path("output", "quote_cards")
    image_dir.mkdir(parents=True, exist_ok=True)
    en_path = image_dir / f"{date_str}_quote_en.png"
    hu_path = image_dir / f"{date_str}_quote_hu.png"
    build_quote_card(quote_en, attribution, context_en, config).convert("RGB").save(en_path)
    build_quote_card(quote_hu, attribution, context_hu, config).convert("RGB").save(hu_path)
    log(f"{date_str}: rendered quote cards.")

    en_url = push_image_to_media_repo(en_path, date_str, "en", config)
    hu_url = push_image_to_media_repo(hu_path, date_str, "hu", config)
    log(f"{date_str}: pushed images to media repo.")

    errors: list[str] = []

    for lang, url in (("en", en_url), ("hu", hu_url)):
        env_prefix = f"META_{lang.upper()}_"
        ig_id = os.environ.get(f"{env_prefix}IG_BUSINESS_ACCOUNT_ID")
        token = os.environ.get(f"{env_prefix}PAGE_ACCESS_TOKEN")
        if not ig_id or not token:
            errors.append(f"{lang}: missing Meta credentials")
            continue
        try:
            creation_id = create_image_story_container(ig_id, token, url, config)
            publish_container(ig_id, token, creation_id, config)
            log(f"{date_str}: posted IG story ({lang}).")
        except SystemExit as e:
            errors.append(f"{lang} IG story: {e}")

    if "hu" in config["publishing"].get("facebook_post_languages", []):
        page_id = os.environ.get("META_HU_PAGE_ID")
        token = os.environ.get("META_HU_PAGE_ACCESS_TOKEN")
        if page_id and token:
            try:
                post_facebook_photo_story(page_id, token, hu_url, config)
                log(f"{date_str}: posted FB story (hu).")
            except SystemExit as e:
                errors.append(f"hu FB story: {e}")
        else:
            errors.append("hu FB story: missing credentials")

    draft["status"] = "posted_story"
    write_json(draft_path, draft)
    subprocess.run(["git", "add", str(draft_path.relative_to(root))], cwd=root, check=True)
    commit = subprocess.run(
        ["git", "commit", "-m", f"Mark {date_str} quote story as posted"],
        cwd=root, capture_output=True, text=True,
    )
    if commit.returncode == 0:
        subprocess.run(["git", "push", "origin", "main"], cwd=root, check=True)

    if errors:
        log(f"{date_str}: completed with errors: {'; '.join(errors)}")
    else:
        log(f"{date_str}: all stories posted successfully.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
