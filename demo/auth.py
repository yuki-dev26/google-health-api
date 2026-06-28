import json
import secrets
import time
from urllib.parse import urlencode

import httpx

from demo.config import (
    AUTH_URL,
    CLIENT_ID,
    CLIENT_SECRET,
    REDIRECT_URI,
    SCOPES,
    TOKEN_PATH,
    TOKEN_URL,
)


def load_token() -> dict | None:
    if not TOKEN_PATH.exists():
        return None
    return json.loads(TOKEN_PATH.read_text(encoding="utf-8"))


def save_token(token: dict) -> None:
    TOKEN_PATH.write_text(json.dumps(token, indent=2), encoding="utf-8")


def build_authorize_url(state: str) -> str:
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
        )
        response.raise_for_status()
        token = response.json()
        token["obtained_at"] = int(time.time())
        return token


async def refresh_access_token(token: dict) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": token["refresh_token"],
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
        )
        response.raise_for_status()
        refreshed = response.json()
        refreshed["refresh_token"] = token.get(
            "refresh_token", refreshed.get("refresh_token")
        )
        refreshed["obtained_at"] = int(time.time())
        return refreshed


def is_expired(token: dict) -> bool:
    expires_in = token.get("expires_in", 3600)
    obtained_at = token.get("obtained_at", 0)
    return time.time() >= obtained_at + expires_in - 60


async def get_valid_access_token() -> str:
    token = load_token()
    if token:
        if is_expired(token):
            if "refresh_token" not in token:
                raise RuntimeError(
                    "トークンの有効期限が切れています。demo/.token.json を削除して再認証してください。"
                )
            token = await refresh_access_token(token)
            save_token(token)
        return token["access_token"]
    raise RuntimeError("未認証")


def new_oauth_state() -> str:
    return secrets.token_urlsafe(32)
