"""Publish a rendered reel to TikTok via the Content Posting API (Direct Post, PULL_FROM_URL).

TikTok pulls the video from a public URL on a domain we've verified in the Developer
Portal, so the video must be hosted under https://ujvariroland.github.io/contentmedia/
(NOT raw.githubusercontent.com - that domain isn't verified). This script copies the
rendered mp4 into the contentmedia repo's docs/ folder (the GitHub Pages root) instead of
the videos/ folder used for Meta.

Until the app passes TikTok's audit, posts made this way are visible as PRIVATE only,
regardless of the privacy_level requested.

Usage:
    python scripts/publish_tiktok.py --draft output/drafts/2026-09-23_news_draft.json --lang en
"""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

from utils import load_config, project_path, read_json

API_BASE = "https://open.tiktokapis.com/v2"


def push_video_for_tiktok(video_path: Path, date_str: str, lang: str, config: dict) -> str:
    """Copy into contentmedia's docs/ (GitHub Pages root = our verified domain)."""
    media_repo = project_path(config["publishing"]["media_repo_path"]).resolve()
    dest_rel = f"docs/tiktok/{date_str}_news_{lang}.mp4"
    dest_path = media_repo / dest_rel
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(video_path.read_bytes())

    subprocess.run(["git", "add", dest_rel], cwd=media_repo, check=True)
    commit = subprocess.run(
        ["git", "commit", "-m", f"Add {dest_rel} for TikTok"],
        cwd=media_repo, capture_output=True, text=True,
    )
    if commit.returncode != 0 and "nothing to commit" not in commit.stdout:
        raise SystemExit(f"git commit failed in media repo:\n{commit.stdout}\n{commit.stderr}")
    subprocess.run(["git", "push", "origin", "main"], cwd=media_repo, check=True)

    return f"https://ujvariroland.github.io/contentmedia/tiktok/{date_str}_news_{lang}.mp4"


def get_privacy_options(access_token: str) -> list[str]:
    resp = requests.post(
        f"{API_BASE}/post/publish/creator_info/query/",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json; charset=UTF-8"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"]["privacy_level_options"]


def init_video_post(access_token: str, video_url: str, title: str, privacy_level: str) -> str:
    resp = requests.post(
        f"{API_BASE}/post/publish/video/init/",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json; charset=UTF-8"},
        json={
            "post_info": {
                "title": title,
                "privacy_level": privacy_level,
                "disable_duet": False,
                "disable_stitch": False,
                "disable_comment": False,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url,
            },
        },
        timeout=30,
    )
    if not resp.ok:
        raise SystemExit(f"TikTok init failed ({resp.status_code}): {resp.text}")
    data = resp.json()
    if data.get("error", {}).get("code") not in (None, "ok"):
        raise SystemExit(f"TikTok init error: {data['error']}")
    return data["data"]["publish_id"]


def check_status(access_token: str, publish_id: str) -> dict:
    resp = requests.post(
        f"{API_BASE}/post/publish/status/fetch/",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json; charset=UTF-8"},
        json={"publish_id": publish_id},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"]


def main() -> int:
    load_dotenv(project_path(".env"))
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", required=True)
    parser.add_argument("--lang", required=True, choices=["en", "hu"])
    args = parser.parse_args()

    config = load_config()
    draft_path = Path(args.draft)
    if not draft_path.is_absolute():
        draft_path = project_path(args.draft)
    draft = read_json(draft_path)
    if draft is None:
        raise SystemExit(f"Draft not found: {draft_path}")

    date_str = draft.get("date") or draft_path.stem.split("_")[0]
    lang = args.lang
    caption = draft.get("instagram_caption", {}).get(lang, "")
    title = caption.split("\n\n")[0][:150] if caption else f"Tennis news {date_str}"

    video_path = project_path(config["paths"]["videos_dir"], date_str, f"news_{lang}.mp4")
    if not video_path.exists():
        raise SystemExit(f"Rendered video not found: {video_path}\nRun render_video.py first.")

    access_token = os.environ.get("TIKTOK_ACCESS_TOKEN")
    if not access_token:
        raise SystemExit("Missing TIKTOK_ACCESS_TOKEN in .env - run scripts/tiktok_login.py first.")

    print("Pushing video to verified TikTok domain...")
    video_url = push_video_for_tiktok(video_path, date_str, lang, config)
    print(f"Public video URL: {video_url}")

    print("Querying creator info for allowed privacy levels...")
    privacy_options = get_privacy_options(access_token)
    print(f"Available: {privacy_options}")
    privacy_level = "PUBLIC_TO_EVERYONE" if "PUBLIC_TO_EVERYONE" in privacy_options else privacy_options[0]
    print(f"Using privacy_level={privacy_level} (note: unaudited apps post as private regardless)")

    print("Initializing post...")
    publish_id = init_video_post(access_token, video_url, title, privacy_level)
    print(f"publish_id: {publish_id}")

    print("Waiting for TikTok to pull and process the video...")
    for _ in range(24):
        status = check_status(access_token, publish_id)
        print(f"status: {status.get('status')}")
        if status.get("status") in ("PUBLISH_COMPLETE", "FAILED"):
            break
        time.sleep(5)

    print(f"Final status: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
