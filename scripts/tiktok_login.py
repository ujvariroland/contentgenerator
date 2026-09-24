"""One-time (well, every ~24h until refreshed) TikTok OAuth login helper.

Prints an authorize URL to open in a browser. After logging in, TikTok redirects to our
static callback page (hosted on GitHub Pages), which displays the `code` query param.
Paste that code back into this script to exchange it for an access token, which gets
saved into .env.

Usage:
    python scripts/tiktok_login.py
"""

from __future__ import annotations

import os
import secrets
import urllib.parse

import requests
from dotenv import load_dotenv

from utils import project_path

AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
SCOPES = "user.info.basic,video.publish,video.upload"


def update_env(key: str, value: str) -> None:
    env_path = project_path(".env")
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    load_dotenv(project_path(".env"))
    client_key = os.environ["TIKTOK_CLIENT_KEY"]
    client_secret = os.environ["TIKTOK_CLIENT_SECRET"]
    redirect_uri = os.environ["TIKTOK_REDIRECT_URI"]

    state = secrets.token_urlsafe(16)
    params = {
        "client_key": client_key,
        "scope": SCOPES,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state,
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    print("1. Open this URL in a browser and log in with the TikTok account to connect:\n")
    print(auth_url)
    print("\n2. After approving, you'll land on the callback page showing a 'code' value.")
    code = input("3. Paste the code here: ").strip()

    resp = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=30,
    )
    if not resp.ok:
        print(f"Token exchange failed ({resp.status_code}): {resp.text}")
        return 1

    data = resp.json()
    if "access_token" not in data:
        print(f"No access_token in response: {data}")
        return 1

    update_env("TIKTOK_ACCESS_TOKEN", data["access_token"])
    update_env("TIKTOK_REFRESH_TOKEN", data.get("refresh_token", ""))
    update_env("TIKTOK_OPEN_ID", data.get("open_id", ""))
    print(f"\nSaved TIKTOK_ACCESS_TOKEN / TIKTOK_REFRESH_TOKEN / TIKTOK_OPEN_ID to .env.")
    print(f"Access token expires in {data.get('expires_in')} seconds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
