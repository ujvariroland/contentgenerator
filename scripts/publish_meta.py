"""Publish a rendered reel to Instagram (as a Reel + Story, and optionally to Facebook) via
the Meta Graph API.

Both language accounts publish through a Facebook Page's linked Instagram Business
Account. The Graph API needs a public HTTPS URL to fetch the video from (it can't accept
a direct upload), so this script first pushes the mp4 into the public `contentmedia` repo
and builds a raw.githubusercontent.com URL for it.

Running this script IS the "post it" action - there is no further confirmation step, so
only run it once the user has explicitly approved posting for that day/language.

Usage:
    python scripts/publish_meta.py --draft output/drafts/2026-09-23_news_draft.json --lang en
    python scripts/publish_meta.py --draft output/drafts/2026-09-23_news_draft.json --lang en --dry-run
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

from utils import load_config, project_path, read_json


def push_video_to_media_repo(video_path: Path, date_str: str, lang: str, config: dict) -> str:
    """Copy the rendered mp4 into the public media repo, commit, push, return its raw URL."""
    media_repo = project_path(config["publishing"]["media_repo_path"]).resolve()
    if not (media_repo / ".git").exists():
        raise SystemExit(
            f"Media repo not found at {media_repo}. Clone it first:\n"
            f"  git clone <your contentmedia repo url> \"{media_repo}\""
        )

    dest_name = f"{date_str}_news_{lang}.mp4"
    dest_path = media_repo / "videos" / dest_name
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(video_path.read_bytes())

    subprocess.run(["git", "add", f"videos/{dest_name}"], cwd=media_repo, check=True)
    commit = subprocess.run(
        ["git", "commit", "-m", f"Add {dest_name}"],
        cwd=media_repo, capture_output=True, text=True,
    )
    if commit.returncode != 0 and "nothing to commit" not in commit.stdout:
        raise SystemExit(f"git commit failed in media repo:\n{commit.stdout}\n{commit.stderr}")
    subprocess.run(["git", "push", "origin", "main"], cwd=media_repo, check=True)

    raw_base = config["publishing"]["media_repo_raw_base"]
    return f"{raw_base}/videos/{dest_name}"


def graph_url(config: dict, path: str) -> str:
    version = config["publishing"]["graph_api_version"]
    return f"https://graph.facebook.com/{version}/{path}"


def _raise_with_body(resp: requests.Response) -> None:
    if not resp.ok:
        raise SystemExit(f"Graph API error {resp.status_code} for {resp.url}:\n{resp.text}")


def create_reel_container(ig_account_id: str, page_token: str, video_url: str, caption: str, config: dict) -> str:
    resp = requests.post(
        graph_url(config, f"{ig_account_id}/media"),
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": page_token,
        },
        timeout=60,
    )
    _raise_with_body(resp)
    return resp.json()["id"]


def create_story_container(ig_account_id: str, page_token: str, video_url: str, config: dict) -> str:
    """Stories have no caption field - just the video."""
    resp = requests.post(
        graph_url(config, f"{ig_account_id}/media"),
        data={
            "media_type": "STORIES",
            "video_url": video_url,
            "access_token": page_token,
        },
        timeout=60,
    )
    _raise_with_body(resp)
    return resp.json()["id"]


def wait_for_container_ready(creation_id: str, page_token: str, config: dict, timeout_s: int = 300) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        resp = requests.get(
            graph_url(config, creation_id),
            params={"fields": "status_code", "access_token": page_token},
            timeout=30,
        )
        _raise_with_body(resp)
        status = resp.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise SystemExit(f"Media container {creation_id} failed to process (status_code=ERROR)")
        time.sleep(5)
    raise SystemExit(f"Timed out waiting for media container {creation_id} to finish processing")


def publish_container(ig_account_id: str, page_token: str, creation_id: str, config: dict) -> dict:
    resp = requests.post(
        graph_url(config, f"{ig_account_id}/media_publish"),
        data={"creation_id": creation_id, "access_token": page_token},
        timeout=60,
    )
    _raise_with_body(resp)
    return resp.json()


def get_media_permalink(media_id: str, page_token: str, config: dict) -> str | None:
    resp = requests.get(
        graph_url(config, media_id),
        params={"fields": "permalink", "access_token": page_token},
        timeout=30,
    )
    _raise_with_body(resp)
    return resp.json().get("permalink")


def post_facebook_video(page_id: str, page_token: str, video_url: str, caption: str, config: dict) -> str:
    """Post the same video natively to the Facebook Page's feed. Returns the video ID."""
    resp = requests.post(
        graph_url(config, f"{page_id}/videos"),
        data={
            "file_url": video_url,
            "description": caption,
            "access_token": page_token,
        },
        timeout=60,
    )
    _raise_with_body(resp)
    return resp.json()["id"]


def get_facebook_video_permalink(video_id: str, page_token: str, config: dict) -> str | None:
    resp = requests.get(
        graph_url(config, video_id),
        params={"fields": "permalink_url", "access_token": page_token},
        timeout=30,
    )
    _raise_with_body(resp)
    permalink = resp.json().get("permalink_url")
    if permalink and permalink.startswith("/"):
        permalink = f"https://www.facebook.com{permalink}"
    return permalink


