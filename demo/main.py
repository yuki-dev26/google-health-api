"""Google Health API デモ — OAuth 認証後、直近1週間の健康データをターミナルに表示する。"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import asyncio
import webbrowser
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from demo.auth import (
    build_authorize_url,
    exchange_code,
    get_valid_access_token,
    new_oauth_state,
    save_token,
)
from demo.config import PORT, REDIRECT_URI, SCOPES, TOKEN_PATH
from demo.health_client import HealthClient, _week_range, print_health_summary

oauth_state: str | None = None
shutdown_event = asyncio.Event()
auth_completed = False
auth_lock = asyncio.Lock()


async def fetch_and_print(access_token: str) -> None:
    start, end = _week_range()
    client = HealthClient(access_token)

    try:
        profile, steps, distance, sleep_points = await asyncio.gather(
            client.get_profile(),
            client.daily_steps(start, end),
            client.daily_distance(start, end),
            client.list_sleep(start, end),
        )
    except httpx.HTTPStatusError as exc:
        print(
            f"\nAPI エラー ({exc.response.status_code}): {exc.response.text}",
            file=sys.stderr,
        )
        if exc.response.status_code == 403:
            print("\ndemo/.token.json を削除して再認証してください。", file=sys.stderr)
        raise

    print_health_summary(profile, steps, distance, sleep_points)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Google Health API Demo", lifespan=lifespan)


@app.get("/")
async def root():
    return RedirectResponse("/auth/login")


@app.get("/auth/login")
async def auth_login():
    global oauth_state
    oauth_state = new_oauth_state()
    return RedirectResponse(build_authorize_url(oauth_state))


@app.get("/callback")
async def auth_callback(request: Request):
    global oauth_state, auth_completed

    async with auth_lock:
        if auth_completed:
            return HTMLResponse("認証処理済みです。このタブは閉じて構いません。")

        error = request.query_params.get("error")
        if error:
            raise HTTPException(status_code=400, detail=f"OAuth エラー: {error}")

        code = request.query_params.get("code")
        state = request.query_params.get("state")
        if not code:
            raise HTTPException(status_code=400, detail="認可コードがありません")
        if state != oauth_state:
            raise HTTPException(status_code=400, detail="state が一致しません")

        token = await exchange_code(code)
        save_token(token)

        print("データを取得しています...", flush=True)
        await fetch_and_print(token["access_token"])
        auth_completed = True
        shutdown_event.set()

    return HTMLResponse(
        "<html><body><h2>認証完了</h2><p>健康データをターミナルに出力しました。このタブは閉じて構いません。</p></body></html>"
    )


async def run_with_existing_token() -> bool:
    if not TOKEN_PATH.exists():
        return False
    try:
        access_token = await get_valid_access_token()
        print("保存済みトークンを使用します（再認証をスキップ）", flush=True)
        print("データを取得しています...", flush=True)
        await fetch_and_print(access_token)
        return True
    except (RuntimeError, httpx.HTTPStatusError) as exc:
        print(f"保存済みトークンが使えません: {exc}", file=sys.stderr, flush=True)
        TOKEN_PATH.unlink(missing_ok=True)
        return False


async def run_oauth_flow() -> None:
    print("Google アカウントで認証します...", flush=True)
    print(f"リダイレクト URI: {REDIRECT_URI}", flush=True)
    print(f"要求スコープ: {', '.join(SCOPES)}", flush=True)
    print(f"ブラウザが開きます → http://127.0.0.1:{PORT}/auth/login\n", flush=True)

    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    serve_task = asyncio.create_task(server.serve())

    webbrowser.open(f"http://127.0.0.1:{PORT}/auth/login")
    await shutdown_event.wait()
    server.should_exit = True
    await serve_task


def main() -> None:
    print("Google Health API デモ", flush=True)
    print("-" * 40, flush=True)

    async def _run():
        if await run_with_existing_token():
            return
        await run_oauth_flow()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
