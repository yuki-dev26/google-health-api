import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from demo.auth import (
    build_authorize_url,
    exchange_code,
    get_valid_access_token,
    new_oauth_state,
    save_token,
)
from demo.config import TOKEN_PATH
from playground.gemini_service import GeminiClient
from playground.health_context import (
    default_date_range,
    fetch_health_snapshot,
    format_health_context,
    parse_inclusive_range,
)

load_dotenv(_ROOT / ".env")

STATIC_DIR = Path(__file__).resolve().parent / "static"

oauth_state: str | None = None
auth_completed = False
auth_lock = asyncio.Lock()

health_context_text = ""
health_snapshot: dict | None = None
current_start: date | None = None
current_end_exclusive: date | None = None
gemini_client: GeminiClient | None = None


async def refresh_health_context(start: date, end_exclusive: date) -> dict:
    global health_context_text, health_snapshot, current_start, current_end_exclusive

    access_token = await get_valid_access_token()
    snapshot = await fetch_health_snapshot(access_token, start, end_exclusive)
    health_snapshot = snapshot
    health_context_text = format_health_context(snapshot)
    current_start = start
    current_end_exclusive = end_exclusive
    return snapshot


@asynccontextmanager
async def lifespan(app: FastAPI):
    global gemini_client, current_start, current_end_exclusive
    try:
        gemini_client = GeminiClient()
    except RuntimeError:
        gemini_client = None

    current_start, current_end_exclusive = default_date_range()

    if TOKEN_PATH.exists():
        try:
            await refresh_health_context(current_start, current_end_exclusive)
        except Exception:
            pass
    yield


app = FastAPI(title="Health AI Playground", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class HealthRangeRequest(BaseModel):
    start: str = Field(description="YYYY-MM-DD")
    end: str = Field(description="YYYY-MM-DD（含む）")


class ChatResponse(BaseModel):
    reply: str


@app.get("/favicon.ico")
async def favicon():
    return FileResponse(STATIC_DIR / "logo_google_health.ico")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
async def status():
    start, end_ex = current_start, current_end_exclusive
    if start is None or end_ex is None:
        start, end_ex = default_date_range()
    return {
        "google_connected": TOKEN_PATH.exists(),
        "gemini_ready": gemini_client is not None,
        "health_loaded": health_snapshot is not None,
        "period": health_snapshot.get("period") if health_snapshot else None,
        "default_range": {
            "start": str(start),
            "end": str(end_ex - timedelta(days=1)),
        },
    }


@app.get("/api/health-data")
async def get_health_data():
    if not health_snapshot:
        raise HTTPException(status_code=404, detail="健康データがありません。")
    return health_snapshot


@app.post("/api/health-data")
async def update_health_data(body: HealthRangeRequest):
    if not TOKEN_PATH.exists():
        raise HTTPException(status_code=401, detail="Google Health の認証が必要です。")

    try:
        start, end_exclusive = parse_inclusive_range(body.start, body.end)
        snapshot = await refresh_health_context(start, end_exclusive)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail="健康データの取得に失敗しました。",
        ) from exc

    return snapshot


@app.get("/auth/login")
async def auth_login():
    global oauth_state
    oauth_state = new_oauth_state()
    return RedirectResponse(build_authorize_url(oauth_state))


@app.get("/callback")
async def auth_callback(
    code: str | None = None, state: str | None = None, error: str | None = None
):
    global oauth_state, auth_completed

    async with auth_lock:
        if error:
            raise HTTPException(status_code=400, detail=f"OAuth エラー: {error}")
        if not code:
            raise HTTPException(status_code=400, detail="認可コードがありません")
        if state != oauth_state:
            raise HTTPException(status_code=400, detail="state が一致しません")

        token = await exchange_code(code)
        save_token(token)
        auth_completed = True

        start, end_ex = current_start, current_end_exclusive
        if start is None or end_ex is None:
            start, end_ex = default_date_range()
        try:
            await refresh_health_context(start, end_ex)
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code,
                detail="健康データの取得に失敗しました。",
            ) from exc

    return RedirectResponse("/?connected=1")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    if gemini_client is None:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY が未設定です。")
    if not TOKEN_PATH.exists() or not health_context_text:
        raise HTTPException(
            status_code=401,
            detail="Google Health の認証が必要です。/connect から接続してください。",
        )

    try:
        reply = gemini_client.ask(body.message.strip(), health_context_text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ChatResponse(reply=reply)


@app.get("/connect")
async def connect_page():
    return FileResponse(STATIC_DIR / "connect.html")
