"""Fully autonomous daily job: post today's "who wins?" poll to both Telegram channels,
if a poll draft exists for today and hasn't already been posted.

No human approval step - meant to run unattended via a local scheduler (Windows Task
Scheduler), around noon. Pulls the latest changes first so it can see a poll draft pushed
earlier the same morning by the cloud routine.

Usage:
    python scripts/publish_poll.py
"""

from __future__ import annotations

import subprocess
import os
from datetime import datetime

import requests
from dotenv import load_dotenv

from utils import project_path, read_json, write_json, today_str


def log(message: str) -> None:
    log_path = project_path("output", "logs", "publish_poll.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat(timespec="seconds")
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(message)


def send_poll(bot_token: str, chat_id: str, question: str, options: list[str]) -> bool:
    resp = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendPoll",
        data={
            "chat_id": chat_id,
            "question": question,
            "options": __import__("json").dumps(options),
            "is_anonymous": "true",
            "type": "regular",
        },
        timeout=30,
    )
    if not resp.ok:
        log(f"sendPoll failed for chat {chat_id} ({resp.status_code}): {resp.text}")
        return False
    return True


def main() -> int:
    load_dotenv(project_path(".env"))
    root = project_path()

    subprocess.run(["git", "pull", "origin", "main"], cwd=root, check=True)

    date_str = today_str()
    draft_path = project_path("output", "drafts", f"{date_str}_poll_draft.json")
    if not draft_path.exists():
        log(f"{date_str}: no poll draft today, nothing to do.")
        return 0

    draft = read_json(draft_path)
    if draft.get("status") == "posted":
        log(f"{date_str}: poll already posted, skipping.")
        return 0

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    match = draft["match"]
    option_a = f"{match['player_a']['short']} {match['player_a']['flag']}"
    option_b = f"{match['player_b']['short']} {match['player_b']['flag']}"

    ok = True
    for lang_key in ("en", "hu"):
        chat_id = os.environ.get(f"TELEGRAM_{lang_key.upper()}_CHAT_ID")
        if not bot_token or not chat_id:
            log(f"{lang_key}: missing TELEGRAM_BOT_TOKEN or chat id.")
            ok = False
            continue
        question = draft["question"].get(lang_key, draft["question"]["en"])
        if send_poll(bot_token, chat_id, question, [option_a, option_b]):
            log(f"{date_str}: posted poll ({lang_key}).")
        else:
            ok = False

    draft["status"] = "posted"
    write_json(draft_path, draft)
    subprocess.run(["git", "add", str(draft_path.relative_to(root))], cwd=root, check=True)
    commit = subprocess.run(
        ["git", "commit", "-m", f"Mark {date_str} poll as posted"],
        cwd=root, capture_output=True, text=True,
    )
    if commit.returncode == 0:
        subprocess.run(["git", "push", "origin", "main"], cwd=root, check=True)

    log(f"{date_str}: {'all polls posted successfully' if ok else 'completed with errors'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