TELEGRAM_ANNOUNCEMENT = {
    "en": (
        "Good morning to all tennis fans! ☀️\U0001F3BE\n\n"
        "We've got today's freshest tennis news for you — everything worth knowing if "
        "you're into the world of tennis. \U0001F4E9\n\n"
        "Check it out at the link below:\n\n"
        "\U0001F4F7: {instagram_url}\n\n"
        "If you enjoyed it and want to see more posts like this, please follow us on social "
        "media and leave an algorithm-friendly like/comment."
    ),
    "hu": (
        "Jó reggelt minden tenisz rajóngónak.☀️\U0001F3BE\n\n"
        "Elhoztuk a mai napi legfrissebb híreket, minden amiről érdemes tudnod, ha "
        "érdekel a tenisz világa.\U0001F4E9\n\n"
        "Az alábbi linkeken tekintheted meg ezeket:\n\n"
        "\U0001F60E: {facebook_url}\n\n"
        "\U0001F4F7: {instagram_url}\n\n"
        "Ha tetszett, és szeretnél több ilyen posztot látni, kérlek kövess be a social "
        "médián keresztül és hagyj egy algoritmus támogató like-ot/kommentet."
    ),
}


def send_telegram_announcement(lang: str, instagram_url: str, facebook_url: str | None) -> None:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get(f"TELEGRAM_{lang.upper()}_CHAT_ID")
    if not bot_token or not chat_id:
        print(f"Skipping Telegram announcement - missing TELEGRAM_BOT_TOKEN or TELEGRAM_{lang.upper()}_CHAT_ID")
        return
    text = TELEGRAM_ANNOUNCEMENT[lang].format(instagram_url=instagram_url, facebook_url=facebook_url or "")
    resp = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data={"chat_id": chat_id, "text": text},
        timeout=30,
    )
    if not resp.ok:
        print(f"Telegram announcement failed ({resp.status_code}): {resp.text}")
    else:
        print("Telegram announcement sent.")


def main() -> int:
    load_dotenv(project_path(".env"))
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", required=True)
    parser.add_argument("--lang", required=True, choices=["en", "hu"])
    parser.add_argument("--dry-run", action="store_true", help="Create the media container but don't publish it")
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
    caption = draft.get("instagram_caption", {}).get(lang)
    if not caption:
        raise SystemExit(f"No instagram_caption.{lang} in {draft_path}")

    video_path = project_path(config["paths"]["videos_dir"], date_str, f"news_{lang}.mp4")
    if not video_path.exists():
        raise SystemExit(f"Rendered video not found: {video_path}\nRun render_video.py first.")

    env_prefix = f"META_{lang.upper()}_"
    ig_account_id = os.environ.get(f"{env_prefix}IG_BUSINESS_ACCOUNT_ID")
    page_id = os.environ.get(f"{env_prefix}PAGE_ID")
    page_token = os.environ.get(f"{env_prefix}PAGE_ACCESS_TOKEN")
    if not ig_account_id or not page_token:
        raise SystemExit(f"Missing {env_prefix}IG_BUSINESS_ACCOUNT_ID / {env_prefix}PAGE_ACCESS_TOKEN in .env")

    print(f"Pushing video to media repo...")
    video_url = push_video_to_media_repo(video_path, date_str, lang, config)
    print(f"Public video URL: {video_url}")

    print("Creating Reels container...")
    creation_id = create_reel_container(ig_account_id, page_token, video_url, caption, config)
    print(f"Container created: {creation_id}, waiting for it to finish processing...")
    wait_for_container_ready(creation_id, page_token, config)

    if args.dry_run:
        print(f"Dry run - container {creation_id} is ready but was NOT published.")
        return 0

    print("Publishing...")
    result = publish_container(ig_account_id, page_token, creation_id, config)
    media_id = result.get("id")
    print(f"Published! Media ID: {media_id}")

    instagram_permalink = get_media_permalink(media_id, page_token, config)
    if instagram_permalink:
        print(f"Instagram permalink: {instagram_permalink}")
    else:
        print("Could not fetch Instagram permalink.")

    facebook_permalink = None
    if lang in config["publishing"].get("facebook_post_languages", []):
        if not page_id:
            print(f"Skipping Facebook post - missing {env_prefix}PAGE_ID in .env")
        else:
            print("Posting to Facebook Page...")
            fb_video_id = post_facebook_video(page_id, page_token, video_url, caption, config)
            print(f"Facebook video posted! Video ID: {fb_video_id}")
            facebook_permalink = get_facebook_video_permalink(fb_video_id, page_token, config)
            if facebook_permalink:
                print(f"Facebook permalink: {facebook_permalink}")
            else:
                print("Could not fetch Facebook permalink.")

    if lang in config["publishing"].get("story_languages", []):
        print("Posting to Instagram Story...")
        story_creation_id = create_story_container(ig_account_id, page_token, video_url, config)
        wait_for_container_ready(story_creation_id, page_token, config)
        publish_container(ig_account_id, page_token, story_creation_id, config)
        print("Story published.")

    if instagram_permalink:
        send_telegram_announcement(lang, instagram_permalink, facebook_permalink)
    else:
        print("Skipping Telegram announcement - no Instagram permalink.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
